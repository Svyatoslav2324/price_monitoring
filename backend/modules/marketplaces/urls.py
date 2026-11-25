from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .registry import PROVIDERS


@api_view(["GET"])
def marketplace_list(request):
    return Response([{"code": p.CODE, "name": p.NAME, "hosts": p.HOSTS} for p in PROVIDERS.values()])


urlpatterns = [
    path("", marketplace_list),
    path("wildberries/", include("modules.marketplaces.wildberries.urls")),
]
