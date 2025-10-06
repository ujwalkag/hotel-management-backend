# apps/menu/serializers.py
from rest_framework import serializers
from .models import MenuItem, MenuCategory

class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = ['id', 'name_en', 'name_hi']

class MenuItemSerializer(serializers.ModelSerializer):
    category = MenuCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuCategory.objects.all(), source='category', write_only=True
    )
    
    # Add soft delete fields to serializer
    status_display = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name_en', 'name_hi', 'description_en', 'description_hi',
            'price', 'available', 'category', 'category_id', 'image',
            'is_active', 'is_discontinued', 'discontinued_at', 'discontinue_reason',
            'created_at', 'updated_at', 'status_display', 'can_delete'
        ]
        read_only_fields = ['discontinued_at']
    
    def get_status_display(self, obj):
        if obj.is_discontinued:
            return "Discontinued"
        elif not obj.is_active:
            return "Inactive"
        elif not obj.available:
            return "Unavailable"
        else:
            return "Active"
    
    def get_can_delete(self, obj):
        return obj.can_be_hard_deleted()

