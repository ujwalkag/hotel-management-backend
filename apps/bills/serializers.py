from rest_framework import serializers
from .models import Bill, BillItem
from apps.menu.models import MenuItem
from apps.bookings.models import RoomBooking
from decimal import Decimal

class BillItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='menu_item.name', read_only=True)
    price = serializers.DecimalField(source='menu_item.price', max_digits=10, decimal_places=2, read_only=True)
    menu_item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())

    class Meta:
        model = BillItem
        fields = ['id', 'menu_item', 'item_name', 'price', 'quantity']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value


class BillSerializer(serializers.ModelSerializer):
    items = BillItemSerializer(many=True, write_only=True)
    item_details = BillItemSerializer(source='billitem_set', many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Bill
        fields = [
            'id',
            'bill_type',
            'customer_name',
            'room_number',
            'booking',  # Used in case of room bills
            'items',  # For write (input)
            'item_details',  # For read
            'total_amount',
            'created_at',
        ]

    def validate(self, data):
        bill_type = data.get('bill_type')
        items = data.get('items', [])
        booking = data.get('booking')

        if bill_type == 'restaurant':
            if not items:
                raise serializers.ValidationError("Items are required for restaurant bills.")
        elif bill_type == 'room':
            if not booking:
                raise serializers.ValidationError("Booking is required for room bills.")
        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        bill = Bill.objects.create(**validated_data)

        total = Decimal('0.00')

        for item_data in items_data:
            menu_item = item_data['menu_item']
            quantity = item_data['quantity']
            subtotal = menu_item.price * quantity
            BillItem.objects.create(bill=bill, menu_item=menu_item, quantity=quantity)
            total += subtotal

        # Add room charges if it's a room bill
        if bill.bill_type == 'room' and bill.booking:
            room_total = bill.booking.total_price
            if room_total:
                total += room_total

        bill.total_amount = total
        bill.save()

        return bill

