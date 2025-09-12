from rest_framework import serializers
from .models import Room, RoomBooking, BookingItem

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'type_en', 'type_hi', 'price_per_day', 'price_per_hour']

class BookingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingItem
        fields = ['room', 'quantity']

class RoomBookingSerializer(serializers.ModelSerializer):
    items = BookingItemSerializer(many=True)

    class Meta:
        model = RoomBooking
        fields = ['id', 'check_in', 'check_out', 'aadhaar_card', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        booking = RoomBooking.objects.create(**validated_data)
        for item in items_data:
            BookingItem.objects.create(booking=booking, **item)
        return booking

