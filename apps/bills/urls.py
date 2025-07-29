from . import views
from django.urls import path
from .analytics import BillHistoryView, BillAnalyticsView, BillSummaryView
from .views import (
    CreateRestaurantBillView,
    CreateRoomBillView,
    BillPDFView,
    BillDetailView,
    DailyBillReportView,
)

urlpatterns = [
    path("create/restaurant/", CreateRestaurantBillView.as_view(), name="create-restaurant-bill"),
    path("create/room/", CreateRoomBillView.as_view(), name="create-room-bill"),
    path("summary/", BillSummaryView.as_view(), name="bill-summary"),
    path("analytics/", BillAnalyticsView.as_view()),
    path("history/", BillHistoryView.as_view(), name="bill-history"),  # ✅ ADD THIS LINE
    path("<int:pk>/pdf/", BillPDFView.as_view(), name="bill-pdf"),
    path("<int:pk>/", BillDetailView.as_view(), name="bill-detail"),
    path("daily-report/", DailyBillReportView.as_view(), name="daily-report"),
]

