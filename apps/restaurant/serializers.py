# apps/restaurant/serializers.py - Serializers for Restaurant/KDS System - FIXED
from rest_framework import serializers
from .models import (
    Table, MenuCategory, MenuItem, Order, OrderSession, KitchenDisplaySettings
)
from apps.users.models import CustomUser
from django.utils import timezone
from decimal import Decimal

class TableSerializer(serializers.ModelSerializer):
    """Serializer for Table model"""
    is_available = serializers.ReadOnlyField()
    active_orders_count = serializers.SerializerMethodField()
    total_bill_amount = serializers.SerializerMethodField()
    time_occupied = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = [
            'id', 'table_number', 'capacity', 'status', 'location',
            'is_available', 'is_active', 'last_occupied_at', 'last_billed_at',
            'active_orders_count', 'total_bill_amount', 'time_occupied',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['last_occupied_at', 'last_billed_at', 'created_at', 'updated_at']

    def get_active_orders_count(self, obj):
        return obj.get_active_orders().count()

    def get_total_bill_amount(self, obj):
        return float(obj.get_total_bill_amount())

    def get_time_occupied(self, obj):
        """Get time in minutes since table was occupied"""
        if obj.last_occupied_at and obj.status == 'occupied':
            delta = timezone.now() - obj.last_occupied_at
            return int(delta.total_seconds() / 60)
        return 0

class TableWithOrdersSerializer(serializers.ModelSerializer):
    """Extended table serializer with order details"""
    active_orders = serializers.SerializerMethodField()
    is_available = serializers.ReadOnlyField()
    total_bill_amount = serializers.SerializerMethodField()
    last_order_time = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = [
            'id', 'table_number', 'capacity', 'status', 'location',
            'is_available', 'active_orders', 'total_bill_amount',
            'last_order_time', 'last_occupied_at'
        ]

    def get_active_orders(self, obj):
        """Get active orders for this table"""
        orders = obj.get_active_orders().select_related('menu_item', 'created_by')
        return OrderSummarySerializer(orders, many=True).data

    def get_total_bill_amount(self, obj):
        return float(obj.get_total_bill_amount())

    def get_last_order_time(self, obj):
        """Get timestamp of last order"""
        last_order = obj.orders.filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready', 'served']
        ).order_by('-created_at').first()

        if last_order:
            return last_order.created_at.isoformat()
        return None

class MenuCategorySerializer(serializers.ModelSerializer):
    """Serializer for MenuCategory model"""
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = MenuCategory
        fields = [
            'id', 'name', 'description', 'display_order', 'icon',
            'is_active', 'items_count', 'created_at'
        ]

    def get_items_count(self, obj):
        return obj.items.filter(is_active=True, availability='available').count()

class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for MenuItem model"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_available = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()
    allergens_list = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'price', 'cost_price', 'availability', 'preparation_time',
            'is_veg', 'is_spicy', 'allergens', 'allergens_list',
            'image_url', 'display_order', 'is_available', 'is_active',
            'profit_margin', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_allergens_list(self, obj):
        """Convert comma-separated allergens to list"""
        if obj.allergens:
            return [allergen.strip() for allergen in obj.allergens.split(',')]
        return []

class MenuItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating menu items"""
    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'category', 'price', 'cost_price',
            'availability', 'preparation_time', 'is_veg', 'is_spicy',
            'allergens', 'image_url', 'display_order', 'is_active'
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value

    def validate_preparation_time(self, value):
        if value < 0:
            raise serializers.ValidationError("Preparation time cannot be negative")
        return value

# ✅ FIXED: UserSerializer - removed first_name and last_name
class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for order tracking - FIXED to match CustomUser model"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'role', 'display_name']

    def get_display_name(self, obj):
        """Get a display name for the user"""
        if obj.email:
            # Use part before @ as display name, or just email
            username = obj.email.split('@')[0]
            return f"{username} ({obj.role})" if obj.role else username
        return obj.role or "Unknown User"

class OrderSerializer(serializers.ModelSerializer):
    """Detailed serializer for Order model"""
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_details = MenuItemSerializer(source='menu_item', read_only=True)
    created_by_details = UserSerializer(source='created_by', read_only=True)
    confirmed_by_details = UserSerializer(source='confirmed_by', read_only=True)
    prepared_by_details = UserSerializer(source='prepared_by', read_only=True)
    served_by_details = UserSerializer(source='served_by', read_only=True)

    preparation_time_remaining = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    total_time_elapsed = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'order_number', 'table', 'table_number',
            'menu_item', 'menu_item_name', 'menu_item_details',
            'quantity', 'unit_price', 'total_price', 'status', 'priority',
            'special_instructions', 'created_by', 'created_by_details',
            'confirmed_by', 'confirmed_by_details', 'prepared_by', 'prepared_by_details',
            'served_by', 'served_by_details', 'created_at', 'confirmed_at',
            'preparation_started_at', 'ready_at', 'served_at',
            'estimated_preparation_time', 'estimated_ready_time',
            'preparation_time_remaining', 'is_overdue', 'total_time_elapsed'
        ]
        read_only_fields = [
            'order_id', 'order_number', 'unit_price', 'total_price',
            'confirmed_at', 'preparation_started_at', 'ready_at', 'served_at',
            'estimated_ready_time'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders"""
    class Meta:
        model = Order
        fields = [
            'table', 'menu_item', 'quantity', 'special_instructions', 'priority'
        ]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate_table(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Table is not active")
        return value

    def validate_menu_item(self, value):
        if not value.is_available:
            raise serializers.ValidationError("Menu item is not available")
        return value

class OrderKDSSerializer(serializers.ModelSerializer):
    """Optimized serializer for Kitchen Display System"""
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    table_capacity = serializers.IntegerField(source='table.capacity', read_only=True)
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_category = serializers.CharField(source='menu_item.category.name', read_only=True)
    preparation_time = serializers.IntegerField(source='menu_item.preparation_time', read_only=True)
    is_veg = serializers.BooleanField(source='menu_item.is_veg', read_only=True)
    is_spicy = serializers.BooleanField(source='menu_item.is_spicy', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    preparation_time_remaining = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    total_time_elapsed = serializers.ReadOnlyField()
    time_since_created = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'table_number', 'table_capacity',
            'menu_item_name', 'menu_category', 'quantity', 'status', 'priority',
            'special_instructions', 'created_at', 'preparation_time',
            'is_veg', 'is_spicy', 'created_by_name', 'estimated_ready_time',
            'preparation_time_remaining', 'is_overdue', 'total_time_elapsed',
            'time_since_created'
        ]

    def get_created_by_name(self, obj):
        """Get creator's name for display - FIXED"""
        if obj.created_by:
            if obj.created_by.email:
                username = obj.created_by.email.split('@')[0]
                return f"{username} ({obj.created_by.role})" if obj.created_by.role else username
            return obj.created_by.role or "Unknown"
        return "Unknown"

    def get_time_since_created(self, obj):
        """Get formatted time since order was created"""
        delta = timezone.now() - obj.created_at
        minutes = int(delta.total_seconds() / 60)

        if minutes < 60:
            return f"{minutes}m"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            return f"{hours}h {remaining_minutes}m"

class OrderSummarySerializer(serializers.ModelSerializer):
    """Lightweight order serializer for summaries"""
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'menu_item_name', 'quantity',
            'status', 'total_price', 'created_at', 'created_by_name'
        ]

    def get_created_by_name(self, obj):
        """Get creator's name for display - FIXED"""
        if obj.created_by:
            if obj.created_by.email:
                username = obj.created_by.email.split('@')[0]
                return f"{username} ({obj.created_by.role})" if obj.created_by.role else username
            return obj.created_by.role or "Unknown"
        return "Unknown"

