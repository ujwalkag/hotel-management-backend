# apps/staff/urls.py - STAFF MANAGEMENT URLS

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StaffDepartmentViewSet, 
    StaffEmployeeViewSet, 
    StaffAttendanceViewSet,
    StaffPayrollViewSet, 
    StaffAdvancePaymentViewSet
)

router = DefaultRouter()
router.register(r'departments', StaffDepartmentViewSet)
router.register(r'employees', StaffEmployeeViewSet)
router.register(r'attendance', StaffAttendanceViewSet)
router.register(r'payroll', StaffPayrollViewSet)
router.register(r'advances', StaffAdvancePaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

