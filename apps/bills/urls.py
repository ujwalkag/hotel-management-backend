# apps/bills/urls.py - FIXED URL ORDERING
from django.urls import path, include
from .analytics import BillHistoryView, BillAnalyticsView, BillSummaryView
from .views import (
    CreateRestaurantBillView,
    CreateRoomBillView,
    BillDetailView,
    BillPDFView,
    DailyBillReportView,
    get_orders_ready_for_billing,
    generate_bill_from_order
)

urlpatterns = [
    # SPECIFIC patterns FIRST (must come before generic patterns)
    path('create/restaurant/', CreateRestaurantBillView.as_view(), name='create-restaurant-bill'),
    path('create/room/', CreateRoomBillView.as_view(), name='create-room-bill'),
    path('daily-report/', DailyBillReportView.as_view(), name='daily-report'),
    path('summary/', BillSummaryView.as_view(), name='bill-summary'),
    path('history/', BillHistoryView.as_view(), name='bill-history'),
    path('orders/ready/', get_orders_ready_for_billing, name='orders-ready-billing'),
    path('generate-from-order/', generate_bill_from_order, name='generate-from-order'),
    
    # GENERIC patterns LAST (these can match anything)
    path('<int:pk>/', BillDetailView.as_view(), name='bill-detail'),
    path('<int:pk>/pdf/', BillPDFView.as_view(), name='bill-pdf'),
    
    # Enhanced billing system - include all enhanced URLs
    path('', include('apps.bills.enhanced_urls')),
]

