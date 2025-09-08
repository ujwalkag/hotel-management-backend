from rest_framework import serializers
from .models import RestaurantTable, TableSession, WaiterOrder, WaiterOrderItem, KitchenOrder
from apps.menu.models import MenuItem

class RestaurantTableSerializer(serializers.ModelSerializer):
    active_orders_count = serializers.ReadOnlyField()
    current_bill_total = serializers.ReadOnlyField()
    session_duration_minutes = serializers.ReadOnlyField()

    class Meta:
        model = RestaurantTable
        fields = '__all__'

class WaiterOrderSerializer(serializers.ModelSerializer):
    order_items = serializers.SerializerMethodField()
    total_items = serializers.ReadOnlyField()
    wait_time_minutes = serializers.ReadOnlyField()
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    waiter_name = serializers.CharField(source='waiter.get_full_name', read_only=True)

    class Meta:
        model = WaiterOrder
        fields = '__all__'

    def get_order_items(self, obj):
        return WaiterOrderItemSerializer(obj.order_items.all(), many=True).data

class WaiterOrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.ReadOnlyField()
    display_name = serializers.ReadOnlyField()
    menu_item_name = serializers.CharField(source='menu_item.name_en', read_only=True)

    class Meta:
        model = WaiterOrderItem
        fields = '__all__'

class KitchenOrderSerializer(serializers.ModelSerializer):
    order_number = serializers.ReadOnlyField()
    total_items = serializers.ReadOnlyField()
    wait_time_minutes = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    urgency_level = serializers.ReadOnlyField()
    order_items = serializers.SerializerMethodField()

    class Meta:
        model = KitchenOrder
        fields = '__all__'

    def get_order_items(self, obj):
        return WaiterOrderItemSerializer(obj.waiter_order.order_items.all(), many=True).data

class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_en', read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name_en', 'name_hi', 'description_en', 'price', 'available', 'category_name', 'image']
