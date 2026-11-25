from rest_framework.routers import SimpleRouter

from .views import TrackingViewSet

router = SimpleRouter()
router.register("", TrackingViewSet, basename="tracking")
urlpatterns = router.urls
