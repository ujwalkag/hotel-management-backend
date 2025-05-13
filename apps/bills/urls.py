from django.urls import path
from .views import  DailySalesView, BillSummaryView

urlpatterns = [
    #path('restaurant/', CreateRestaurantBillView.as_view(), name='create-restaurant-bill'),
    #path('room/', CreateRoomBillView.as_view(), name='create-room-bill'),
    #path('history/', BillHistoryView.as_view(), name='bill-history'),
    path('summary/', BillSummaryView.as_view(), name='bill-summary'),
    path("daily-sales/", DailySalesView.as_view(), name="daily-sales"), 
    ]

