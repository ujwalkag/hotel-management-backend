from rest_framework import viewsets, permissions
from .models import Room
from .serializers import RoomSerializer
from apps.bills.permissions import IsAdminOrStaff

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAdminOrStaff]

