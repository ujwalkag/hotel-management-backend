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
router.register(r'departments', StaffDepartmentViewSet, basename='staff-department')
router.register(r'employees', StaffEmployeeViewSet, basename='staff-employee')
router.register(r'attendance', StaffAttendanceViewSet, basename='staff-attendance')
router.register(r'payroll', StaffPayrollViewSet, basename='staff-payroll')
router.register(r'advances', StaffAdvancePaymentViewSet, basename='staff-advance')

urlpatterns = [
    path('', include(router.urls)),
]
