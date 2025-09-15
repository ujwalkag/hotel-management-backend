# apps/inventory/serializers.py - ENHANCED VERSION
from rest_framework import serializers
from .models import InventoryCategory, InventoryEntry, SpendingBudget
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
    """Basic inventory entry serializer for backward compatibility"""
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

class EnhancedInventoryEntrySerializer(serializers.ModelSerializer):
    """Enhanced inventory entry serializer with all new fields"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.email', read_only=True)
    cost_per_unit_display = serializers.SerializerMethodField()
    total_cost_display = serializers.SerializerMethodField()
    purchase_date_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()

    class Meta:
        model = InventoryEntry
        fields = [
            'id', 'category', 'category_name', 'item_name', 
            'price_per_unit', 'cost_per_unit_display', 'quantity', 'unit_type',
            'total_cost', 'total_cost_display', 'purchase_date', 'purchase_date_display',
            'supplier_name', 'notes', 'is_recurring', 'priority', 'priority_display',
            'tags', 'tags_list', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['total_cost', 'created_by_name', 'created_at']

    def get_cost_per_unit_display(self, obj):
        return f"₹{obj.price_per_unit:,.2f}"

    def get_total_cost_display(self, obj):
        return f"₹{obj.total_cost:,.2f}"

    def get_purchase_date_display(self, obj):
        return obj.purchase_date.strftime('%d %b %Y')

    def get_priority_display(self, obj):
        priority_map = {
            'low': 'Low Priority',
            'medium': 'Medium Priority',
            'high': 'High Priority',
            'urgent': 'Urgent'
        }
        return priority_map.get(obj.priority, obj.priority.title())

    def get_tags_list(self, obj):
        if obj.tags:
            return [tag.strip() for tag in obj.tags.split(',') if tag.strip()]
        return []

    def validate_item_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Item name is required")
        return value.strip()

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
        return value.strip()

    def validate_unit_type(self, value):
        if not value.strip():
            raise serializers.ValidationError("Unit type is required")
        return value.strip().lower()

    def validate_tags(self, value):
        if value:
            # Clean up tags
            tags = [tag.strip() for tag in value.split(',') if tag.strip()]
            return ', '.join(tags)
        return value

class SpendingBudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.email', read_only=True)
    spent_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    utilization_percentage = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    budget_amount_display = serializers.SerializerMethodField()
    spent_amount_display = serializers.SerializerMethodField()
    remaining_amount_display = serializers.SerializerMethodField()

    class Meta:
        model = SpendingBudget
        fields = [
            'id', 'category', 'category_name', 'budget_name', 
            'budget_amount', 'budget_amount_display', 'period_type',
            'start_date', 'end_date', 'is_active',
            'spent_amount', 'spent_amount_display',
            'remaining_amount', 'remaining_amount_display',
            'utilization_percentage', 'status',
            'created_by_name', 'created_at'
        ]
        read_only_fields = ['created_by_name', 'created_at']

    def get_spent_amount(self, obj):
        return float(obj.get_spent_amount())

    def get_remaining_amount(self, obj):
        return float(obj.get_remaining_amount())

    def get_utilization_percentage(self, obj):
        return obj.get_utilization_percentage()

    def get_status(self, obj):
        remaining = obj.get_remaining_amount()
        utilization = obj.get_utilization_percentage()

        if remaining < 0:
            return 'over_budget'
        elif utilization >= 90:
            return 'near_limit'
        elif utilization >= 75:
            return 'on_track'
        else:
            return 'under_utilized'

    def get_budget_amount_display(self, obj):
        return f"₹{obj.budget_amount:,.2f}"

    def get_spent_amount_display(self, obj):
        spent = obj.get_spent_amount()
        return f"₹{spent:,.2f}"

    def get_remaining_amount_display(self, obj):
        remaining = obj.get_remaining_amount()
        return f"₹{remaining:,.2f}"

    def validate_budget_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget amount must be greater than 0")
        return value

    def validate(self, data):
        """Validate that end_date is after start_date"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError("End date must be after start date")

        return data

class InventoryReportSerializer(serializers.Serializer):
    """Enhanced serializer for comprehensive reports"""
    month = serializers.CharField()
    year = serializers.CharField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_entries = serializers.IntegerField()
    avg_cost_per_entry = serializers.DecimalField(max_digits=12, decimal_places=2)
    categories_data = serializers.JSONField()
    top_suppliers = serializers.JSONField()
    priority_breakdown = serializers.JSONField()
    daily_spending = serializers.JSONField()

class SpendingAnalyticsSerializer(serializers.Serializer):
    """Serializer for spending analytics response"""
    total_spent = serializers.FloatField()
    total_entries = serializers.IntegerField()
    avg_cost_per_entry = serializers.FloatField()
    category_breakdown = serializers.JSONField()
    supplier_breakdown = serializers.JSONField()
    monthly_trend = serializers.JSONField()
    priority_breakdown = serializers.JSONField()
    filters_applied = serializers.JSONField()

class FilterOptionsSerializer(serializers.Serializer):
    """Serializer for filter options response"""
    suppliers = serializers.ListField(child=serializers.CharField())
    categories = serializers.JSONField()
    priorities = serializers.JSONField()
    unit_types = serializers.ListField(child=serializers.CharField())
    cost_stats = serializers.JSONField()
    tags = serializers.ListField(child=serializers.CharField())

class SpendingComparisonSerializer(serializers.Serializer):
    """Serializer for spending comparison response"""
    period1 = serializers.JSONField()
    period2 = serializers.JSONField()
    comparison = serializers.JSONField()

class DashboardStatsSerializer(serializers.Serializer):
    """Enhanced serializer for dashboard statistics"""
    current_month_spent = serializers.FloatField()
    total_categories = serializers.IntegerField()
    total_suppliers = serializers.IntegerField()
    last_30_days_spent = serializers.FloatField()
    top_category_this_month = serializers.JSONField()
    recent_entries = EnhancedInventoryEntrySerializer(many=True)

# Bulk operations serializers
class BulkInventoryEntrySerializer(serializers.Serializer):
    """Serializer for bulk inventory entry operations"""
    entries = EnhancedInventoryEntrySerializer(many=True)

    def create(self, validated_data):
        entries_data = validated_data['entries']
        created_entries = []

        for entry_data in entries_data:
            entry = InventoryEntry.objects.create(**entry_data)
            created_entries.append(entry)

        return {'entries': created_entries}

class InventoryFilterSerializer(serializers.Serializer):
    """Serializer for validating filter parameters"""
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    category = serializers.IntegerField(required=False)
    supplier = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        required=False
    )
    min_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    max_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    unit_type = serializers.CharField(required=False, allow_blank=True)
    is_recurring = serializers.BooleanField(required=False)
    tags = serializers.CharField(required=False, allow_blank=True)
    search = serializers.CharField(required=False, allow_blank=True)
    sort_by = serializers.CharField(required=False)

    def validate(self, data):
        """Validate filter combinations"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        min_cost = data.get('min_cost')
        max_cost = data.get('max_cost')

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("End date must be after start date")

        if min_cost and max_cost and max_cost < min_cost:
            raise serializers.ValidationError("Maximum cost must be greater than minimum cost")

        return data
