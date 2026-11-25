from rest_framework.response import Response
from rest_framework.views import APIView

from ..errors import as_api_error
from . import client


class ProductPreviewView(APIView):
    """Живой запрос карточки WB без сохранения — для предпросмотра перед добавлением."""

    throttle_scope = "marketplace"

    def get(self, request, nm_id: str):
        with as_api_error():
            snap = client.fetch(nm_id)
        return Response({
            "marketplace": client.CODE,
            "external_id": snap.external_id,
            "url": client.PRODUCT_URL.format(id=snap.external_id),
            "title": snap.title,
            "price": snap.price,
            "in_stock": snap.in_stock,
        })
