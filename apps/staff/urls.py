# apps/staff/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.StaffProfileViewSet)
router.register(r'attendance', views.AttendanceViewSet)
router.register(r'payments', views.PaymentRecordViewSet)
router.register(r'advances', views.AdvancePaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
