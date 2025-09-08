# apps/enhanced_billing/serializers.py
from rest_framework import serializers
from .models import EnhancedBill, EnhancedBillItem, BillPaymentRecord, BillingSession

class EnhancedBillItemSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = EnhancedBillItem
        fields = '__all__'

class EnhancedBillSerializer(serializers.ModelSerializer):
    bill_items = EnhancedBillItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    effective_tax_percentage = serializers.ReadOnlyField()
    waiter_name = serializers.CharField(source='waiter.get_full_name', read_only=True)

    class Meta:
        model = EnhancedBill
        fields = '__all__'

class BillPaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillPaymentRecord
        fields = '__all__'

class BillingSessionSerializer(serializers.ModelSerializer):
    session_duration_minutes = serializers.ReadOnlyField()
    biller_name = serializers.CharField(source='biller.get_full_name', read_only=True)

    class Meta:
        model = BillingSession
        fields = '__all__'

class PaymentProcessSerializer(serializers.Serializer):
    """Serializer for processing payments"""
    payment_method = serializers.ChoiceField(choices=EnhancedBill.PAYMENT_METHOD_CHOICES)
    cash_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    card_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    upi_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)

class BillFromSessionSerializer(serializers.Serializer):
    """Serializer for creating bill from table session"""
    table_session_id = serializers.CharField(max_length=50)
    customer_name = serializers.CharField(max_length=100, default="Guest")
    customer_phone = serializers.CharField(max_length=15, required=False)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)

