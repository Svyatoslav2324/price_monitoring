from decimal import Decimal

from django.test import SimpleTestCase

from .base import ProductNotFound, UnsupportedURL
from .registry import resolve
from .wildberries import client as wb

CARD = {
    "id": 169684889,
    "brand": "Sony",
    "name": "Наушники WH-1000XM5",
    "totalQuantity": 12,
    "sizes": [
        {"price": {"basic": 3000000, "product": 2450000}},
        {"price": {"basic": 3000000, "product": 2399900}},
        {},  # размер без цены (нет в наличии)
    ],
}


class WildberriesParseTests(SimpleTestCase):
    def test_parse_url(self):
        self.assertEqual(wb.parse_url("https://www.wildberries.ru/catalog/169684889/detail.aspx?size=1"), "169684889")
        self.assertIsNone(wb.parse_url("https://www.wildberries.ru/brands/sony"))

    def test_card_v4_takes_min_price_in_rubles(self):
        snap = wb.parse_card("169684889", {"products": [CARD]})
        self.assertEqual(snap.price, Decimal("23999.00"))
        self.assertTrue(snap.in_stock)
        self.assertEqual(snap.title, "Sony / Наушники WH-1000XM5")

    def test_card_v2_layout(self):
        self.assertEqual(wb.parse_card("169684889", {"data": {"products": [CARD]}}).price, Decimal("23999.00"))

    def test_out_of_stock(self):
        snap = wb.parse_card("1", {"products": [{"id": 1, "name": "x", "totalQuantity": 0, "sizes": [{}]}]})
        self.assertFalse(snap.in_stock)
        self.assertIsNone(snap.price)

    def test_missing_card(self):
        with self.assertRaises(ProductNotFound):
            wb.parse_card("1", {"products": []})


class RegistryTests(SimpleTestCase):
    def test_resolve(self):
        provider, ext_id = resolve("https://wildberries.ru/catalog/123456/detail.aspx")
        self.assertEqual((provider.CODE, ext_id), ("wildberries", "123456"))

    def test_rejects(self):
        for url in ("wildberries.ru/catalog/1/", "https://evil-wildberries.ru/catalog/123456/", "https://ozon.ru/product/1/",
                    "https://www.wildberries.ru/brands/sony"):
            with self.subTest(url=url), self.assertRaises(UnsupportedURL):
                resolve(url)
