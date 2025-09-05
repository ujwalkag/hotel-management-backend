from rest_framework import serializers
from .models import RestaurantTable, TableOrder, OrderItem, KitchenDisplayItem
from apps.menu.models import MenuItem

# Main Table Serializer (matches import name in views.py)
class TableSerializer(serializers.ModelSerializer):
    active_orders_count = serializers.ReadOnlyField()
    current_order = serializers.SerializerMethodField()

    class Meta:
        model = RestaurantTable
        fields = ['id', 'table_number', 'capacity', 'location', 'is_active', 
                 'is_occupied', 'active_orders_count', 'current_order', 'created_at']

    def get_current_order(self, obj):
        current = obj.current_order
        if current:
            return {
                'id': current.id,
                'order_number': current.order_number,
                'status': current.status,
                'customer_name': current.customer_name,
                'total_amount': str(current.total_amount)
            }
        return None

# Alias for consistency
RestaurantTableSerializer = TableSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name_en', read_only=True)
    menu_item_name_hi = serializers.CharField(source='menu_item.name_hi', read_only=True)
    total_price = serializers.ReadOnlyField()
    preparation_time_minutes = serializers.ReadOnlyField()
    menu_item = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'menu_item_name_hi', 'quantity', 
                 'price', 'status', 'special_instructions', 'total_price', 'order_time',
                 'preparation_started', 'ready_time', 'served_time', 'preparation_time_minutes']

    def get_menu_item(self, obj):
        if obj.menu_item:
            return {
                'id': obj.menu_item.id,
                'name_en': obj.menu_item.name_en,
                'name_hi': getattr(obj.menu_item, 'name_hi', ''),
                'price': float(obj.menu_item.price)
            }
        return None

class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['menu_item', 'quantity', 'special_instructions']

    def validate_menu_item(self, value):
        if not value.available:
            raise serializers.ValidationError("This menu item is not available")
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

# Main Order Serializer (matches import name in views.py)
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    table_location = serializers.CharField(source='table.location', read_only=True)
    waiter_name = serializers.CharField(source='waiter.email', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = TableOrder
        fields = ['id', 'order_number', 'table', 'table_number', 'table_location', 
                 'waiter', 'waiter_name', 'customer_name', 'customer_phone', 
                 'customer_count', 'status', 'special_instructions', 'total_amount', 
                 'items', 'items_count', 'created_at', 'updated_at', 'completed_at']
        read_only_fields = ['order_number', 'total_amount']

    def get_items_count(self, obj):
        return obj.items.count()

# Alias for consistency
TableOrderSerializer = OrderSerializer

class TableOrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)

    class Meta:
        model = TableOrder
        fields = ['table', 'customer_name', 'customer_phone', 'customer_count',
                 'special_instructions', 'items']

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")
        return value

    def validate_customer_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Customer name is required")
        return value.strip()

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = TableOrder.objects.create(**validated_data)

        for item_data in items_data:
            menu_item = item_data['menu_item']
            OrderItem.objects.create(
                table_order=order,
                menu_item=menu_item,
                price=menu_item.price,
                **item_data
            )

        # Mark table as occupied
        order.table.is_occupied = True
        order.table.save()

        return order

class KitchenDisplaySerializer(serializers.ModelSerializer):
    order_item = OrderItemSerializer(read_only=True)
    table_number = serializers.CharField(source='order_item.table_order.table.table_number', read_only=True)
    table_location = serializers.CharField(source='order_item.table_order.table.location', read_only=True)
    order_number = serializers.CharField(source='order_item.table_order.order_number', read_only=True)
    customer_name = serializers.CharField(source='order_item.table_order.customer_name', read_only=True)
    customer_count = serializers.IntegerField(source='order_item.table_order.customer_count', read_only=True)
    waiter_name = serializers.CharField(source='order_item.table_order.waiter.email', read_only=True)
    time_since_order = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = KitchenDisplayItem
        fields = ['id', 'order_item', 'table_number', 'table_location', 'order_number', 
                 'customer_name', 'customer_count', 'waiter_name', 'display_time', 
                 'estimated_prep_time', 'is_priority', 'is_highlighted', 
                 'time_since_order', 'is_overdue', 'kitchen_notes']

class OrderItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['status', 'special_instructions']

    def validate_status(self, value):
        valid_statuses = ['pending', 'preparing', 'ready', 'served', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}")
        return value

# ============================================
# MOBILE WAITER SERIALIZERS - ADDED
# ============================================

class MobileTableSerializer(serializers.ModelSerializer):
    active_orders_count = serializers.ReadOnlyField()
    current_order = serializers.SerializerMethodField()

    class Meta:
        model = RestaurantTable
        fields = ['id', 'table_number', 'capacity', 'location', 'is_active', 
                 'is_occupied', 'active_orders_count', 'current_order']

    def get_current_order(self, obj):
        current = obj.current_order
        if current:
            return {
                'id': current.id,
                'order_number': current.order_number,
                'status': current.status,
                'customer_name': current.customer_name,
                'total_amount': str(current.total_amount)
            }
        return None

class MobileOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    table_number = serializers.CharField(source='table.table_number', read_only=True)

    class Meta:
        model = TableOrder
        fields = ['id', 'order_number', 'table_number', 'customer_name', 
                 'customer_phone', 'customer_count', 'status', 'total_amount', 
                 'items', 'created_at']
