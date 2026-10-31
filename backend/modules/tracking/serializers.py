from decimal import Decimal
from rest_framework import serializers
from modules.products.serializers import ProductSerializer
from .models import Tracking

_price = dict(max_digits=12, decimal_places=2, min_value=Decimal("0.01"), coerce_to_string=False)


class TrackingSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    target_price = serializers.DecimalField(**_price)
    status = serializers.ChoiceField(
        choices=[Tracking.Status.ACTIVE, Tracking.Status.PAUSED], required=False,
        help_text="Клиент может только ставить на паузу и возобновлять",
    )

    class Meta:
        model = Tracking
        fields = (
            "id", "product", "status", "check_interval", "target_price",
            "target_reached_at", "created_at", "updated_at",
        )
        read_only_fields = ("target_reached_at", "created_at", "updated_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["status"] = instance.status  # отдаём в т.ч. "error", хотя записать его нельзя
        return data

    def update(self, instance, validated_data):
        if "target_price" in validated_data and validated_data["target_price"] != instance.target_price:
            instance.target_reached_at = None  # новая цель — уведомим заново
        return super().update(instance, validated_data)


class TrackingCreateSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=500)
    check_interval = serializers.ChoiceField(choices=Tracking.Interval.choices, default=Tracking.Interval.HOURLY)
    target_price = serializers.DecimalField(**_price)
