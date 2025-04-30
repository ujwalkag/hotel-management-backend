from django.urls import path
from .views import (
    DashboardHomeView,
    OrderStatsView,
    RevenueStatsView,
    BestSellingItemsView,
    SalesSummaryView
)

urlpatterns = [
    path('', DashboardHomeView.as_view(), name='dashboard-home'),
    path('summary/', SalesSummaryView.as_view(), name='sales-summary'),
    path('orders/', OrderStatsView.as_view(), name='order-stats'),
    path('revenue/', RevenueStatsView.as_view(), name='revenue-stats'),
    path('top-items/', BestSellingItemsView.as_view(), name='best-selling-items'),
    #path("all-orders/", AllOrdersView.as_view(), name="all-orders"),
]

