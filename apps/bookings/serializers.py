from rest_framework import serializers
from .models import MenuItem, RoomService, Order, Category
# apps/bookings/serializers.py
#from rest_framework import serializers
from .models import Room  # Ensure Room is imported

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'price', 'category', 'category_name', 'availability']


class RoomServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomService
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)
    room_service = RoomServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_type', 'items', 'room_service', 'total_price', 'created_at']

