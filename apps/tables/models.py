
# apps/tables/models.py - UPDATED FOR ENHANCED BILLING INTEGRATION
from django.db import models
from apps.users.models import CustomUser
from apps.menu.models import MenuItem
from django.utils.timezone import now
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from decimal import Decimal

class RestaurantTable(models.Model):
    """Restaurant table management with enhanced billing integration"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'), 
        ('reserved', 'Reserved'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Out of Order'),
    ]

    table_number = models.CharField(max_length=10, unique=True)
    capacity = models.PositiveIntegerField(default=4)
    location = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)

    # Enhanced billing integration
    current_session_id = models.CharField(max_length=50, blank=True, help_text="Current billing session")
    last_occupied_at = models.DateTimeField(null=True, blank=True)
    last_available_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Table {self.table_number}"

    @property
    def active_orders_count(self):
        """Count of active orders for this table"""
        return self.orders.filter(status__in=['pending', 'in_progress', 'ready']).count()

    @property
    def current_bill_total(self):
        """Current bill total from all active orders"""
        active_orders = self.orders.filter(status__in=['pending', 'in_progress', 'ready', 'completed'])
        return sum(order.total_amount for order in active_orders)

    @property
    def has_active_orders(self):
        """Check if table has any active orders"""
        return self.active_orders_count > 0

    def occupy_table(self, session_id=None):
        """Mark table as occupied and create session"""
        self.status = 'occupied'
        self.current_session_id = session_id or str(uuid.uuid4())
        self.last_occupied_at = now()
        self.save()
        return self.current_session_id

    def release_table(self):
        """Mark table as available and clear session"""
        self.status = 'available'
        self.current_session_id = ''
        self.last_available_at = now()
        self.save()

    class Meta:
        db_table = 'restaurant_tables'
        ordering = ['table_number']
        verbose_name = 'Restaurant Table'
        verbose_name_plural = 'Restaurant Tables'

class TableOrder(models.Model):
    """Orders placed via mobile for specific tables - Enhanced billing integration"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'), 
        ('ready', 'Ready to Serve'),
        ('completed', 'Completed'),
        ('billed', 'Billed'),
        ('cancelled', 'Cancelled'),
    ]

    # Table and Order Information
    table = models.ForeignKey(RestaurantTable, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    session_id = models.CharField(max_length=50, blank=True, help_text="Links to table session")

    # Staff and Customer Information
    waiter = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, default="Guest")
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_count = models.PositiveIntegerField(default=1)

    # Order Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_instructions = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Enhanced Billing Integration
    is_in_enhanced_billing = models.BooleanField(default=False, help_text="Appears in enhanced billing dashboard")
    enhanced_billing_notes = models.TextField(blank=True)
    can_be_billed = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    billed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number: T01-ABC123
            self.order_number = f"T{self.table.table_number}-{uuid.uuid4().hex[:6].upper()}"

        # Auto-assign session ID from table if not set
        if not self.session_id and self.table.current_session_id:
            self.session_id = self.table.current_session_id

        super().save(*args, **kwargs)

    def calculate_total(self):
        """Calculate total amount from order items"""
        total = sum(item.quantity * item.price for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

    def add_to_enhanced_billing(self):
        """Add this order to enhanced billing dashboard"""
        self.is_in_enhanced_billing = True
        self.save(update_fields=['is_in_enhanced_billing'])

        # Ensure table is occupied
        if self.table.status != 'occupied':
            self.table.occupy_table(self.session_id)

    def mark_completed(self):
        """Mark order as completed"""
        self.status = 'completed'
        self.completed_at = now()
        self.save(update_fields=['status', 'completed_at'])

    def mark_billed(self):
        """Mark order as billed and update table status if no more active orders"""
        self.status = 'billed'
        self.billed_at = now()
        self.is_in_enhanced_billing = False
        self.save(update_fields=['status', 'billed_at', 'is_in_enhanced_billing'])

        # Check if table can be released
        remaining_orders = self.table.orders.filter(
            status__in=['pending', 'in_progress', 'ready', 'completed']
        ).exclude(id=self.id).count()

        if remaining_orders == 0:
            self.table.release_table()

    def __str__(self):
        return f"{self.order_number} - Table {self.table.table_number} ({self.status})"

    class Meta:
        db_table = 'table_orders'
        ordering = ['-created_at']
        verbose_name = 'Table Order'
        verbose_name_plural = 'Table Orders'

class OrderItem(models.Model):
    """Individual items in a table order"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('cancelled', 'Cancelled'),
    ]

    table_order = models.ForeignKey(TableOrder, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of order
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_instructions = models.TextField(blank=True)

    # Kitchen Integration
    kitchen_notes = models.TextField(blank=True)
    estimated_prep_time = models.IntegerField(default=15, help_text="Minutes")
    actual_prep_time = models.IntegerField(null=True, blank=True)

    # Timestamps
    order_time = models.DateTimeField(auto_now_add=True)
    preparation_started = models.DateTimeField(null=True, blank=True)
    ready_time = models.DateTimeField(null=True, blank=True)
    served_time = models.DateTimeField(null=True, blank=True)

    @property
    def total_price(self):
        return self.quantity * self.price

    @property
    def item_display_name(self):
        """Display name for enhanced billing"""
        return f"{self.menu_item.name_en} x {self.quantity}"

    def start_preparation(self):
        """Mark item as being prepared"""
        self.status = 'preparing'
        self.preparation_started = now()
        self.save(update_fields=['status', 'preparation_started'])

    def mark_ready(self):
        """Mark item as ready"""
        self.status = 'ready'
        self.ready_time = now()

        if self.preparation_started:
            prep_time = (self.ready_time - self.preparation_started).total_seconds() / 60
            self.actual_prep_time = int(prep_time)

        self.save(update_fields=['status', 'ready_time', 'actual_prep_time'])

    def mark_served(self):
        """Mark item as served"""
        self.status = 'served'
        self.served_time = now()
        self.save(update_fields=['status', 'served_time'])

    def __str__(self):
        return f"{self.menu_item.name_en} x {self.quantity} - {self.table_order.order_number}"

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

class EnhancedBillingSession(models.Model):
    """Session tracking for enhanced billing - groups multiple orders for a table"""
    table = models.ForeignKey(RestaurantTable, on_delete=models.CASCADE, related_name='billing_sessions')
    session_id = models.CharField(max_length=50, unique=True)

    # Customer Information (can be updated from mobile orders)
    customer_name = models.CharField(max_length=255, default="Guest")
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_count = models.PositiveIntegerField(default=1)

    # Session Status
    status = models.CharField(max_length=20, default='active')  # active, completed, billed

    # Billing Information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Payment Information
    payment_method = models.CharField(max_length=20, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def calculate_totals(self):
        """Calculate session totals from all associated orders"""
        orders = TableOrder.objects.filter(session_id=self.session_id)
        self.subtotal = sum(order.total_amount for order in orders)
        # Tax and discount would be calculated here
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.save(update_fields=['subtotal', 'total_amount', 'updated_at'])

    def mark_completed(self):
        """Mark session as completed and release table"""
        self.status = 'completed'
        self.completed_at = now()
        self.save()

        # Mark all associated orders as billed
        TableOrder.objects.filter(session_id=self.session_id).update(
            status='billed',
            billed_at=now(),
            is_in_enhanced_billing=False
        )

        # Release table
        self.table.release_table()

    def __str__(self):
        return f"Session {self.session_id} - Table {self.table.table_number}"

    class Meta:
        db_table = 'enhanced_billing_sessions'
        ordering = ['-created_at']

# Signals
@receiver(post_save, sender=TableOrder)
def update_table_status(sender, instance, created, **kwargs):
    """Update table status when order is created"""
    if created and instance.status in ['pending', 'in_progress']:
        # Occupy table and add to enhanced billing
        instance.table.occupy_table(instance.session_id)
        instance.add_to_enhanced_billing()

@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    """Update order total when items change"""
    instance.table_order.calculate_total()

