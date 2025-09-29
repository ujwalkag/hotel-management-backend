from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth.models import User
from .models import AdvanceBooking, BookingPayment, BookingStatusHistory

class BookingPaymentSerializer(serializers.ModelSerializer):
    """Serializer for booking payments"""
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)

    class Meta:
        model = BookingPayment
        fields = [
            'id', 'payment_date', 'amount', 'payment_method',
            'transaction_reference', 'notes', 'recorded_by', 'recorded_by_name'
        ]
        read_only_fields = ['recorded_by', 'payment_date']


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for booking status history"""
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = BookingStatusHistory
        fields = [
            'id', 'old_status', 'new_status', 'changed_at',
            'changed_by', 'changed_by_name', 'reason'
        ]
        read_only_fields = ['changed_by', 'changed_at']


class AdvanceBookingSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for AdvanceBooking model
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_today = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    booking_datetime = serializers.DateTimeField(read_only=True)
    payment_status = serializers.CharField(read_only=True)
    formatted_phone = serializers.CharField(read_only=True)
    booking_reference = serializers.CharField(read_only=True)
    
    # Related fields
    payments = BookingPaymentSerializer(many=True, read_only=True)
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = AdvanceBooking
        fields = [
            'id', 'customer_name', 'customer_phone', 'customer_aadhar',
            'customer_address', 'booking_date', 'booking_time', 'party_size',
            'booking_notes', 'total_amount', 'advance_paid', 'remaining_amount',
            'status', 'created_by', 'created_by_name', 'created_at', 'updated_at',
            'is_today', 'is_upcoming', 'is_past', 'booking_datetime', 
            'payment_status', 'formatted_phone', 'booking_reference',
            'payments', 'status_history'
        ]
        read_only_fields = [
            'remaining_amount', 'created_by', 'created_at', 'updated_at'
        ]

    def validate_booking_date(self, value):
        """Validate that booking date is not in the past"""
        if value < timezone.now().date():
            raise serializers.ValidationError("Booking date cannot be in the past.")
        return value

    def validate_customer_phone(self, value):
        """Validate phone number format"""
        import re
        digits_only = re.sub(r'[^0-9]', '', value)
        if len(digits_only) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def validate_customer_aadhar(self, value):
        """Validate Aadhar number format if provided"""
        if value:
            import re
            digits_only = re.sub(r'[^0-9]', '', value)
            if len(digits_only) != 12:
                raise serializers.ValidationError("Aadhar number must be exactly 12 digits.")
        return value

    def validate_party_size(self, value):
        """Validate party size is reasonable"""
        if value < 1:
            raise serializers.ValidationError("Party size must be at least 1.")
        if value > 50:
            raise serializers.ValidationError("Party size cannot exceed 50 people.")
        return value

    def validate(self, data):
        """Cross-field validation"""
        total_amount = data.get('total_amount', 0)
        advance_paid = data.get('advance_paid', 0)
        
        if advance_paid > total_amount:
            raise serializers.ValidationError(
                "Advance amount cannot be greater than total amount."
            )

        # Check for duplicate bookings
        if self.instance is None:  # Creating new booking
            existing_booking = AdvanceBooking.objects.filter(
                customer_phone=data.get('customer_phone'),
                booking_date=data.get('booking_date'),
                booking_time=data.get('booking_time'),
                status__in=['confirmed', 'pending']
            ).exists()
            
            if existing_booking:
                raise serializers.ValidationError(
                    "A booking already exists for this phone number at the same date and time."
                )

        return data

    def create(self, validated_data):
        """Create new advance booking"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update booking and track status changes"""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Update the booking
        booking = super().update(instance, validated_data)
        
        # Track status change if status changed
        if old_status != new_status:
            BookingStatusHistory.objects.create(
                booking=booking,
                old_status=old_status,
                new_status=new_status,
                changed_by=self.context['request'].user,
                reason=f"Status updated via API"
            )
        
        return booking

    def to_representation(self, instance):
        """Customize the output representation"""
        data = super().to_representation(instance)
        
        # Format amounts as strings with currency
        data['total_amount_formatted'] = f"₹{instance.total_amount:,.2f}"
        data['advance_paid_formatted'] = f"₹{instance.advance_paid:,.2f}"
        data['remaining_amount_formatted'] = f"₹{instance.remaining_amount:,.2f}"
        
        # Format date and time for display
        data['booking_date_formatted'] = instance.booking_date.strftime('%d %b %Y')
        data['booking_time_formatted'] = instance.booking_time.strftime('%I:%M %p')
        
        return data


class AdvanceBookingListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing bookings (dashboard widgets)
    """
    payment_status = serializers.CharField(read_only=True)
    booking_reference = serializers.CharField(read_only=True)

    class Meta:
        model = AdvanceBooking
        fields = [
            'id', 'customer_name', 'customer_phone', 'booking_date', 'booking_time',
            'party_size', 'total_amount', 'advance_paid', 'remaining_amount',
            'payment_status', 'booking_reference', 'booking_notes'
        ]

    def to_representation(self, instance):
        """Add formatted fields"""
        data = super().to_representation(instance)
        data['booking_date_formatted'] = instance.booking_date.strftime('%d %b %Y')
        data['booking_time_formatted'] = instance.booking_time.strftime('%I:%M %p')
        return data
