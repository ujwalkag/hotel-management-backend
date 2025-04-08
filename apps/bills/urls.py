from django.urls import path
from .views import BillCreateView, BillListView

urlpatterns = [
    path('create/', BillCreateView.as_view(), name='bill-create'),
    path('list/', BillListView.as_view(), name='bill-list'),
]

