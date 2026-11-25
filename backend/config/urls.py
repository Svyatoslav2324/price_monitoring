from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", lambda request: JsonResponse({"status": "ok"})),
    path("api/auth/", include("modules.accounts.urls")),
    path("api/products/", include("modules.products.urls")),
    path("api/trackings/", include("modules.tracking.urls")),
    path("api/marketplaces/", include("modules.marketplaces.urls")),
]