class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for order status updates"""
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_status(self, value):
        """Validate status transitions"""
        instance = self.instance
        if instance:
            current_status = instance.status

            # Define allowed transitions
            allowed_transitions = {
                'pending': ['confirmed', 'cancelled'],
                'confirmed': ['preparing', 'cancelled'],
                'preparing': ['ready', 'cancelled'],
                'ready': ['served'],
                'served': [],  # No transitions from served
                'cancelled': []  # No transitions from cancelled
            }

            if value not in allowed_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot change status from {current_status} to {value}"
                )

        return value

class BulkOrderCreateSerializer(serializers.Serializer):
    """Serializer for creating multiple orders at once - UPDATED to handle both menu systems"""
    table = serializers.PrimaryKeyRelatedField(queryset=Table.objects.filter(is_active=True))
    orders = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=50
    )
    special_instructions = serializers.CharField(required=False, allow_blank=True)

    def validate_orders(self, value):
        """Validate individual orders - HANDLES BOTH MENU SYSTEMS"""
        validated_orders = []

        for order_data in value:
            # Validate required fields
            if 'menu_item' not in order_data or 'quantity' not in order_data:
                raise serializers.ValidationError(
                    "Each order must have 'menu_item' and 'quantity'"
                )

            menu_item_id = order_data['menu_item']
            menu_item = None
            
            # ✅ TRY RESTAURANT MENU FIRST
            try:
                menu_item = MenuItem.objects.get(
                    id=menu_item_id,
                    is_active=True,
                    availability='available'
                )
                print(f"✅ Found in restaurant menu: {menu_item.name}")
                
            except MenuItem.DoesNotExist:
                # ✅ FALLBACK TO OLD MENU SYSTEM  
                try:
                    from apps.menu.models import MenuItem as OldMenuItem, MenuCategory as OldMenuCategory
                    old_item = OldMenuItem.objects.get(
                        id=menu_item_id,
                        available=True
                    )
                    print(f"✅ Found in old menu: {old_item.name_en}")
                    
                    # ✅ AUTO-CREATE RESTAURANT MENU ITEM
                    if old_item.category:
                        category, created = MenuCategory.objects.get_or_create(
                            name=old_item.category.name_en,
                            defaults={
                                'description': f'Migrated from old menu: {old_item.category.name_hi}',
                                'is_active': True,
                                'display_order': 0
                            }
                        )
                        if created:
                            print(f"✅ Created restaurant category: {category.name}")
                    else:
                        category = None
                    
                    menu_item, created = MenuItem.objects.get_or_create(
                        name=old_item.name_en,
                        defaults={
                            'description': old_item.description_en or old_item.description_hi or '',
                            'category': category,
                            'price': old_item.price,
                            'availability': 'available',
                            'preparation_time': 15,  # Default preparation time
                            'is_veg': True,  # Default - can be enhanced based on your data
                            'is_spicy': False,  # Default - can be enhanced
                            'is_active': True,
                            'image_url': '',  # Convert from old_item.image if needed
                            'display_order': 0
                        }
                    )
                    
                    if created:
                        print(f"✅ Created restaurant menu item: {menu_item.name} (₹{menu_item.price})")
                    else:
                        print(f"✅ Using existing restaurant menu item: {menu_item.name}")
                        
                except Exception as e:
                    raise serializers.ValidationError(
                        f"Menu item {menu_item_id} not found in either menu system: {str(e)}"
                    )

            # Validate quantity
            quantity = order_data['quantity']
            if not isinstance(quantity, int) or quantity <= 0:
                raise serializers.ValidationError(
                    f"Invalid quantity {quantity} for menu item {menu_item.name}"
                )

            validated_orders.append({
                'menu_item': menu_item,
                'quantity': quantity,
                'priority': order_data.get('priority', 'normal'),
                'special_instructions': order_data.get('special_instructions', '')
            })

        return validated_orders

    def create(self, validated_data):
        """Create multiple orders"""
        table = validated_data['table']
        orders_data = validated_data['orders']
        global_instructions = validated_data.get('special_instructions', '')
        created_by = self.context['request'].user

        created_orders = []

        for order_data in orders_data:
            # Combine global and individual instructions
            instructions = []
            if global_instructions:
                instructions.append(global_instructions)
            if order_data.get('special_instructions'):
                instructions.append(order_data['special_instructions'])

            order = Order.objects.create(
                table=table,
                menu_item=order_data['menu_item'],
                quantity=order_data['quantity'],
                priority=order_data.get('priority', 'normal'),
                special_instructions=' | '.join(instructions),
                created_by=created_by
            )

            created_orders.append(order)
            print(f"✅ Created order: {order.order_number} - {order.menu_item.name} x{order.quantity}")

        return created_orders

class OrderSessionSerializer(serializers.ModelSerializer):
    """Serializer for OrderSession model"""
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    session_orders = serializers.SerializerMethodField()
    session_duration = serializers.SerializerMethodField()

    class Meta:
        model = OrderSession
        fields = [
            'id', 'session_id', 'table', 'table_number', 'created_by_name',
            'is_active', 'total_amount', 'discount_amount', 'tax_amount',
            'final_amount', 'payment_status', 'notes', 'created_at',
            'completed_at', 'session_orders', 'session_duration'
        ]
        read_only_fields = ['session_id', 'created_at', 'completed_at']

    def get_created_by_name(self, obj):
        """Get creator's name for display - FIXED"""
        if obj.created_by:
            if obj.created_by.email:
                username = obj.created_by.email.split('@')[0]
                return f"{username} ({obj.created_by.role})" if obj.created_by.role else username
            return obj.created_by.role or "Unknown"
        return "Unknown"

    def get_session_orders(self, obj):
        """Get orders for this session"""
        orders = obj.table.orders.filter(
            created_at__gte=obj.created_at,
            status__in=['confirmed', 'preparing', 'ready', 'served']
        )
        return OrderSummarySerializer(orders, many=True).data

    def get_session_duration(self, obj):
        """Get session duration in minutes"""
        end_time = obj.completed_at or timezone.now()
        delta = end_time - obj.created_at
        return int(delta.total_seconds() / 60)

class KitchenDisplaySettingsSerializer(serializers.ModelSerializer):
    """Serializer for KitchenDisplaySettings model"""
    class Meta:
        model = KitchenDisplaySettings
        fields = [
            'id', 'name', 'audio_enabled', 'auto_refresh_interval',
            'display_completed_orders', 'completed_order_display_time',
            'priority_color_coding', 'show_preparation_time',
            'show_order_notes', 'max_orders_per_screen',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

# Analytics and Reporting Serializers
class OrderAnalyticsSerializer(serializers.Serializer):
    """Serializer for order analytics data"""
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    preparing_orders = serializers.IntegerField()
    ready_orders = serializers.IntegerField()
    served_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()

    average_preparation_time = serializers.FloatField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    busiest_table = serializers.CharField()
    most_ordered_item = serializers.CharField()

    hourly_breakdown = serializers.JSONField()
    status_breakdown = serializers.JSONField()
    category_breakdown = serializers.JSONField()

class TableAnalyticsSerializer(serializers.Serializer):
    """Serializer for table analytics data"""
    total_tables = serializers.IntegerField()
    occupied_tables = serializers.IntegerField()
    free_tables = serializers.IntegerField()
    average_occupancy_time = serializers.FloatField()
    table_turnover_rate = serializers.FloatField()
    revenue_per_table = serializers.JSONField()
