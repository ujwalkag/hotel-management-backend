from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'orders', views.KitchenDisplayViewSet, basename='kitchen-order')
router.register(r'items', views.KitchenItemStatusViewSet, basename='kitchen-item')
router.register(r'audio', views.AudioAlertViewSet, basename='audio-alert')

urlpatterns = [
    path('', include(router.urls)),
]
