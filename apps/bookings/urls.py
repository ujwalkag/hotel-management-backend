from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MenuItemViewSet, RoomServiceViewSet, OrderViewSet, CategoryViewSet

router = DefaultRouter()
router.register('menu-items', MenuItemViewSet, basename='menu-items')
router.register('room-services', RoomServiceViewSet, basename='room-services')
router.register('orders', OrderViewSet, basename='orders')
router.register('categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
]

