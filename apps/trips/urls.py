from rest_framework.routers import SimpleRouter

from .views import TripViewSet

router = SimpleRouter()
router.register("", TripViewSet, basename="trip")

urlpatterns = router.urls
