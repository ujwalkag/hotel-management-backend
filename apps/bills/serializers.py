from rest_framework import serializers
from .models import Bill, BillItem

class BillItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillItem
        fields = ['item_name', 'quantity', 'price']

class BillSerializer(serializers.ModelSerializer):
    items = BillItemSerializer(many=True)

    class Meta:
        model = Bill
        fields = ['id', 'bill_type', 'created_at', 'total_amount', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        bill = Bill.objects.create(**validated_data)

        for item_data in items_data:
            BillItem.objects.create(bill=bill, **item_data)
        
        return bill

