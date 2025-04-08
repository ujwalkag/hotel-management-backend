from rest_framework import serializers
from apps.admin_dashboard.models import SalesSummary, BestSellingItem
from apps.bookings.models import Order, MenuItem


class SalesSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesSummary
        fields = '__all__'


class BestSellingItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = BestSellingItem
        fields = ['id', 'item', 'item_name', 'sales_count']


class OrderStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    failed_orders = serializers.IntegerField()


class RevenueStatsSerializer(serializers.Serializer):
    daily_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    weekly_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_sales = serializers.DecimalField(max_digits=10, decimal_places=2)

