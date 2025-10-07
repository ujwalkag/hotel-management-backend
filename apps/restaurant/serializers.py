# apps/restaurant/serializers.py - Enhanced Serializers
from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from .models import (
    Table, MenuCategory, MenuItem, Order, OrderSession,
    KitchenDisplaySettings, OfflineOrderBackup
)

class MenuCategorySerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuCategory
        fields = [
            'id', 'name', 'name_en', 'name_hi', 'description', 
            'display_order', 'icon', 'is_active', 'items_count', 'created_at'
        ]
    
    def get_items_count(self, obj):
        return obj.items.filter(is_active=True).count()

class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_name_en = serializers.CharField(source='category.name_en', read_only=True)
    category_name_hi = serializers.CharField(source='category.name_hi', read_only=True)
    is_available_status = serializers.BooleanField(source='is_available', read_only=True)
    profit_margin = serializers.FloatField(read_only=True)
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'name_en', 'name_hi', 'description', 
            'description_en', 'description_hi', 'category', 'category_name',
            'category_name_en', 'category_name_hi', 'price', 'cost_price', 
            'availability', 'preparation_time', 'is_veg', 'is_spicy', 
            'allergens', 'image_url', 'display_order', 'is_active', 
            'available', 'is_available_status', 'profit_margin',
            'created_at', 'updated_at'
        ]

class MenuItemCreateSerializer(serializers.ModelSerializer):
    # Frontend compatibility fields
    name_en = serializers.CharField(required=True)
    name_hi = serializers.CharField(required=False, allow_blank=True)
    description_en = serializers.CharField(required=False, allow_blank=True)
    description_hi = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.IntegerField(write_only=True, required=True)
    available = serializers.BooleanField(required=False, default=True)
    
    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'category', 'price', 'cost_price',
            'availability', 'preparation_time', 'is_veg', 'is_spicy',
            'allergens', 'image_url', 'display_order', 'is_active',
            # Frontend compatibility fields
            'name_en', 'name_hi', 'description_en', 'description_hi',
            'category_id', 'available'
        ]
    
    def validate(self, data):
        """Custom validation with Hindi name support"""
        
        # Validate and map category
        category_id = data.get('category_id')
        if not category_id:
            raise serializers.ValidationError({"category": "Category is required"})
        
        try:
            category = MenuCategory.objects.get(id=int(category_id), is_active=True)
            data['category'] = category
        except (MenuCategory.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError({"category": "Invalid category selected"})
        
        # Validate and map names
        name_en = data.get('name_en', '').strip()
        name_hi = data.get('name_hi', '').strip()
        
        if not name_en:
            raise serializers.ValidationError({"name_en": "English name is required"})
        
        # Set main name field
        data['name'] = name_en
        
        # Handle descriptions
        description_en = data.get('description_en', '').strip()
        description_hi = data.get('description_hi', '').strip()
        data['description'] = description_en
        
        # Handle availability
        available = data.get('available', True)
        data['availability'] = 'available' if available else 'out_of_stock'
        data['is_active'] = available
        
        # Validate price
        price = data.get('price')
        if not price or price <= 0:
            raise serializers.ValidationError({"price": "Valid price is required"})
        
        return data
    
    def create(self, validated_data):
        """Create with proper field handling"""
        # Extract frontend fields
        name_en = validated_data.pop('name_en', '')
        name_hi = validated_data.pop('name_hi', '')
        description_en = validated_data.pop('description_en', '')
        description_hi = validated_data.pop('description_hi', '')
        validated_data.pop('category_id', None)
        validated_data.pop('available', None)
        
        # Create the item
        item = super().create(validated_data)
        
        # Set compatibility fields
        item.name_en = name_en
        item.name_hi = name_hi or name_en
        item.description_en = description_en
        item.description_hi = description_hi or description_en
        item.available = item.is_active
        item.save()
        
        return item
    
    def update(self, instance, validated_data):
        """Update with proper field handling"""
        # Extract frontend fields
        name_en = validated_data.pop('name_en', instance.name_en)
        name_hi = validated_data.pop('name_hi', instance.name_hi)
        description_en = validated_data.pop('description_en', instance.description_en)
        description_hi = validated_data.pop('description_hi', instance.description_hi)
        validated_data.pop('category_id', None)
        validated_data.pop('available', None)
        
        # Update the item
        item = super().update(instance, validated_data)
        
        # Update compatibility fields
        item.name_en = name_en
        item.name_hi = name_hi or name_en
        item.description_en = description_en
        item.description_hi = description_hi or description_en
        item.available = item.is_active
        item.save()
        
        return item

class OrderSerializer(serializers.ModelSerializer):
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_category = serializers.CharField(source='menu_item.category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    preparation_time_remaining = serializers.FloatField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    total_time_elapsed = serializers.FloatField(read_only=True)

    # Enhanced fields
    can_modify = serializers.SerializerMethodField()
    estimated_ready_time_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'order_number', 'table', 'table_number',
            'menu_item', 'menu_item_name', 'menu_category', 'quantity',
            'unit_price', 'total_price', 'status', 'priority', 'source',
            'special_instructions', 'created_by', 'created_by_name',
            'confirmed_by', 'prepared_by', 'served_by',
            'created_at', 'confirmed_at', 'preparation_started_at',
            'ready_at', 'served_at', 'estimated_preparation_time',
            'estimated_ready_time', 'preparation_time_remaining',
            'is_overdue', 'total_time_elapsed', 'admin_notes',
            'can_modify', 'estimated_ready_time_formatted', 'is_kds_notified'
        ]

    def get_can_modify(self, obj):
        """Check if order can be modified"""
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.role in ['admin', 'manager']:
            return obj.status not in ['served', 'cancelled']
        return obj.status == 'pending'

    def get_estimated_ready_time_formatted(self, obj):
        """Format estimated ready time"""
        if obj.estimated_ready_time:
            now = timezone.now()
            if obj.estimated_ready_time > now:
                diff = (obj.estimated_ready_time - now).total_seconds() / 60
                return f"{int(diff)} minutes"
            else:
                return "Ready"
        return None

class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'table', 'menu_item', 'quantity', 'special_instructions',
            'priority', 'source'
        ]

    def validate(self, data):
        """Validate order data"""
        table = data.get('table')
        menu_item = data.get('menu_item')

        # Check table availability
        if not table.is_active:
            raise serializers.ValidationError("Table is not active")

        # Check menu item availability
        if not menu_item.is_available:
            raise serializers.ValidationError("Menu item is not available")

        return data

