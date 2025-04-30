# apps/bills/urls.py
from django.urls import path
from .views import CreateRestaurantBillView, CreateRoomBillView, BillHistoryView

urlpatterns = [
    path("restaurant/", CreateRestaurantBillView.as_view(), name="create-restaurant-bill"),
    path("room/", CreateRoomBillView.as_view(), name="create-room-bill"),
    path("history/", BillHistoryView.as_view(), name="bill-history"),  # ✅ Add this
]

