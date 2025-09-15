# apps/restaurant/urls.py - URL patterns for Restaurant/KDS System
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

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Additional endpoints
    path('dashboard-stats/', views.dashboard_stats, name='dashboard-stats'),
    path('menu-for-ordering/', views.menu_for_ordering, name='menu-for-ordering'),
    path('quick-order/', views.quick_order, name='quick-order'),
]