class OrderKDSSerializer(serializers.ModelSerializer):
    """Simplified serializer for Kitchen Display System"""
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_category = serializers.CharField(source='menu_item.category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_veg = serializers.BooleanField(source='menu_item.is_veg', read_only=True)
    is_spicy = serializers.BooleanField(source='menu_item.is_spicy', read_only=True)
    time_elapsed = serializers.SerializerMethodField()
    next_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'table_number', 'menu_item_name',
            'menu_category', 'quantity', 'status', 'priority',
            'special_instructions', 'created_by_name', 'is_veg', 'is_spicy',
            'created_at', 'estimated_ready_time', 'time_elapsed', 'next_status'
        ]

    def get_time_elapsed(self, obj):
        """Get time elapsed since order creation"""
        elapsed = (timezone.now() - obj.created_at).total_seconds() / 60
        return int(elapsed)

    def get_next_status(self, obj):
        """Get next possible status"""
        status_flow = {
            'pending': 'confirmed',
            'confirmed': 'preparing',
            'preparing': 'ready',
            'ready': 'served'
        }
        return status_flow.get(obj.status)

class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']

    def validate_status(self, value):
        """Validate status transition"""
        if value not in dict(Order.STATUS_CHOICES):
            raise serializers.ValidationError("Invalid status")
        return value

class BulkOrderCreateSerializer(serializers.Serializer):
    """Serializer for creating multiple orders at once"""
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.filter(is_active=True))
    orders = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=50  # Prevent too many orders at once
    )

    def validate_orders(self, orders_data):
        """Validate order items"""
        validated_orders = []

        for order_data in orders_data:
            # Validate required fields
            if 'menu_item_id' not in order_data:
                raise serializers.ValidationError("menu_item_id is required for each order")

            # Check menu item exists and is available
            try:
                menu_item = MenuItem.objects.get(
                    id=order_data['menu_item_id'],
                    is_active=True,
                    availability='available'
                )
            except MenuItem.DoesNotExist:
                raise serializers.ValidationError(f"Menu item {order_data['menu_item_id']} not available")

            validated_orders.append({
                'menu_item': menu_item,
                'quantity': order_data.get('quantity', 1),
                'special_instructions': order_data.get('special_instructions', ''),
                'priority': order_data.get('priority', 'normal'),
                'source': order_data.get('source', 'dine_in')
            })

        return validated_orders

    def create(self, validated_data):
        """Create multiple orders"""
        table = validated_data['table']
        orders_data = validated_data['orders']
        user = self.context['request'].user

        orders = []
        for order_data in orders_data:
            order = Order.objects.create(
                table=table,
                created_by=user,
                **order_data
            )
            orders.append(order)

        return orders

