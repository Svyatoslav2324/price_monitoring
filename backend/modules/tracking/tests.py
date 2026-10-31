from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.utils import timezone
from rest_framework.test import APITestCase

from modules.marketplaces.base import MarketplaceError, ProductNotFound, ProductSnapshot
from modules.products.models import Product

from . import worker
from .models import Tracking

URL = "https://www.wildberries.ru/catalog/123456/detail.aspx"
FETCH = "modules.marketplaces.wildberries.client.fetch"


def snap(price):
    return ProductSnapshot("123456", "Sony / Наушники", None if price is None else Decimal(price), price is not None)


class TrackingFlowTests(APITestCase):
    def auth(self, username):
        r = self.client.post("/api/auth/register/", {"username": username, "password": "s3cret-pass"})
        self.assertEqual(r.status_code, 201, r.data)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + r.data["token"])

    def add(self, target="20000", url=URL):
        return self.client.post("/api/trackings/", {"url": url, "check_interval": 60, "target_price": target})

    def test_full_flow(self):
        self.auth("alice")
        with mock.patch(FETCH, return_value=snap("25000")) as fetch:
            r = self.add()
            self.assertEqual(r.status_code, 201, r.data)
            self.assertEqual(r.data["product"]["current_price"], 25000.0)
            self.assertEqual(self.add().status_code, 409)
            fetch.assert_called_once()  # повторно карточку не грузим

        tid, pid = r.data["id"], r.data["product"]["id"]
        self.assertEqual(len(self.client.get("/api/trackings/").data), 1)
        self.assertEqual(self.client.get(f"/api/products/{pid}/").data["tracking"]["target_price"], 20000.0)
        self.assertEqual(len(self.client.get(f"/api/products/{pid}/history/").data), 1)
        self.assertEqual(self.client.get(f"/api/products/{pid}/history/?days=0").status_code, 400)

        self.assertEqual(self.client.patch(f"/api/trackings/{tid}/", {"status": "error"}).status_code, 400)
        r = self.client.patch(f"/api/trackings/{tid}/", {"status": "paused"})
        self.assertEqual(r.data["status"], "paused")

        # Чужие данные не видны
        self.auth("bob")
        self.assertEqual(self.client.get(f"/api/trackings/{tid}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/products/{pid}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/trackings/{tid}/").status_code, 404)

    def test_add_errors(self):
        self.auth("alice")
        self.assertEqual(self.add(url="https://ozon.ru/product/1/").status_code, 400)
        self.assertEqual(self.add(target="0").status_code, 400)
        with mock.patch(FETCH, side_effect=ProductNotFound("нет")):
            self.assertEqual(self.add().status_code, 404)
        with mock.patch(FETCH, side_effect=MarketplaceError("down")):
            self.assertEqual(self.add().status_code, 502)
        self.assertEqual(Product.objects.count(), 0)

    def test_auth(self):
        self.assertEqual(self.client.get("/api/trackings/").status_code, 401)
        r = self.client.post("/api/auth/register/", {"username": "alice", "password": "123"})
        self.assertIn("password", r.data)
        self.auth("alice")
        self.assertEqual(self.client.post("/api/auth/register/", {"username": "ALICE", "password": "s3cret-pass"}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login/", {"username": "alice", "password": "wrong"}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)


class WorkerTests(APITestCase):
    def setUp(self):
        r = self.client.post("/api/auth/register/", {"username": "alice", "password": "s3cret-pass"})
        self.client.credentials(HTTP_AUTHORIZATION="Token " + r.data["token"])
        with mock.patch(FETCH, return_value=snap("25000")):
            self.client.post("/api/trackings/", {"url": URL, "check_interval": 60, "target_price": "20000"})
        self.product = Product.objects.get()
        self.tracking = Tracking.objects.get()

    def make_due(self):
        Product.objects.update(last_checked_at=timezone.now() - timedelta(minutes=61))

    def test_not_due_right_after_add(self):
        self.assertEqual(worker.run_once(), 0)

    def test_paused_is_not_checked(self):
        Tracking.objects.update(status=Tracking.Status.PAUSED)
        self.make_due()
        self.assertEqual(worker.run_once(), 0)

    def test_price_drop_reaches_target(self):
        self.make_due()
        with mock.patch(FETCH, return_value=snap("19990")):
            self.assertEqual(worker.run_once(), 1)
        self.product.refresh_from_db()
        self.tracking.refresh_from_db()
        self.assertEqual(self.product.current_price, Decimal("19990"))
        self.assertEqual(self.product.prices.count(), 2)
        self.assertIsNotNone(self.tracking.target_reached_at)
        self.assertEqual(worker.run_once(), 0)  # сразу после проверки — не due

    def test_gone_then_back(self):
        self.make_due()
        with mock.patch(FETCH, side_effect=ProductNotFound("нет")):
            worker.run_once()
        self.tracking.refresh_from_db()
        self.assertEqual(self.tracking.status, Tracking.Status.ERROR)

        self.make_due()
        with mock.patch(FETCH, return_value=snap(None)):  # вернулся, но нет в наличии
            worker.run_once()
        self.tracking.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.tracking.status, Tracking.Status.ACTIVE)
        self.assertFalse(self.product.in_stock)
        self.assertEqual(self.product.prices.count(), 1)

    def test_transient_error_keeps_status(self):
        self.make_due()
        with mock.patch(FETCH, side_effect=MarketplaceError("503")):
            worker.run_once()
        self.tracking.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.tracking.status, Tracking.Status.ACTIVE)
        self.assertEqual(self.product.last_error, "503")
