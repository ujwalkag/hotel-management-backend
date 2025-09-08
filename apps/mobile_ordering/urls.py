from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RestaurantTableViewSet, WaiterOrderViewSet, 
    KitchenOrderViewSet, MenuItemViewSet
)

router = DefaultRouter()
router.register(r'tables', RestaurantTableViewSet)
router.register(r'orders', WaiterOrderViewSet)
router.register(r'kitchen-orders', KitchenOrderViewSet)
router.register(r'menu-items', MenuItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
