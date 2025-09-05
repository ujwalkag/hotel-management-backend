from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.StaffProfileViewSet, basename='staff-profile')
router.register(r'attendance', views.AttendanceRecordViewSet, basename='attendance')

urlpatterns = [
    path('', include(router.urls)),
    
    # Existing endpoints
    path('mark_attendance/', views.mark_attendance, name='mark-attendance'),
    path('generate_payroll/', views.generate_payroll, name='generate-payroll'),
    path('attendance_summary/', views.attendance_summary, name='attendance-summary'),
    
    # NEW Payroll staff endpoints
    path('payroll-staff/', views.payroll_staff_management, name='payroll-staff-management'),
    path('payroll-staff/<int:staff_id>/', views.delete_payroll_staff, name='delete-payroll-staff'),
]
