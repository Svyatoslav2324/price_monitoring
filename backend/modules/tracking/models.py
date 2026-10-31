from django.conf import settings
from django.db import models

from modules.products.models import Product


class Tracking(models.Model):
    """Подписка пользователя на цену товара."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Активен"
        PAUSED = "paused", "На паузе"
        ERROR = "error", "Ошибка"  # товар пропал с маркетплейса; воркер продолжает проверять

    class Interval(models.IntegerChoices):
        HOURLY = 60, "Каждый час"
        EVERY_6H = 360, "Раз в 6 часов"
        DAILY = 1440, "Раз в день"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trackings")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="trackings")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    check_interval = models.PositiveIntegerField(choices=Interval.choices, default=Interval.HOURLY)  # минуты
    target_price = models.DecimalField(max_digits=12, decimal_places=2)
    target_reached_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="uniq_tracking_per_user"),
            models.CheckConstraint(condition=models.Q(target_price__gt=0), name="tracking_target_positive"),
        ]
        indexes = [models.Index(fields=["status", "product"])]
