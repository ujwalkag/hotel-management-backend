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

legacy_menu_patterns = [
    path('items/', views.menu_items_legacy_crud, name='menu-items-legacy'),
    path('items/<int:pk>/', views.menu_item_detail_legacy, name='menu-item-detail-legacy'),
    path('categories/', views.menu_categories_legacy_crud, name='menu-categories-legacy'),
]
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
    path('tables/<int:pk>/manage_orders/', views.TableViewSet.as_view({'get': 'manage_orders', 'post': 'manage_orders'}), name='table-manage-orders'),
    path('orders/<int:pk>/admin_modify/', views.OrderViewSet.as_view({'post': 'admin_modify'}), name='order-admin-modify'),
    path('orders/admin_bulk_modify/', views.OrderViewSet.as_view({'post': 'admin_bulk_modify'}), name='order-admin-bulk-modify'),
    # REQUIRED: Additional endpoints that your frontend is calling
    path('tables/with_orders/', views.TablesWithOrdersView.as_view(), name='tables-with-orders'),
    path('menu-for-ordering/', views.MenuForOrderingView.as_view(), name='menu-for-ordering'),
    path('dashboard-stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),

    

    
    path('tables/<int:pk>/current_bill/', views.TableViewSet.as_view({'get': 'current_bill'}), name='table-current-bill'),
    path('tables/<int:pk>/complete_billing/', views.TableViewSet.as_view({'post': 'complete_billing'}), name='table-complete-billing'),
    path('orders/bulk_create/', views.OrderViewSet.as_view({'post': 'bulk_create'}), name='order-bulk-create'),
    path('menu/', include(legacy_menu_patterns)),
]
