from django.urls import path
from .views import (
    CreateRestaurantBillView,
    CreateRoomBillView,
    BillHistoryView,
    BillSummaryView
)

urlpatterns = [
    path("create/restaurant/", CreateRestaurantBillView.as_view(), name="create-restaurant-bill"),
    path("create/room/", CreateRoomBillView.as_view(), name="create-room-bill"),
    path("history/", BillHistoryView.as_view(), name="bill-history"),
    path("summary/", BillSummaryView.as_view(), name="bill-summary"),
]

