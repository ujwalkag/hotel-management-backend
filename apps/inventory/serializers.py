# apps/inventory/serializers.py
from rest_framework import serializers
from .models import (
    InventoryCategory, 
    InventoryItem, 
    StockMovement, 
    LowStockAlert,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem
)

class InventoryCategorySerializer(serializers.ModelSerializer):
    items_count = serializers.ReadOnlyField()
    total_value = serializers.ReadOnlyField()
    
    class Meta:
        model = InventoryCategory
        fields = ['id', 'name', 'description', 'is_active', 'items_count', 
                 'total_value', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Category name is required")
        return value.strip()

class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_value = serializers.ReadOnlyField()
    stock_status = serializers.ReadOnlyField()
    stock_status_class = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    is_out_of_stock = serializers.ReadOnlyField()
    is_overstocked = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    is_expiring_soon = serializers.ReadOnlyField()
    unit_display = serializers.CharField(source='get_unit_display', read_only=True)
    
    class Meta:
        model = InventoryItem
        fields = ['id', 'category', 'category_name', 'name', 'description', 'sku',
                 'unit', 'unit_display', 'current_stock', 'min_stock_level', 'max_stock_level',
                 'cost_per_unit', 'selling_price_per_unit', 'supplier_name',
                 'supplier_contact', 'expiry_date', 'location', 'is_active',
                 'total_value', 'stock_status', 'stock_status_class', 
                 'is_low_stock', 'is_out_of_stock', 'is_overstocked', 'days_until_expiry',
                 'is_expired', 'is_expiring_soon', 'created_at', 'last_updated']
        read_only_fields = ['sku', 'total_value', 'stock_status', 'stock_status_class',
                           'is_low_stock', 'is_out_of_stock', 'is_overstocked',
                           'days_until_expiry', 'is_expired', 'is_expiring_soon',
                           'created_at', 'last_updated']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Item name is required")
        return value.strip()

    def validate_cost_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Cost per unit must be greater than 0")
        return value

    def validate_min_stock_level(self, value):
        if value < 0:
            raise serializers.ValidationError("Minimum stock level cannot be negative")
        return value

    def validate_max_stock_level(self, value):
        if value < 0:
            raise serializers.ValidationError("Maximum stock level cannot be negative")
        return value

    def validate(self, data):
        min_stock = data.get('min_stock_level', 0)
        max_stock = data.get('max_stock_level', 0)
        
        if min_stock > max_stock:
            raise serializers.ValidationError(
                "Minimum stock level cannot be greater than maximum stock level"
            )
        
        return data

class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_unit = serializers.CharField(source='item.unit', read_only=True)
    item_sku = serializers.CharField(source='item.sku', read_only=True)
    total_cost = serializers.ReadOnlyField()
    movement_direction = serializers.ReadOnlyField()
    recorded_by_name = serializers.CharField(source='recorded_by.email', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = ['id', 'item', 'item_name', 'item_unit', 'item_sku', 'movement_type', 
                 'movement_type_display', 'quantity', 'cost_per_unit', 'total_cost', 
                 'movement_direction', 'supplier_name', 'invoice_number', 'batch_number', 
                 'expiry_date', 'date', 'reference', 'notes', 'recorded_by', 
                 'recorded_by_name', 'created_at']
        read_only_fields = ['total_cost', 'movement_direction', 'recorded_by', 
                           'recorded_by_name', 'created_at']

class StockMovementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ['item', 'movement_type', 'quantity', 'cost_per_unit', 
                 'supplier_name', 'invoice_number', 'batch_number', 'expiry_date',
                 'reference', 'notes']
        
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate_cost_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Cost per unit must be greater than 0")
        return value

    def validate(self, data):
        movement_type = data.get('movement_type')
        item = data.get('item')
        quantity = data.get('quantity', 0)
        
        # For out movements, check if sufficient stock exists
        if movement_type in ['out', 'waste', 'expired'] and item:
            if quantity > item.current_stock:
                raise serializers.ValidationError(
                    f"Cannot remove {quantity} {item.unit}. Only {item.current_stock} {item.unit} available."
                )
        
        return data

class LowStockAlertSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_sku = serializers.CharField(source='item.sku', read_only=True)
    item_current_stock = serializers.DecimalField(source='item.current_stock', max_digits=10, decimal_places=2, read_only=True)
    item_unit = serializers.CharField(source='item.unit', read_only=True)
    category_name = serializers.CharField(source='item.category.name', read_only=True)
    days_since_alert = serializers.ReadOnlyField()
    resolved_by_name = serializers.CharField(source='resolved_by.email', read_only=True)
    
    class Meta:
        model = LowStockAlert
        fields = ['id', 'item', 'item_name', 'item_sku', 'item_current_stock', 'item_unit',
                 'category_name', 'alert_date', 'stock_level_at_alert', 'threshold_level', 
                 'is_resolved', 'resolved_date', 'resolved_by', 'resolved_by_name',
                 'days_since_alert', 'notes']
        read_only_fields = ['alert_date', 'days_since_alert', 'resolved_by', 'resolved_by_name']

class SupplierSerializer(serializers.ModelSerializer):
    total_purchase_amount = serializers.ReadOnlyField()
    
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'address',
                 'gst_number', 'payment_terms', 'is_active', 'total_purchase_amount',
                 'created_at', 'updated_at']
        read_only_fields = ['total_purchase_amount', 'created_at', 'updated_at']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Supplier name is required")
        return value.strip()

    def validate_phone(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("Phone number should contain only digits")
        return value

    def validate_email(self, value):
        if value and '@' not in value:
            raise serializers.ValidationError("Enter a valid email address")
        return value

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_unit = serializers.CharField(source='item.unit', read_only=True)
    item_sku = serializers.CharField(source='item.sku', read_only=True)
    total_amount = serializers.ReadOnlyField()
    pending_quantity = serializers.ReadOnlyField()
    is_fully_received = serializers.ReadOnlyField()
    
    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'item', 'item_name', 'item_unit', 'item_sku', 'quantity_ordered',
                 'quantity_received', 'unit_price', 'total_amount', 'pending_quantity',
                 'is_fully_received']

class PurchaseOrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ['item', 'quantity_ordered', 'unit_price']

    def validate_quantity_ordered(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity ordered must be greater than 0")
        return value

    def validate_unit_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Unit price must be greater than 0")
        return value

class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ['id', 'order_number', 'supplier', 'supplier_name', 'order_date',
                 'expected_delivery_date', 'status', 'status_display', 'total_amount', 
                 'notes', 'created_by', 'created_by_name', 'items', 'created_at', 'updated_at']
        read_only_fields = ['order_number', 'total_amount', 'created_by', 'created_by_name',
                           'created_at', 'updated_at']

class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'order_date', 'expected_delivery_date', 'notes', 'items']

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        purchase_order = PurchaseOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            PurchaseOrderItem.objects.create(
                purchase_order=purchase_order,
                **item_data
            )
        
        purchase_order.calculate_total()
        return purchase_order

class InventoryDashboardSerializer(serializers.Serializer):
    """Serializer for inventory dashboard summary"""
    total_items = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    expiring_count = serializers.IntegerField()
    total_inventory_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    recent_movements_count = serializers.IntegerField()
    active_alerts_count = serializers.IntegerField()

class StockMovementSummarySerializer(serializers.Serializer):
    """Serializer for stock movement summary reports"""
    date = serializers.DateField()
    movement_type = serializers.CharField()
    total_movements = serializers.IntegerField()
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_value = serializers.DecimalField(max_digits=12, decimal_places=2)
