from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('order-summary/', views.order_summary, name='order_summary'),
    path('sales-overview/', views.sales_overview, name='sales_overview'),
    path('top-items/', views.top_items, name='top_items'),
    path('revenue-analytics/', views.revenue_analytics, name='revenue_analytics'),
]

