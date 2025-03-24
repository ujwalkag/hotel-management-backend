from django.urls import path
from . import views
from .views import PaymentStatusView

urlpatterns = [
    path('stripe/', views.stripe_payment, name='stripe_payment'),
    path('razorpay/', views.razorpay_payment, name='razorpay_payment'),
    path('payment-status/', PaymentStatusView.as_view(), name='payment_status'),  # ✅ Add this line
]

