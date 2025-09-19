# apps/restaurant/urls.py - COMPLETE Enhanced URL patterns with ALL Functionality
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tables', views.TableViewSet, basename='table')
router.register(r'menu-categories', views.MenuCategoryViewSet, basename='menu-category')
router.register(r'menu-items', views.MenuItemViewSet, basename='menu-item')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-sessions', views.OrderSessionViewSet, basename='order-session')
router.register(r'kds-settings', views.KitchenDisplaySettingsViewSet, basename='kds-settings')

# Enhanced billing router for frontend compatibility
billing_router = DefaultRouter()
billing_router.register(r'enhanced', views.EnhancedBillingViewSet, basename='enhanced-billing')

urlpatterns = [
    # Main router URLs
    path('', include(router.urls)),
    
    # Enhanced billing URLs for frontend compatibility
    path('bills/', include(billing_router.urls)),
    
    # Dashboard and statistics endpoints
    path('dashboard-stats/', views.dashboard_stats, name='dashboard-stats'),
    path('system-health/', views.system_health, name='system-health'),
    
    # Menu and ordering endpoints
    path('menu-for-ordering/', views.menu_for_ordering, name='menu-for-ordering'),
    path('quick-order/', views.quick_order, name='quick-order'),
    
    # KDS specific endpoints
    path('kds/connection-status/', views.kds_connection_status, name='kds-connection-status'),
    path('kds/offline-orders/', views.process_offline_orders_endpoint, name='process-offline-orders'),
    path('kds/heartbeat/', views.kds_heartbeat, name='kds-heartbeat'),
    
    # Reports and exports
    path('exports/orders-csv/', views.export_orders_csv, name='export-orders-csv'),
]
