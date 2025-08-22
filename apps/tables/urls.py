# apps/tables/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tables', views.RestaurantTableViewSet)
router.register(r'orders', views.TableOrderViewSet)
router.register(r'kitchen', views.KitchenDisplayViewSet, basename='kitchen')

urlpatterns = [
    path('', include(router.urls)),
]
