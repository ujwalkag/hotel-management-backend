from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tables', views.RestaurantTableViewSet, basename='table')
router.register(r'orders', views.TableOrderViewSet, basename='order')
router.register(r'kitchen', views.KitchenDisplayViewSet, basename='kitchen')

urlpatterns = [
    path('', include(router.urls)),
    
    # Mobile waiter endpoints
    path('mobile/tables_layout/', views.get_tables_layout, name='mobile-tables-layout'),
    path('mobile/create_order/', views.create_waiter_order, name='mobile-create-order'),
    
    # Enhanced billing endpoints
    path('active-orders-for-billing/', views.get_active_orders_for_billing, name='active-orders-billing'),
    
    # Kitchen endpoints
    path('kitchen/orders/', views.get_kitchen_orders, name='kitchen-orders'),
    path('kitchen/orders/<int:order_item_id>/update-status/', views.update_kitchen_order_status, name='kitchen-update-status'),
]
