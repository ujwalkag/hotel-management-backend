# apps/staff/urls.py - COMPLETE VERSION
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'profiles', views.StaffProfileViewSet, basename='staffprofile')
router.register(r'attendance', views.AttendanceViewSet, basename='attendance')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]

