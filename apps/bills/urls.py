# apps/bills/urls.py - COMPLETE UPDATED VERSION
from . import views
from django.urls import path
from .analytics import BillHistoryView, BillAnalyticsView, BillSummaryView
from .views import (
    CreateRestaurantBillView,
    CreateRoomBillView,
    BillPDFView,
    BillDetailView,
    DailyBillReportView,
    # ENHANCED BILLING FUNCTIONS - ADDED
    get_orders_ready_for_billing,
    generate_bill_from_order,
)

urlpatterns = [
    path("create/restaurant/", CreateRestaurantBillView.as_view(), name="create-restaurant-bill"),
    path("create/room/", CreateRoomBillView.as_view(), name="create-room-bill"),
    path("summary/", BillSummaryView.as_view(), name="bill-summary"),
    path("analytics/", BillAnalyticsView.as_view()),
    path("history/", BillHistoryView.as_view(), name="bill-history"),
    path("<int:pk>/pdf/", BillPDFView.as_view(), name="bill-pdf"),
    path("<int:pk>/", BillDetailView.as_view(), name="bill-detail"),
    path("daily-report/", DailyBillReportView.as_view(), name="daily-report"),
    # ENHANCED BILLING ENDPOINTS - ADDED
    path("orders_ready_for_billing/", get_orders_ready_for_billing, name="orders-ready-billing"),
    path("generate_bill_from_order/", generate_bill_from_order, name="generate-bill-from-order"),
]

