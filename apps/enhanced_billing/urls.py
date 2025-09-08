
# apps/enhanced_billing/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnhancedBillViewSet, BillPaymentRecordViewSet, BillingSessionViewSet
)

router = DefaultRouter()
router.register(r'bills', EnhancedBillViewSet)
router.register(r'payments', BillPaymentRecordViewSet)
router.register(r'sessions', BillingSessionViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]

