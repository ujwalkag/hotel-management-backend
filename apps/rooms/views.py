from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Room, RoomBooking
from .serializers import RoomSerializer, RoomBookingSerializer

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

class RoomBookingViewSet(viewsets.ModelViewSet):
    queryset = RoomBooking.objects.all()
    serializer_class = RoomBookingSerializer
    permission_classes = [IsAuthenticated]

