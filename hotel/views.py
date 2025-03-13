from rest_framework import viewsets, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .models import Room, Booking, RestaurantOrder
from .serializers import RoomSerializer, BookingSerializer, OrderSerializer, UserSerializer

User = get_user_model()

class RegisterView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

class OrderViewSet(viewsets.ModelViewSet):
    queryset = RestaurantOrder.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
