from django.db import IntegrityError, transaction
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from modules.marketplaces.errors import as_api_error
from modules.products.services import get_or_create_product

from .models import Tracking
from .serializers import TrackingCreateSerializer, TrackingSerializer


class AlreadyTracked(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Вы уже отслеживаете этот товар"
    default_code = "already_tracked"


class TrackingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TrackingSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return Tracking.objects.filter(user=self.request.user).select_related("product")

    def create(self, request):
        payload = TrackingCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        with as_api_error("url"):
            product = get_or_create_product(data["url"])
        try:
            with transaction.atomic():
                tracking = Tracking.objects.create(
                    user=request.user,
                    product=product,
                    check_interval=data["check_interval"],
                    target_price=data["target_price"],
                )
        except IntegrityError:
            raise AlreadyTracked()
        return Response(TrackingSerializer(tracking).data, status=status.HTTP_201_CREATED)
