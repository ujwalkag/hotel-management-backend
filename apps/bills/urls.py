from django.urls import path
from .views import BillCreateView, BillListView, BillInvoicePDFView

urlpatterns = [
    path('create/', BillCreateView.as_view(), name='bill-create'),
    path('list/', BillListView.as_view(), name='bill-list'),
    path('<int:pk>/invoice/', BillInvoicePDFView.as_view(), name='bill-invoice'),
]

