from rest_framework import serializers
from modules.marketplaces.registry import PROVIDERS
from .models import PricePoint, Product


class ProductSerializer(serializers.ModelSerializer):
    marketplace_name = serializers.SerializerMethodField()
    current_price = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, allow_null=True)

    class Meta:
        model = Product
        fields = (
            "id", "marketplace", "marketplace_name", "external_id", "url", "title",
            "current_price", "in_stock", "last_checked_at", "last_error",
        )

    def get_marketplace_name(self, obj):
        provider = PROVIDERS.get(obj.marketplace)
        return provider.NAME if provider else obj.marketplace


class PricePointSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = PricePoint
        fields = ("price", "checked_at")
