# apps/inventory/urls.py - ENHANCED VERSION
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.InventoryCategoryViewSet, basename='category')
router.register(r'entries', views.InventoryEntryViewSet, basename='entry')
router.register(r'budgets', views.SpendingBudgetViewSet, basename='budget')

urlpatterns = [
    path('', include(router.urls)),

    # Additional endpoints for enhanced features
    path('spending-comparison/', views.spending_comparison, name='spending-comparison'),
]
