from rest_framework import serializers
from .models import Bill, BillItem
from apps.menu.models import MenuItem

class BillItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())

    class Meta:
        model = BillItem
        fields = ['id', 'item', 'item_name', 'quantity', 'price']
        read_only_fields = ['price']

class BillSerializer(serializers.ModelSerializer):
    items = BillItemSerializer(many=True)
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Bill
        fields = ['id', 'room', 'created_by', 'created_at', 'total_amount', 'items']
        read_only_fields = ['total_amount', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        bill = Bill.objects.create(**validated_data)
        total = 0

        for item_data in items_data:
            menu_item = item_data['item']
            quantity = item_data.get('quantity', 1)
            item_price = menu_item.price  # Pull price from MenuItem model
            total_price = item_price * quantity
            total += total_price

            BillItem.objects.create(
                bill=bill,
                item=menu_item,
                quantity=quantity,
                price=total_price
            )

        bill.total_amount = total
        bill.save()
        return bill

