from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from .models import MenuItem, RoomService, Order, Category, Room
from .serializers import (
    MenuItemSerializer,
    RoomServiceSerializer,
    OrderSerializer,
    CategorySerializer,
    RoomSerializer
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

class RoomServiceViewSet(viewsets.ModelViewSet):
    queryset = RoomService.objects.all()
    serializer_class = RoomServiceSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        order_data = request.data
        order_type = order_data.get('order_type')
        items = order_data.get('items', [])
        room_services = order_data.get('room_service', [])

        order = Order.objects.create(order_type=order_type)
        order.items.set(MenuItem.objects.filter(id__in=items))
        order.room_service.set(RoomService.objects.filter(id__in=room_services))
        order.calculate_total_price()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# ✅ NEW: Room ViewSet to handle /api/rooms/
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

