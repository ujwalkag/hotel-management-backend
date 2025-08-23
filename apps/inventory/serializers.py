# apps/inventory/serializers.py
from rest_framework import serializers
from .models import InventoryCategory, InventoryEntry
from datetime import datetime, date

class InventoryCategorySerializer(serializers.ModelSerializer):
    total_entries = serializers.ReadOnlyField()
    total_spent = serializers.ReadOnlyField()

    class Meta:
        model = InventoryCategory
        fields = [
            'id', 'name', 'description', 'is_active', 
            'total_entries', 'total_spent', 'created_at'
        ]
        read_only_fields = ['created_at']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Category name is required")
        return value.strip().title()

class InventoryEntrySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.email', read_only=True)

    class Meta:
        model = InventoryEntry
        fields = [
            'id', 'category', 'category_name', 'item_name', 
            'price_per_unit', 'quantity', 'total_cost', 
            'purchase_date', 'supplier_name', 'notes',
            'created_by_name', 'created_at'
        ]
        read_only_fields = ['total_cost', 'created_by_name', 'created_at']

    def validate_item_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Item name is required")
        return value.strip().title()

    def validate_price_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate_supplier_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Supplier name is required")
        return value.strip().title()

class InventoryReportSerializer(serializers.Serializer):
    """For monthly reports"""
    month = serializers.CharField()
    year = serializers.CharField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_entries = serializers.IntegerField()
    categories_data = serializers.JSONField()
    top_suppliers = serializers.JSONField()

