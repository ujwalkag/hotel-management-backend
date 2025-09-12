# apps/staff_management/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('employees', views.EmployeeViewSet, basename='employees')
router.register('designations', views.DesignationViewSet, basename='designations')
router.register('attendance', views.AttendanceViewSet, basename='attendance')
router.register('payments', views.MonthlyPaymentViewSet, basename='payments')

urlpatterns = [
    path('', include(router.urls)),
    path('attendance-sheet/', views.attendance_sheet, name='attendance-sheet'),
    path('mark-attendance/', views.mark_attendance, name='mark-attendance'),
    path('payroll-summary/', views.payroll_summary, name='payroll-summary'),
    path('employee/<int:employee_id>/attendance-history/', views.employee_attendance_history, name='employee-attendance-history'),
    path('record-payment/', views.record_monthly_payment, name='record-payment'),
]

