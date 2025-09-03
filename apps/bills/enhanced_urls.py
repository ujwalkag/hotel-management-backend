# apps/bills/enhanced_urls.py - Enhanced Billing URLs  
from django.urls import path
from .views import get_orders_ready_for_billing, generate_bill_from_order

enhanced_billing_urls = [
    path('orders_ready_for_billing/', get_orders_ready_for_billing, name='orders-ready-billing'),
    path('generate_bill_from_order/', generate_bill_from_order, name='generate-bill-from-order'),
]
