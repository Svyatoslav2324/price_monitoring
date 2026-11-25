from django.db import models


class Product(models.Model):
    """Товар маркетплейса. Общий для всех пользователей, которые его отслеживают."""

    marketplace = models.CharField(max_length=32)
    external_id = models.CharField(max_length=64)
    url = models.URLField(max_length=500)
    title = models.CharField(max_length=500)
    current_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    in_stock = models.BooleanField(default=False)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["marketplace", "external_id"], name="uniq_product_per_marketplace"),
        ]

    def __str__(self):
        return f"[{self.marketplace}] {self.title}"


class PricePoint(models.Model):
    """Цена на момент проверки. Пишется только когда товар в наличии."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["product", "checked_at"])]
        ordering = ["checked_at"]
