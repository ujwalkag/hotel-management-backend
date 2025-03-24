from rest_framework import serializers
from apps.bookings.models import Order, MenuItem
from .models import SalesSummary, BestSellingItem

class OrderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'order_type', 'total_price', 'created_at']


class SalesSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesSummary
        fields = '__all__'


class BestSellingItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name')

    class Meta:
        model = BestSellingItem
        fields = ['item_name', 'sales_count']

