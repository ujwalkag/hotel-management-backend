# apps/inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.InventoryCategoryViewSet, basename='category')
router.register(r'entries', views.InventoryEntryViewSet, basename='entry')

urlpatterns = [
    path('', include(router.urls)),
]

