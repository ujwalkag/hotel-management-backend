# apps/enhanced_billing/models.py
"""
ENHANCED BILLING SYSTEM - GST Compliant with Mobile Order Integration
COMPATIBLE: Works with existing billing and new mobile ordering
NO CONFLICTS: Separate database tables from existing Bill model
"""

from django.db import models
from django.utils import timezone
from apps.users.models import CustomUser  # Your existing user model
from decimal import Decimal
import uuid

class EnhancedBill(models.Model):
    """
    Enhanced billing system that integrates with mobile orders
    SEPARATE from existing Bill model to avoid conflicts
    Provides GST compliance and multi-payment support
    """
    BILL_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ready', 'Ready for Payment'),
        ('processing', 'Processing Payment'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('mixed', 'Mixed Payment'),
        ('pending', 'Pending'),
    ]

    BILL_TYPE_CHOICES = [
        ('dine_in', 'Dine In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    ]

    # Bill identification
    bill_number = models.CharField(max_length=20, unique=True, blank=True)

    # Reference to table session (if from mobile ordering)
    table_session_id = models.CharField(max_length=50, blank=True, help_text="Table session from mobile ordering")

    # Customer information
    customer_name = models.CharField(max_length=100, default="Guest")
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_count = models.PositiveIntegerField(default=1)

    # Bill details
    bill_type = models.CharField(max_length=20, choices=BILL_TYPE_CHOICES, default='dine_in')
    table_number = models.CharField(max_length=10, blank=True)
    waiter = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'waiter'},
        related_name='served_enhanced_bills'
    )

    # Financial details
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # GST calculations (GST compliant)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.5)
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.5)
    igst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Service charges
    service_charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    service_charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Final amounts
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    round_off_amount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment tracking
    status = models.CharField(max_length=20, choices=BILL_STATUS_CHOICES, default='draft')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='pending')

    # Multiple payment support
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    card_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    upi_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Staff tracking
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_enhanced_bills'
    )
    processed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_enhanced_bills'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    bill_date = models.DateField(auto_now_add=True)
    bill_time = models.TimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Additional information
    special_instructions = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # Auto-generate bill number
        if not self.bill_number:
            today = timezone.now().strftime('%y%m%d')
            count = EnhancedBill.objects.filter(created_at__date=timezone.now().date()).count() + 1
            self.bill_number = f"ENH-{today}-{count:04d}"

        super().save(*args, **kwargs)

    def add_orders_from_session(self, session_id):
        """Add all orders from a table session to this bill - MOBILE ORDER INTEGRATION"""
        try:
            # Import here to avoid circular import
            from apps.mobile_ordering.models import WaiterOrder

            orders = WaiterOrder.objects.filter(
                session_id=session_id,
                status__in=['confirmed', 'preparing', 'ready', 'served', 'completed']
            )

            for order in orders:
                # Create bill items from order items
                for order_item in order.order_items.all():
                    EnhancedBillItem.objects.create(
                        bill=self,
                        waiter_order_id=order.id,
                        menu_item_name=order_item.menu_item.name_en,
                        item_name=order_item.menu_item.name_en,
                        quantity=order_item.quantity,
                        unit_price=order_item.unit_price,
                        total_price=order_item.total_price,
                        customizations=order_item.item_customizations,
                        special_instructions=order_item.special_instructions
                    )

            # Set table session reference
            self.table_session_id = session_id

            # Calculate totals
            self.calculate_totals()

        except ImportError:
            # If mobile_ordering app is not available, continue without it
            pass

    def add_manual_items(self, items_data):
        """Add manual items for traditional billing"""
        for item in items_data:
            EnhancedBillItem.objects.create(
                bill=self,
                item_name=item['name'],
                quantity=item['quantity'],
                unit_price=Decimal(str(item['price'])),
                total_price=Decimal(str(item['quantity'])) * Decimal(str(item['price']))
            )

        self.calculate_totals()

    def calculate_totals(self):
        """Calculate all bill totals with GST compliance"""
        # Calculate subtotal from bill items
        bill_items = self.bill_items.all()
        self.subtotal = sum(item.total_price for item in bill_items)

        # Apply discount
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / 100)

        # Calculate service charge
        taxable_amount = self.subtotal - self.discount_amount
        self.service_charge_amount = taxable_amount * (self.service_charge_percentage / 100)

        # Calculate GST - PROPER GST COMPLIANCE
        gst_base = taxable_amount + self.service_charge_amount

        if self.igst_percentage > 0:
            # Interstate - IGST only
            self.igst_amount = gst_base * (self.igst_percentage / 100)
            self.cgst_amount = 0
            self.sgst_amount = 0
        else:
            # Intrastate - CGST + SGST
            self.cgst_amount = gst_base * (self.cgst_percentage / 100)
            self.sgst_amount = gst_base * (self.sgst_percentage / 100)
            self.igst_amount = 0

        self.total_tax_amount = self.cgst_amount + self.sgst_amount + self.igst_amount

        # Calculate final total
        self.total_amount = (
            self.subtotal - self.discount_amount + 
            self.service_charge_amount + self.total_tax_amount
        )

        # Round off to nearest rupee
        self.round_off_amount = round(self.total_amount) - self.total_amount
        self.final_amount = round(self.total_amount)

        # Calculate balance
        self.balance_amount = self.final_amount - self.total_paid

        self.save()
        return self.final_amount

    def process_payment(self, payment_method, cash=0, card=0, upi=0, processed_by=None):
        """Process payment for the bill - MULTI-PAYMENT SUPPORT"""
        self.cash_amount = Decimal(str(cash))
        self.card_amount = Decimal(str(card))
        self.upi_amount = Decimal(str(upi))
        self.total_paid = self.cash_amount + self.card_amount + self.upi_amount
        self.payment_method = payment_method
        self.processed_by = processed_by

        if self.total_paid >= self.final_amount:
            self.status = 'paid'
            self.paid_at = timezone.now()
            self.balance_amount = 0

            # Mark table session as billed if it's from mobile ordering
            if self.table_session_id:
                self._mark_table_session_billed(processed_by)
        else:
            self.status = 'partially_paid'
            self.balance_amount = self.final_amount - self.total_paid

        self.save()
        return self.status == 'paid'

    def _mark_table_session_billed(self, processed_by):
        """Mark table session as billed - TABLE BECOMES AVAILABLE"""
        try:
            from apps.mobile_ordering.models import TableSession
            session = TableSession.objects.get(session_id=self.table_session_id)
            session.mark_as_billed(processed_by)
        except ImportError:
            # If mobile_ordering app is not available, continue without it
            pass
        except Exception:
            # If session not found, continue without error
            pass

    def cancel_bill(self, reason=""):
        """Cancel the bill"""
        if self.status in ['draft', 'ready']:
            self.status = 'cancelled'
            self.internal_notes += f" [CANCELLED: {reason}]"
            self.save()
            return True
        return False

    def generate_receipt_data(self):
        """Generate structured data for receipt printing"""
        return {
            'bill_number': self.bill_number,
            'bill_date': self.bill_date.strftime('%d/%m/%Y'),
            'bill_time': self.bill_time.strftime('%H:%M'),
            'table_number': self.table_number,
            'customer_name': self.customer_name,
            'customer_count': self.customer_count,
            'waiter': self.waiter.get_full_name() if self.waiter else 'N/A',
            'items': [
                {
                    'name': item.item_name,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.total_price),
                    'customizations': item.customizations
                }
                for item in self.bill_items.all()
            ],
            'subtotal': float(self.subtotal),
            'discount_amount': float(self.discount_amount),
            'service_charge': float(self.service_charge_amount),
            'cgst_amount': float(self.cgst_amount),
            'sgst_amount': float(self.sgst_amount),
            'igst_amount': float(self.igst_amount),
            'total_tax': float(self.total_tax_amount),
            'total_amount': float(self.total_amount),
            'round_off': float(self.round_off_amount),
            'final_amount': float(self.final_amount),
            'payment_method': self.get_payment_method_display(),
            'cash_amount': float(self.cash_amount),
            'card_amount': float(self.card_amount),
            'upi_amount': float(self.upi_amount),
            'total_paid': float(self.total_paid),
            'balance': float(self.balance_amount)
        }

    @property
    def total_items(self):
        """Total number of items in the bill"""
        return sum(item.quantity for item in self.bill_items.all())

    @property
    def effective_tax_percentage(self):
        """Effective tax percentage applied"""
        if self.igst_percentage > 0:
            return self.igst_percentage
        else:
            return self.cgst_percentage + self.sgst_percentage

    def __str__(self):
        return f"Bill {self.bill_number} - Table {self.table_number} (₹{self.final_amount})"

    class Meta:
        db_table = 'enhanced_bills'
        verbose_name = 'Enhanced Bill'
        verbose_name_plural = 'Enhanced Bills'
        ordering = ['-created_at']

