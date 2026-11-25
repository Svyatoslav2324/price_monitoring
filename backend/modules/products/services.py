from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.marketplaces.base import MarketplaceError
from modules.marketplaces.registry import get_provider, resolve

from .models import PricePoint, Product


def get_or_create_product(url: str) -> Product:
    """Находит товар по ссылке или создаёт его, сразу загрузив карточку с маркетплейса.

    Бросает UnsupportedURL / ProductNotFound / MarketplaceError.
    """
    provider, external_id = resolve(url)
    product = Product.objects.filter(marketplace=provider.CODE, external_id=external_id).first()
    if product:
        return product

    snap = provider.fetch(external_id)
    try:
        with transaction.atomic():
            product = Product.objects.create(
                marketplace=provider.CODE,
                external_id=external_id,
                url=provider.PRODUCT_URL.format(id=external_id),
                title=snap.title,
            )
            _apply_snapshot(product, snap)
    except IntegrityError:  # параллельный запрос успел создать тот же товар
        product = Product.objects.get(marketplace=provider.CODE, external_id=external_id)
    return product


def refresh_product(product: Product) -> None:
    """Перезагружает цену с маркетплейса. Ошибки записывает в product.last_error и пробрасывает."""
    provider = get_provider(product.marketplace)
    try:
        snap = provider.fetch(product.external_id)
    except MarketplaceError as e:
        product.last_error = str(e)[:500]
        product.last_checked_at = timezone.now()
        product.save(update_fields=["last_error", "last_checked_at"])
        raise
    with transaction.atomic():
        product.title = snap.title
        _apply_snapshot(product, snap)


def _apply_snapshot(product: Product, snap) -> None:
    product.current_price = snap.price
    product.in_stock = snap.in_stock
    product.last_error = ""
    product.last_checked_at = timezone.now()
    product.save()
    if snap.price is not None:
        PricePoint.objects.create(product=product, price=snap.price)
