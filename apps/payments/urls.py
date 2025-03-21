from django.urls import path
from . import views

urlpatterns = [
    path('stripe/', views.stripe_payment, name='stripe_payment'),
    path('razorpay/', views.razorpay_payment, name='razorpay_payment'),
]
