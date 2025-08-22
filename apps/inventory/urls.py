# apps/inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.InventoryCategoryViewSet)
router.register(r'items', views.InventoryItemViewSet)
router.register(r'movements', views.StockMovementViewSet)
router.register(r'alerts', views.LowStockAlertViewSet)
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'purchase-orders', views.PurchaseOrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
