"""Ozon parser adapted from uparser for one long-lived queue worker."""
import asyncio
import logging
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

if __name__ == "__main__" and not __package__:
    import sys
    from pathlib import Path

    # Resolve package imports when this file is launched directly.
    sys.path[0] = str(Path(__file__).resolve().parents[1])
    __package__ = "app"

from .profile_pool import lease_profile
from .price_status import UnavailablePrice

from .ozon_parser import Parser


def ozon_url(url):
    parts = urlsplit(url)
    host = parts.hostname or ""
    return (parts.scheme in ("http", "https") and parts.username is None
            and host in ("ozon.ru", "www.ozon.ru", "m.ozon.ru") and parts.port in (None, 80, 443))


@asynccontextmanager
async def worker_session(*, headed=False):
    async with lease_profile() as profile:
        parser = Parser("ozon-worker", profile_path=profile, headed=headed)

        async def parse(url, marketplace_id):
            if not ozon_url(url):
                raise ValueError("Ожидалась ссылка на Ozon")
            async with asyncio.timeout(240):
                await parser.start_browser()
                if not await parser.check_authentication():
                    parser.logger.warning("%s: авторизация не подтверждена, проверяем гостевую цену", profile.name)
                try:
                    product = await parser.parse(url)
                    raw = product["price"]
                    statuses = {
                        "товар закончился": UnavailablePrice.OUT_OF_STOCK,
                        "этот товар закончился": UnavailablePrice.OUT_OF_STOCK,
                        "страницы не существует": UnavailablePrice.NOT_FOUND,
                        "такой страницы не существует": UnavailablePrice.NOT_FOUND,
                        "не доставляется в ваш регион": UnavailablePrice.REGION,
                        "товар не доставляется в ваш регион": UnavailablePrice.REGION,
                    }
                    if raw in statuses:
                        return statuses[raw]
                    try:
                        return Decimal(str(raw))
                    except InvalidOperation as exc:
                        raise ValueError(f"Цена недоступна: {product['price']}") from exc
                finally:
                    # Историю хранит PostgreSQL; очищаем буфер пакетного парсера.
                    parser.products.clear()
                    parser.product_index = 0

        try:
            yield parse
        finally:
            await parser.stop_browser()


def check_price(url, marketplace_id):
    """Compatibility for callers that request a standalone price check."""
    async def once():
        async with worker_session() as parse:
            return await parse(url, marketplace_id)
    return asyncio.run(once())

async def debug_card(url, pause_seconds=1000):
    from pathlib import Path

    profile = "./data/test_profile"
    parser = Parser("ozon-debug", profile_path=profile, headed=True)
    try:
        await parser.start_browser()
        product = await parser.parse(url)
        print(f"Результат: {product['price']}")
    finally:
        await parser.stop_browser()


if __name__ == "__main__":
    import argparse

    cli = argparse.ArgumentParser(description="Проверить одну карточку Ozon в видимом браузере")
    cli.add_argument("url", nargs="?", default="https://www.ozon.ru/product/hudi-don-veneziani-4437605960/?at=1kqs1XbevjhuwOmRcqiYheK19q4oVMmS&sh=Fo9zToD_Fw",
                     help="Ссылка на тестовую карточку товара")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cli.add_argument("--pause", type=int, default=1000, help="Пауза после открытия карточки в секундах (по умолчанию 1000)")
    args = cli.parse_args()
    if args.pause < 0:
        cli.error("--pause должен быть неотрицательным")
    asyncio.run(debug_card(args.url, args.pause))
