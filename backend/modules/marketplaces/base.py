"""Общий контракт для клиентов маркетплейсов.

Каждый маркетплейс — модуль в modules/marketplaces/<code>/client.py, экспортирующий:
  CODE, NAME, HOSTS, parse_url(url) -> external_id | None, fetch(external_id) -> ProductSnapshot
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProductSnapshot:
    external_id: str
    title: str
    price: Decimal | None  # None — товара нет в наличии
    in_stock: bool


class MarketplaceError(Exception):
    """Временная ошибка (сеть, 5xx, лимиты). Стоит повторить позже."""


class ProductNotFound(MarketplaceError):
    """Товар не существует или снят с продажи. Повторять бессмысленно."""


class UnsupportedURL(ValueError):
    pass
