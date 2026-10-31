"""Фоновая проверка цен.

Товар «пора проверять», если у него есть не-приостановленное отслеживание и с последней
проверки прошло больше check_interval этого отслеживания (берётся самый частый).
Несколько воркеров безопасны: товары захватываются через SELECT ... FOR UPDATE SKIP LOCKED.
"""
import logging
import time
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from modules.marketplaces.base import MarketplaceError, ProductNotFound
from modules.products.models import Product
from modules.products.services import refresh_product

from .models import Tracking

log = logging.getLogger(__name__)
_LIVE = [Tracking.Status.ACTIVE, Tracking.Status.ERROR]


def claim_due_products(limit: int) -> list[Product]:
    now = timezone.now()
    stale = Q(product__last_checked_at__isnull=True)
    for minutes in Tracking.Interval.values:  # интервалов фиксированный набор — условие на каждый
        stale |= Q(check_interval=minutes, product__last_checked_at__lte=now - timedelta(minutes=minutes))
    due = Tracking.objects.filter(stale, status__in=_LIVE)

    with transaction.atomic():
        products = list(
            Product.objects.select_for_update(skip_locked=True)
            .filter(id__in=due.values("product_id"))
            .order_by(F("last_checked_at").asc(nulls_first=True))[:limit]
        )
        # Захват: сдвигаем last_checked_at, чтобы другие воркеры не взяли те же товары
        Product.objects.filter(id__in=[p.id for p in products]).update(last_checked_at=now)
    return products


def check_product(product: Product) -> None:
    try:
        refresh_product(product)
    except ProductNotFound as e:
        Tracking.objects.filter(product=product, status=Tracking.Status.ACTIVE).update(status=Tracking.Status.ERROR)
        log.info("product %s gone: %s", product.id, e)
        return
    except MarketplaceError as e:
        log.warning("product %s check failed: %s", product.id, e)  # временная ошибка, статусы не трогаем
        return

    Tracking.objects.filter(product=product, status=Tracking.Status.ERROR).update(status=Tracking.Status.ACTIVE)
    if product.current_price is not None:
        reached = Tracking.objects.filter(
            product=product,
            status=Tracking.Status.ACTIVE,
            target_reached_at__isnull=True,
            target_price__gte=product.current_price,
        )
        # ponytail: уведомление = запись в лог; канал доставки (email/Telegram) подключать здесь
        for t in reached.select_related("user"):
            log.info("target reached: user=%s product=%s price=%s", t.user.username, product.id, product.current_price)
        reached.update(target_reached_at=timezone.now())


def run_once(batch_size: int | None = None) -> int:
    products = claim_due_products(batch_size or settings.WORKER_BATCH_SIZE)
    # ponytail: последовательно, чтобы не ловить лимиты WB; пул потоков — когда товаров станут тысячи
    for product in products:
        check_product(product)
    return len(products)


def run_forever() -> None:
    log.info("price worker started")
    while True:
        try:
            checked = run_once()
        except Exception:
            log.exception("worker iteration failed")
            checked = 0
        if not checked:
            time.sleep(settings.WORKER_IDLE_SECONDS)
