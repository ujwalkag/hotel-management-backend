# apps/advance_booking/models.py

from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator, MinValueValidator
from decimal import Decimal
from django.utils import timezone
from datetime import datetime

class AdvanceBooking(models.Model):
    """
    Model for advance bookings with customer details and payment information
    Separate from restaurant app to maintain modularity
    """
    BOOKING_STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    # Customer Information
    customer_name = models.CharField(
        max_length=100,
        help_text="Customer's full name"
    )
    customer_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
        )],
        help_text="Customer's contact phone number"
    )
    customer_aadhar = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex=r'^\d{12}$',
            message="Aadhar number must be 12 digits."
        )],
        help_text="Customer's Aadhar number (optional)"
    )
    customer_address = models.TextField(
        blank=True,
        null=True,
        help_text="Customer's address (optional)"
    )

    # Booking Details
    booking_date = models.DateField(help_text="Date of the booking")
    booking_time = models.TimeField(help_text="Time of the booking")
    party_size = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of people in the party"
    )
    booking_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Special requests, dietary restrictions, celebration details, etc."
    )

    # Payment Information
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount for the booking"
    )
    advance_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Advance amount paid"
    )
    remaining_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Remaining amount to be paid"
    )

    # System Fields
    status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS_CHOICES,
        default='confirmed',
        help_text="Current status of the booking"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="Admin user who created this booking"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['booking_date', 'booking_time']
        verbose_name = 'Advance Booking'
        verbose_name_plural = 'Advance Bookings'
        db_table = 'advance_booking'
        indexes = [
            models.Index(fields=['booking_date']),
            models.Index(fields=['customer_phone']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def save(self, *args, **kwargs):
        """Auto-calculate remaining amount before saving"""
        self.remaining_amount = self.total_amount - self.advance_paid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_name} - {self.booking_date} {self.booking_time}"

    @property
    def is_today(self):
        """Check if booking is for today"""
        return self.booking_date == timezone.now().date()

    @property
    def is_upcoming(self):
        """Check if booking is upcoming (today or future)"""
        return self.booking_date >= timezone.now().date()

    @property
    def is_past(self):
        """Check if booking is in the past"""
        now = timezone.now()
        booking_datetime = timezone.make_aware(
            datetime.combine(self.booking_date, self.booking_time)
        )
        return booking_datetime < now

    @property
    def booking_datetime(self):
        """Get booking as datetime object"""
        dt = datetime.combine(self.booking_date, self.booking_time)
        return timezone.make_aware(dt)

    @property
    def formatted_phone(self):
        """Format phone number for display"""
        phone = self.customer_phone
        if len(phone) == 10:
            return f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
        return phone

    @property
    def payment_status(self):
        """Get payment status"""
        if self.remaining_amount <= 0:
            return 'paid'
        elif self.advance_paid > 0:
            return 'partial'
        else:
            return 'unpaid'

    @property
    def booking_reference(self):
        """Generate booking reference number"""
        return f"ADV-{self.id:06d}"


class BookingPayment(models.Model):
    """
    Track payment history for advance bookings
    """
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('online', 'Online Transfer'),
        ('cheque', 'Cheque'),
    ]

    booking = models.ForeignKey(
        AdvanceBooking,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Transaction ID, cheque number, etc."
    )
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Booking Payment'
        verbose_name_plural = 'Booking Payments'

    def __str__(self):
        return f"₹{self.amount} - {self.booking.customer_name}"


class BookingStatusHistory(models.Model):
    """
    Track status changes for advance bookings
    """
    booking = models.ForeignKey(
        AdvanceBooking,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Booking Status History'
        verbose_name_plural = 'Booking Status Histories'

    def __str__(self):
        return f"{self.booking.customer_name}: {self.old_status} → {self.new_status}"

