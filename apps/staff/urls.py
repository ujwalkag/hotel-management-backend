from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.StaffProfileViewSet, basename='staff-profile')
router.register(r'attendance', views.AttendanceRecordViewSet, basename='attendance')
router.register(r'advances', views.AdvancePaymentViewSet, basename='advance')

urlpatterns = [
    path('', include(router.urls)),
]
