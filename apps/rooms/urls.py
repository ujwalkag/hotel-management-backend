from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomBookingViewSet, RoomViewSet

router = DefaultRouter()
router.register('bookings', RoomBookingViewSet, basename='room-booking')
router.register('types', RoomViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

