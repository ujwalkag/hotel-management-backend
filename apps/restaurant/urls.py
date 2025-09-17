# apps/restaurant/urls.py - Enhanced URL patterns with Admin Functionality
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
# Under router for orders:
#router.register(r'orders/(?P<pk>[^/.]+)/bulk-create', views.OrderViewSet, basename='order-bulk-for-table')

# Admin billing router
admin_router = DefaultRouter()
admin_router.register(r'admin-billing', views.AdminBillingViewSet, basename='admin-billing')

urlpatterns = [
    # Main router URLs
    path('', include(router.urls)),
    
    # Admin router URLs  
    path('', include(admin_router.urls)),

    # Dashboard and statistics endpoints
    path('dashboard-stats/', views.dashboard_stats, name='dashboard-stats'),
    path('system-health/', views.system_health, name='system-health'),
    
    # Menu and ordering endpoints
    path('menu-for-ordering/', views.menu_for_ordering, name='menu-for-ordering'),
    path('quick-order/', views.quick_order, name='quick-order'),
    
    # Enhanced table management endpoints
    path('tables/<int:table_id>/orders/', views.table_orders, name='table-orders'),
    path('tables/<int:table_id>/session/', views.table_session, name='table-session'),
    path('tables/bulk-update/', views.bulk_update_tables, name='bulk-update-tables'),
    
    # Enhanced order management endpoints
    path('orders/bulk-status-update/', views.bulk_order_status_update, name='bulk-order-status-update'),
    path('orders/by-table/<int:table_id>/', views.orders_by_table, name='orders-by-table'),
    path('orders/<int:order_id>/history/', views.order_status_history, name='order-status-history'),
    
    # KDS specific endpoints
    path('kds/connection-status/', views.kds_connection_status, name='kds-connection-status'),
    path('kds/offline-orders/', views.process_offline_orders, name='process-offline-orders'),
    path('kds/heartbeat/', views.kds_heartbeat, name='kds-heartbeat'),
    
    # Billing and receipt endpoints
    path('billing/generate-receipt/<uuid:session_id>/', views.generate_receipt, name='generate-receipt'),
    path('billing/print-receipt/<uuid:session_id>/', views.print_receipt, name='print-receipt'),
    path('billing/void-session/<uuid:session_id>/', views.void_session, name='void-session'),
    
    # Admin specific endpoints
    path('admin/tables/analytics/', views.admin_table_analytics, name='admin-table-analytics'),
    path('admin/orders/analytics/', views.admin_order_analytics, name='admin-order-analytics'),
    path('admin/billing/reports/', views.admin_billing_reports, name='admin-billing-reports'),
    path('admin/system/cleanup/', views.admin_system_cleanup, name='admin-system-cleanup'),
    
    # Reports and exports
    path('reports/daily-sales/', views.daily_sales_report, name='daily-sales-report'),
    path('reports/table-utilization/', views.table_utilization_report, name='table-utilization-report'),
    path('reports/menu-performance/', views.menu_performance_report, name='menu-performance-report'),
    path('exports/orders-csv/', views.export_orders_csv, name='export-orders-csv'),
    path('exports/sessions-csv/', views.export_sessions_csv, name='export-sessions-csv'),
    
    # Mobile ordering endpoints
    path('mobile/tables/available/', views.mobile_available_tables, name='mobile-available-tables'),
    path('mobile/menu/', views.mobile_menu, name='mobile-menu'),
    path('mobile/order/create/', views.mobile_create_order, name='mobile-create-order'),
    path('mobile/order/status/<str:order_number>/', views.mobile_order_status, name='mobile-order-status'),
]