class EnhancedBillItem(models.Model):
    """Individual items in an enhanced bill"""
    bill = models.ForeignKey(EnhancedBill, on_delete=models.CASCADE, related_name='bill_items')

    # Reference to waiter order (if from mobile ordering)
    waiter_order_id = models.IntegerField(null=True, blank=True, help_text="Reference to WaiterOrder ID")

    # Menu item reference (if available)
    menu_item_name = models.CharField(max_length=200, blank=True, help_text="Menu item name for reference")

    # Item details (stored for historical record)
    item_name = models.CharField(max_length=200)
    item_description = models.TextField(blank=True)

    # Pricing
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Customizations (stored as JSON for flexibility)
    customizations = models.JSONField(default=dict, blank=True)
    special_instructions = models.TextField(blank=True)

    # Tax information
    is_taxable = models.BooleanField(default=True)
    tax_category = models.CharField(max_length=50, blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def display_name(self):
        """Display name with customizations"""
        name = f"{self.item_name} x {self.quantity}"
        if self.customizations:
            customizations = ", ".join([f"{k}: {v}" for k, v in self.customizations.items()])
            name += f" ({customizations})"
        return name

    def __str__(self):
        return f"{self.item_name} x {self.quantity} - {self.bill.bill_number}"

    class Meta:
        db_table = 'enhanced_bill_items'
        verbose_name = 'Enhanced Bill Item'
        verbose_name_plural = 'Enhanced Bill Items'

class BillPaymentRecord(models.Model):
    """Track individual payment transactions for a bill"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    bill = models.ForeignKey(EnhancedBill, on_delete=models.CASCADE, related_name='payment_records')
    transaction_id = models.CharField(max_length=50, unique=True, blank=True)

    # Payment details
    payment_method = models.CharField(max_length=20, choices=EnhancedBill.PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Transaction info
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    reference_number = models.CharField(max_length=100, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    # Staff tracking
    processed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_payments'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Additional info
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            today = timezone.now().strftime('%y%m%d%H%M')
            self.transaction_id = f"TXN-{today}-{uuid.uuid4().hex[:6].upper()}"

        super().save(*args, **kwargs)

    def mark_completed(self):
        """Mark payment as completed"""
        self.status = 'completed'
        self.processed_at = timezone.now()
        self.save()

    def mark_failed(self, reason=""):
        """Mark payment as failed"""
        self.status = 'failed'
        self.notes += f" [FAILED: {reason}]"
        self.save()

    def __str__(self):
        return f"Payment {self.transaction_id} - ₹{self.amount}"

    class Meta:
        db_table = 'enhanced_bill_payments'
        verbose_name = 'Bill Payment Record'
        verbose_name_plural = 'Bill Payment Records'
        ordering = ['-created_at']

class BillingSession(models.Model):
    """Track billing sessions for analytics and reporting"""
    biller = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__in': ['staff', 'admin']},
        related_name='enhanced_billing_sessions'
    )

    # Session details
    session_start = models.DateTimeField(auto_now_add=True)
    session_end = models.DateTimeField(null=True, blank=True)

    # Session statistics
    bills_processed = models.IntegerField(default=0)
    total_amount_processed = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cash_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    card_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    upi_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # System info
    device_info = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    @property
    def session_duration_minutes(self):
        """Session duration in minutes"""
        end_time = self.session_end or timezone.now()
        return int((end_time - self.session_start).total_seconds() / 60)

    def end_session(self):
        """End the billing session"""
        if not self.session_end:
            self.session_end = timezone.now()

            # Calculate session totals
            bills = EnhancedBill.objects.filter(
                processed_by=self.biller,
                created_at__range=[self.session_start, self.session_end]
            )

            self.bills_processed = bills.count()
            self.total_amount_processed = sum(bill.final_amount for bill in bills)
            self.cash_collected = sum(bill.cash_amount for bill in bills)
            self.card_collected = sum(bill.card_amount for bill in bills)
            self.upi_collected = sum(bill.upi_amount for bill in bills)

            self.save()

    def __str__(self):
        return f"Billing Session - {self.biller.get_full_name() if self.biller else 'Unknown'} ({self.session_start.strftime('%d/%m/%Y %H:%M')})"

    class Meta:
        db_table = 'enhanced_billing_sessions'
        verbose_name = 'Billing Session'
        verbose_name_plural = 'Billing Sessions'
        ordering = ['-session_start']

