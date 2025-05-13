from rest_framework import viewsets, permissions
from .models import RoomService
from .serializers import RoomServiceSerializer
from apps.menu.views import IsAdminOrReadOnly  # Reuse permission class

class RoomServiceViewSet(viewsets.ModelViewSet):
    queryset = RoomService.objects.all().order_by('-created_at')
    serializer_class = RoomServiceSerializer
    permission_classes = [IsAdminOrReadOnly]

