from rest_framework import serializers
from .models import RoomService

class RoomServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomService
        fields = ['id', 'name', 'description', 'price', 'available', 'image', 'created_at', 'updated_at']

