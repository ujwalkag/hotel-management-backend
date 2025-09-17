# apps/bills/urls.py - UPDATED TO INCLUDE ENHANCED BILLING
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
    # Regular billing endpoints
    path('create/restaurant/', CreateRestaurantBillView.as_view(), name='create-restaurant-bill'),
    path('create/room/', CreateRoomBillView.as_view(), name='create-room-bill'),
    path('<int:pk>/', BillDetailView.as_view(), name='bill-detail'),
    path('<int:pk>/pdf/', BillPDFView.as_view(), name='bill-pdf'),
    path('daily-report/', DailyBillReportView.as_view(), name='daily-report'),
    path('summary/', BillSummaryView.as_view(), name='bill-summary'),
    path('history/', BillHistoryView.as_view(), name='bill-history'),
    # Orders ready for billing
    path('orders/ready/', get_orders_ready_for_billing, name='orders-ready-billing'),
    path('generate-from-order/', generate_bill_from_order, name='generate-from-order'),

    # Enhanced billing system - include all enhanced URLs
    path('', include('apps.bills.enhanced_urls')),
]

