from rest_framework import serializers
from .models import KitchenOrder, KitchenItemStatus, AudioAlert

class KitchenOrderSerializer(serializers.ModelSerializer):
    bill_receipt_number = serializers.CharField(source='bill.receipt_number', read_only=True)
    customer_name = serializers.CharField(source='bill.customer_name', read_only=True)
    table_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    items = serializers.SerializerMethodField()
    time_elapsed = serializers.SerializerMethodField()
    
    class Meta:
        model = KitchenOrder
        fields = '__all__'
        read_only_fields = ['received_at', 'created_at', 'updated_at']

    def get_table_info(self, obj):
        """Extract table information from customer name"""
        customer_name = obj.bill.customer_name
        if 'Table' in customer_name:
            parts = customer_name.split(' - ')
            return parts[0] if parts else customer_name
        return "Takeaway"

    def get_items(self, obj):
        """Get all bill items for this order"""
        items = obj.bill.items.all()
        return [
            {
                'id': item.id,
                'name': item.item_name,
                'quantity': item.quantity,
                'price': item.price,
                'kitchen_status': getattr(item, 'kitchen_status', None)
            }
            for item in items
        ]

    def get_time_elapsed(self, obj):
        """Calculate time elapsed since order received"""
        from datetime import datetime
        if obj.received_at:
            elapsed = datetime.now() - obj.received_at.replace(tzinfo=None)
            return int(elapsed.total_seconds() / 60)  # Return minutes
        return 0

class KitchenItemStatusSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='bill_item.item_name', read_only=True)
    quantity = serializers.IntegerField(source='bill_item.quantity', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = KitchenItemStatus
        fields = '__all__'
        read_only_fields = ['actual_time', 'created_at', 'updated_at']

class AudioAlertSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    
    class Meta:
        model = AudioAlert
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
