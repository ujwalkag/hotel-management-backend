from rest_framework.routers import DefaultRouter
from .views import RoomServiceViewSet

router = DefaultRouter()
router.register(r'', RoomServiceViewSet, basename='room-services')

urlpatterns = router.urls

