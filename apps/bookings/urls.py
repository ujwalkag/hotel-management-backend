from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, MenuItemViewSet,
    RoomServiceViewSet, OrderViewSet,
    RoomViewSet  # ✅ Add this
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'menu-items', MenuItemViewSet)
router.register(r'room-services', RoomServiceViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'rooms', RoomViewSet)  # ✅ this enables /api/bookings/rooms/

urlpatterns = [
    path('', include(router.urls)),
]