class TableSerializer(serializers.ModelSerializer):
    active_orders_count = serializers.SerializerMethodField()
    current_bill_amount = serializers.SerializerMethodField()
    occupancy_duration = serializers.SerializerMethodField()
    can_modify = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = [
            'id', 'table_number', 'capacity', 'status', 'location',
            'last_occupied_at', 'last_billed_at', 'is_active',
            'qr_code_url', 'notes', 'priority_level',
            'active_orders_count', 'current_bill_amount',
            'occupancy_duration', 'can_modify', 'created_at'
        ]

    def get_active_orders_count(self, obj):
        return obj.get_active_orders().count()

    def get_current_bill_amount(self, obj):
        return float(obj.get_total_bill_amount())

    def get_occupancy_duration(self, obj):
        return obj.get_occupied_duration()

    def get_can_modify(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.role in ['admin', 'manager']:
            return True
        return obj.status != 'occupied' or obj.get_active_orders().count() == 0

class TableWithOrdersSerializer(TableSerializer):
    """Extended table serializer with order details"""
    active_orders = serializers.SerializerMethodField()
    session_info = serializers.SerializerMethodField()

    class Meta(TableSerializer.Meta):
        fields = TableSerializer.Meta.fields + ['active_orders', 'session_info']

    def get_active_orders(self, obj):
        active_orders = obj.get_active_orders()
        return OrderSerializer(active_orders, many=True, context=self.context).data

    def get_session_info(self, obj):
        active_session = obj.order_sessions.filter(is_active=True).first()
        if active_session:
            return {
                'session_id': str(active_session.session_id),
                'created_at': active_session.created_at,
                'can_bill': True,
                'order_count': active_session.get_session_orders().count()
            }
        return None

class OrderSessionSerializer(serializers.ModelSerializer):
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    billed_by_name = serializers.CharField(source='billed_by.get_full_name', read_only=True)
    order_count = serializers.SerializerMethodField()

    class Meta:
        model = OrderSession
        fields = [
            'id', 'session_id', 'table', 'table_number', 'created_by',
            'created_by_name', 'billed_by', 'billed_by_name', 'is_active',
            'subtotal_amount', 'discount_amount', 'discount_percentage',
            'tax_amount', 'service_charge', 'final_amount',
            'payment_status', 'payment_method', 'payment_details',
            'notes', 'admin_notes', 'receipt_number', 'printed_at',
            'created_at', 'completed_at', 'order_count'
        ]

    def get_order_count(self, obj):
        return obj.get_session_orders().count()

class OrderSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderSession
        fields = [
            'table', 'discount_amount', 'discount_percentage',
            'service_charge', 'payment_method', 'notes'
        ]

class AdminBillSerializer(serializers.Serializer):
    """Serializer for admin bill modifications"""
    session_id = serializers.UUIDField()
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    service_charge = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    void_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate admin bill data"""
        if data.get('discount_percentage', 0) > 100:
            raise serializers.ValidationError("Discount percentage cannot exceed 100%")

        if data.get('discount_amount', 0) < 0:
            raise serializers.ValidationError("Discount amount cannot be negative")

        return data

class KitchenDisplaySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitchenDisplaySettings
        fields = [
            'id', 'name', 'audio_enabled', 'auto_refresh_interval',
            'display_completed_orders', 'completed_order_display_time',
            'priority_color_coding', 'show_preparation_time', 'show_order_notes',
            'max_orders_per_screen', 'offline_mode_enabled',
            'notification_sound_volume', 'auto_confirm_orders',
            'group_orders_by_table', 'created_at', 'updated_at'
        ]

class OfflineOrderBackupSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineOrderBackup
        fields = [
            'id', 'order_data', 'table_number', 'created_at',
            'processed_at', 'is_processed'
        ]

# Analytics Serializers
class OrderAnalyticsSerializer(serializers.Serializer):
    """Serializer for order analytics data"""
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    preparing_orders = serializers.IntegerField()
    ready_orders = serializers.IntegerField()
    served_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    average_preparation_time = serializers.FloatField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    busiest_table = serializers.CharField()
    most_ordered_item = serializers.CharField()
    hourly_breakdown = serializers.ListField()
    status_breakdown = serializers.DictField()
    category_breakdown = serializers.ListField()

class TableAnalyticsSerializer(serializers.Serializer):
    """Serializer for table analytics data"""
    date_range = serializers.DictField()
    table_stats = serializers.DictField()
    operational_stats = serializers.DictField()
    revenue_stats = serializers.DictField()
    table_utilization = serializers.ListField()

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    orders = serializers.DictField()
    tables = serializers.DictField()
    revenue = serializers.DictField()
    sessions = serializers.DictField()
    system = serializers.DictField()
    timestamp = serializers.DateTimeField()



