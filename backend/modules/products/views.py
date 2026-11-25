from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import PricePointSerializer, ProductSerializer


def _user_product(request, pk) -> Product:
    # Политика доступа: товар виден только тем, кто его отслеживает
    return get_object_or_404(Product.objects.filter(trackings__user=request.user).distinct(), pk=pk)


class ProductDetailView(APIView):
    def get(self, request, pk: int):
        product = _user_product(request, pk)
        tracking = product.trackings.get(user=request.user)
        data = ProductSerializer(product).data
        data["tracking"] = {"id": tracking.id, "target_price": float(tracking.target_price), "status": tracking.status}
        return Response(data)


class ProductHistoryView(APIView):
    MAX_DAYS = 365

    def get(self, request, pk: int):
        product = _user_product(request, pk)
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            days = 0
        if not 1 <= days <= self.MAX_DAYS:
            raise ValidationError({"days": [f"Целое число от 1 до {self.MAX_DAYS}"]})

        points = product.prices.filter(checked_at__gte=timezone.now() - timedelta(days=days))
        return Response(PricePointSerializer(points, many=True).data)
