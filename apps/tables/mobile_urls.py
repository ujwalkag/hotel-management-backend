# apps/tables/mobile_urls.py - Mobile Waiter URLs
from django.urls import path
from .views import get_tables_layout, create_waiter_order

urlpatterns = [
    path('tables_layout/', get_tables_layout, name='mobile-tables-layout'),
    path('create_order/', create_waiter_order, name='mobile-create-order'),
]

