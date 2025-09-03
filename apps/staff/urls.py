# apps/staff/urls.py - Complete Staff Management URLs
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaffProfileViewSet, AttendanceViewSet
from . import views

router = DefaultRouter()
router.register(r'profiles', StaffProfileViewSet, basename='staff-profiles')
router.register(r'attendance', AttendanceViewSet, basename='staff-attendance')

urlpatterns = [
    path('', include(router.urls)),
]

