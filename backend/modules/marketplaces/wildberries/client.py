"""Клиент публичного API карточек Wildberries (card.wb.ru).

API отвечает 403 на запросы не из РФ — сервер должен стоять в российском сегменте.
"""
import json
import logging
import re
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from ..base import MarketplaceError, ProductNotFound, ProductSnapshot

CODE = "wildberries"
NAME = "Wildberries"
HOSTS = ("wildberries.ru", "wb.ru")
PRODUCT_URL = "https://www.wildberries.ru/catalog/{id}/detail.aspx"

CARD_API = "https://card.wb.ru/cards/v4/detail"
RETRIES = 3
_URL_RE = re.compile(r"/catalog/(\d{3,12})/")

log = logging.getLogger(__name__)


def parse_url(url: str) -> str | None:
    m = _URL_RE.search(url)
    return m.group(1) if m else None


def fetch(nm_id: str) -> ProductSnapshot:
    query = urlencode({"appType": 1, "curr": "rub", "dest": settings.WB_DEST, "nm": nm_id})
    payload = _get_json(f"{CARD_API}?{query}")
    return parse_card(nm_id, payload)


def parse_card(nm_id: str, payload: dict) -> ProductSnapshot:
    # v4 отдаёт products в корне, v2 — внутри data
    products = payload.get("products") or (payload.get("data") or {}).get("products") or []
    card = next((p for p in products if str(p.get("id")) == str(nm_id)), None)
    if card is None:
        raise ProductNotFound(f"Товар {nm_id} не найден на Wildberries")

    # Цены в копейках; у разных размеров они могут отличаться — берём минимальную
    prices = [
        s["price"]["product"]
        for s in card.get("sizes") or []
        if (s.get("price") or {}).get("product")
    ]
    if not prices and card.get("salePriceU"):  # старый формат v1
        prices = [card["salePriceU"]]

    in_stock = bool(prices) and card.get("totalQuantity", 1) > 0
    title = " / ".join(x for x in (card.get("brand"), card.get("name")) if x) or f"Товар {nm_id}"
    return ProductSnapshot(
        external_id=str(nm_id),
        title=title[:500],
        price=(Decimal(min(prices)) / 100).quantize(Decimal("0.01")) if in_stock else None,
        in_stock=in_stock,
    )


def _get_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    for attempt in range(1, RETRIES + 1):
        try:
            with urlopen(req, timeout=settings.WB_TIMEOUT) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            if e.code == 404:
                raise ProductNotFound("Товар не найден на Wildberries") from e
            retriable = e.code == 429 or e.code >= 500
            error = MarketplaceError(f"Wildberries ответил {e.code}")
        except (URLError, TimeoutError, json.JSONDecodeError) as e:
            retriable = True
            error = MarketplaceError(f"Wildberries недоступен: {e}")

        if not retriable or attempt == RETRIES:
            raise error
        log.warning("WB request failed (%s), retry %d/%d", error, attempt, RETRIES)
        time.sleep(attempt)  # 1s, 2s
    raise AssertionError("unreachable")
