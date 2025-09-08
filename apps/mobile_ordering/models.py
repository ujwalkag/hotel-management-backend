# Create new Django app: apps/mobile_ordering/

# apps/mobile_ordering/models.py - COMPLETE MOBILE ORDERING & KITCHEN DISPLAY SYSTEM
"""
COMPLETE MOBILE ORDERING SYSTEM
- Waiter mobile interface for table ordering
- Kitchen display with real-time status updates
- Table management with occupancy tracking
- Tables occupied until billed, then auto-available
"""

from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from apps.users.models import CustomUser
from apps.menu.models import MenuItem
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

class RestaurantTable(models.Model):
    """
    Restaurant tables for mobile ordering system
    SEPARATE from any existing table model to avoid conflicts
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Out of Order'),
        ('billing', 'Billing in Progress'),
    ]

    TABLE_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('vip', 'VIP'),
        ('outdoor', 'Outdoor'),
        ('private_dining', 'Private Dining'),
        ('bar_seating', 'Bar Seating'),
    ]

    # Basic table information
    table_number = models.CharField(max_length=10, unique=True)
    table_name = models.CharField(max_length=100, blank=True)
    seating_capacity = models.PositiveIntegerField(default=4)
    table_type = models.CharField(max_length=20, choices=TABLE_TYPE_CHOICES, default='regular')
    location_area = models.CharField(max_length=100, blank=True, help_text="Floor/Area location")

    # Current status
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)

    # Current session management - OCCUPIED UNTIL BILLED
    current_session_id = models.CharField(max_length=50, blank=True)
    session_start_time = models.DateTimeField(null=True, blank=True)
    current_customer_count = models.PositiveIntegerField(default=0)
    estimated_checkout_time = models.DateTimeField(null=True, blank=True)

    # Table analytics
    total_sessions_today = models.IntegerField(default=0)
    average_dining_duration = models.IntegerField(default=90, help_text="Average minutes per session")
    last_occupied_at = models.DateTimeField(null=True, blank=True)
    last_available_at = models.DateTimeField(null=True, blank=True)

    # Mobile ordering features
    qr_code_data = models.TextField(blank=True, help_text="QR code data for mobile ordering")
    mobile_ordering_enabled = models.BooleanField(default=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def start_new_session(self, customer_count=1, waiter=None):
        """Start a new dining session - TABLE OCCUPIED"""
        if self.current_status == 'available':
            session_id = f"T{self.table_number}-{timezone.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

            self.current_session_id = session_id
            self.session_start_time = timezone.now()
            self.current_customer_count = customer_count
            self.estimated_checkout_time = timezone.now() + timedelta(minutes=self.average_dining_duration)
            self.current_status = 'occupied'
            self.last_occupied_at = timezone.now()
            self.total_sessions_today += 1
            self.save()

            # Create table session record
            TableSession.objects.create(
                table=self,
                session_id=session_id,
                customer_count=customer_count,
                assigned_waiter=waiter,
                session_start=self.session_start_time,
                estimated_end=self.estimated_checkout_time
            )

            return session_id
        return None

    def end_current_session(self):
        """End current session - TABLE BECOMES AVAILABLE"""
        if self.current_session_id:
            try:
                session = TableSession.objects.get(session_id=self.current_session_id)
                session.end_session()
            except TableSession.DoesNotExist:
                pass

            # Calculate actual duration for analytics
            if self.session_start_time:
                actual_duration = (timezone.now() - self.session_start_time).total_seconds() / 60
                self.average_dining_duration = int((self.average_dining_duration + actual_duration) / 2)

            # Reset table - AUTO AVAILABLE
            self.current_session_id = ''
            self.session_start_time = None
            self.current_customer_count = 0
            self.estimated_checkout_time = None
            self.current_status = 'available'
            self.last_available_at = timezone.now()
            self.save()

    def generate_qr_code(self):
        """Generate QR code data for mobile ordering"""
        if not self.qr_code_data:
            self.qr_code_data = f"table={self.table_number}&location={self.location_area}&capacity={self.seating_capacity}&id={self.id}"
            self.save()
        return self.qr_code_data

    @property
    def active_orders_count(self):
        """Count of active orders for this table"""
        return self.mobile_orders.filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).count()

    @property
    def current_bill_total(self):
        """Current bill total for active session"""
        if not self.current_session_id:
            return Decimal('0.00')

        orders = self.mobile_orders.filter(
            session_id=self.current_session_id,
            status__in=['confirmed', 'preparing', 'ready', 'served']
        )
        return sum(order.total_amount for order in orders) or Decimal('0.00')

    @property
    def session_duration_minutes(self):
        """Current session duration in minutes"""
        if self.session_start_time:
            return int((timezone.now() - self.session_start_time).total_seconds() / 60)
        return 0

    def __str__(self):
        return f"Table {self.table_number} - {self.get_current_status_display()}"

    class Meta:
        db_table = 'mobile_restaurant_tables'
        verbose_name = 'Restaurant Table'
        verbose_name_plural = 'Restaurant Tables'
        ordering = ['table_number']

class TableSession(models.Model):
    """Track complete dining sessions - OCCUPIED UNTIL BILLED"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    table = models.ForeignKey(RestaurantTable, on_delete=models.CASCADE, related_name='sessions')
    session_id = models.CharField(max_length=50, unique=True)

    # Session details
    customer_count = models.PositiveIntegerField(default=1)
    assigned_waiter = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'role': 'waiter'}
    )

    # Timing
    session_start = models.DateTimeField()
    estimated_end = models.DateTimeField()
    actual_end = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Billing information
    total_orders = models.IntegerField(default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Payment tracking
    is_billed = models.BooleanField(default=False)
    billed_at = models.DateTimeField(null=True, blank=True)
    billed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='billed_sessions'
    )

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_totals(self, tax_percentage=5, service_charge_percentage=10):
        """Calculate session totals from all orders"""
        orders = WaiterOrder.objects.filter(session_id=self.session_id, status__in=['confirmed', 'preparing', 'ready', 'served'])

        self.total_orders = orders.count()
        self.subtotal = sum(order.total_amount for order in orders)
        self.tax_amount = self.subtotal * Decimal(str(tax_percentage / 100))
        self.service_charge = self.subtotal * Decimal(str(service_charge_percentage / 100))
        self.final_amount = self.subtotal + self.tax_amount + self.service_charge - self.discount_amount

        self.save()
        return self.final_amount

    def end_session(self):
        """Mark session as completed"""
        if self.status == 'active':
            self.status = 'completed'
            self.actual_end = timezone.now()
            self.calculate_totals()
            self.save()

    def mark_as_billed(self, billed_by_user):
        """Mark session as billed - TABLE BECOMES AVAILABLE"""
        self.is_billed = True
        self.billed_at = timezone.now()
        self.billed_by = billed_by_user
        self.save()

        # End the session and free the table
        self.end_session()
        self.table.end_current_session()

    @property
    def duration_minutes(self):
        """Session duration in minutes"""
        end_time = self.actual_end or timezone.now()
        return int((end_time - self.session_start).total_seconds() / 60)

    def __str__(self):
        return f"Session {self.session_id} - Table {self.table.table_number}"

    class Meta:
        db_table = 'mobile_table_sessions'
        verbose_name = 'Table Session'
        verbose_name_plural = 'Table Sessions'
        ordering = ['-created_at']

class WaiterOrder(models.Model):
    """WAITER MOBILE ORDERING SYSTEM - Orders placed by waiters"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready to Serve'),
        ('served', 'Served'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Basic order information
    table = models.ForeignKey(RestaurantTable, on_delete=models.CASCADE, related_name='mobile_orders')
    order_number = models.CharField(max_length=25, unique=True, blank=True)
    session_id = models.CharField(max_length=50)

    # Staff and customer info
    waiter = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True,
        limit_choices_to={'role': 'waiter'},
        related_name='waiter_orders'
    )
    customer_name = models.CharField(max_length=100, default="Guest")
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_count = models.PositiveIntegerField(default=1)

    # Order management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    special_instructions = models.TextField(blank=True)

    # Kitchen integration
    kitchen_notes = models.TextField(blank=True)
    estimated_prep_time = models.IntegerField(default=20, help_text="Estimated preparation time in minutes")
    actual_prep_time = models.IntegerField(null=True, blank=True)

    # Billing information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Enhanced billing integration
    is_in_billing = models.BooleanField(default=False)
    can_be_billed = models.BooleanField(default=True)

    # Additional features
    is_takeaway = models.BooleanField(default=False)
    delivery_time = models.DateTimeField(null=True, blank=True)

    # Timestamps for complete tracking
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    kitchen_received_at = models.DateTimeField(null=True, blank=True)
    preparation_started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-generate order number
        if not self.order_number:
            today = timezone.now().strftime('%y%m%d')
            count = WaiterOrder.objects.filter(created_at__date=timezone.now().date()).count() + 1
            self.order_number = f"WO-T{self.table.table_number}-{today}-{count:03d}"

        # Auto-set session ID if table has active session
        if not self.session_id and self.table.current_session_id:
            self.session_id = self.table.current_session_id

        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Calculate order totals from items"""
        items = self.order_items.all()
        self.subtotal = sum(item.total_price for item in items)

        # Apply discount
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / 100)

        self.total_amount = self.subtotal - self.discount_amount
        self.save(update_fields=['subtotal', 'discount_amount', 'total_amount'])
        return self.total_amount

    def confirm_order(self):
        """Confirm order and send to kitchen"""
        if self.status in ['draft', 'pending']:
            # Ensure table has active session
            if not self.table.current_session_id:
                self.table.start_new_session(self.customer_count, self.waiter)
                self.session_id = self.table.current_session_id

            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()

            # Send to kitchen
            self.send_to_kitchen()

            return True
        return False

    def send_to_kitchen(self):
        """Send order to kitchen display"""
        if self.status == 'confirmed':
            KitchenOrder.objects.create(
                waiter_order=self,
                table_number=self.table.table_number,
                customer_count=self.customer_count,
                priority=self.priority,
                estimated_prep_time=self.estimated_prep_time,
                special_instructions=self.special_instructions,
                kitchen_notes=self.kitchen_notes
            )

            self.status = 'preparing'
            self.kitchen_received_at = timezone.now()
            self.save()

    def mark_ready(self):
        """Mark order as ready for service"""
        if self.status == 'preparing':
            self.status = 'ready'
            self.ready_at = timezone.now()

            # Calculate actual prep time
            if self.preparation_started_at:
                prep_time = (self.ready_at - self.preparation_started_at).total_seconds() / 60
                self.actual_prep_time = int(prep_time)

            self.save()

            # Update kitchen display
            try:
                kitchen_order = KitchenOrder.objects.get(waiter_order=self)
                kitchen_order.mark_ready()
            except KitchenOrder.DoesNotExist:
                pass

    def mark_served(self):
        """Mark order as served to customers"""
        if self.status == 'ready':
            self.status = 'served'
            self.served_at = timezone.now()
            self.save()

    def mark_completed(self):
        """Mark order as completed"""
        if self.status == 'served':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()

    @property
    def total_items(self):
        """Total number of items in the order"""
        return sum(item.quantity for item in self.order_items.all())

    @property
    def wait_time_minutes(self):
        """How long the order has been waiting"""
        if self.kitchen_received_at:
            return int((timezone.now() - self.kitchen_received_at).total_seconds() / 60)
        return 0

    def __str__(self):
        return f"{self.order_number} - Table {self.table.table_number} ({self.get_status_display()})"

    class Meta:
        db_table = 'mobile_waiter_orders'
        verbose_name = 'Waiter Order'
        verbose_name_plural = 'Waiter Orders'
        ordering = ['-created_at']

class WaiterOrderItem(models.Model):
    """Individual items in a waiter order"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('cancelled', 'Cancelled'),
    ]

    waiter_order = models.ForeignKey(WaiterOrder, on_delete=models.CASCADE, related_name='order_items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Customization
    item_customizations = models.JSONField(default=dict, blank=True, help_text="Spice level, cooking preferences, etc.")
    special_instructions = models.TextField(blank=True)

    # Kitchen tracking
    assigned_cook = models.CharField(max_length=100, blank=True)
    prep_start_time = models.DateTimeField(null=True, blank=True)
    prep_end_time = models.DateTimeField(null=True, blank=True)
    prep_time_minutes = models.IntegerField(null=True, blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        """Total price for this item (quantity * unit_price)"""
        return self.quantity * self.unit_price

    @property
    def display_name(self):
        """Display name with customizations"""
        name = f"{self.menu_item.name_en} x {self.quantity}"
        if self.item_customizations:
            customizations = ", ".join([f"{k}: {v}" for k, v in self.item_customizations.items()])
            name += f" ({customizations})"
        return name

    def __str__(self):
        return f"{self.menu_item.name_en} x {self.quantity} - {self.waiter_order.order_number}"

    class Meta:
        db_table = 'mobile_waiter_order_items'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

class KitchenOrder(models.Model):
    """KITCHEN DISPLAY SYSTEM - Real-time order management"""
    STATUS_CHOICES = [
        ('received', 'Received'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready to Serve'),
        ('served', 'Served'),
        ('completed', 'Completed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Order reference
    waiter_order = models.OneToOneField(WaiterOrder, on_delete=models.CASCADE, related_name='kitchen_order')

    # Kitchen display info
    table_number = models.CharField(max_length=10)
    customer_count = models.PositiveIntegerField(default=1)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')

    # Kitchen management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    assigned_cook = models.CharField(max_length=100, blank=True)
    estimated_prep_time = models.IntegerField(default=20)

    # Time tracking
    received_at = models.DateTimeField(auto_now_add=True)
    preparation_started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Kitchen notes
    special_instructions = models.TextField(blank=True)
    kitchen_notes = models.TextField(blank=True)
    cook_comments = models.TextField(blank=True)

    @property
    def order_number(self):
        return self.waiter_order.order_number

    @property
    def total_items(self):
        return self.waiter_order.total_items

    @property
    def wait_time_minutes(self):
        """Time since order was received"""
        return int((timezone.now() - self.received_at).total_seconds() / 60)

    @property
    def is_overdue(self):
        """Check if order is taking longer than estimated"""
        return self.wait_time_minutes > self.estimated_prep_time

    @property
    def urgency_level(self):
        """Calculate urgency based on wait time and priority"""
        if self.is_overdue and self.priority in ['high', 'urgent']:
            return 'critical'
        elif self.is_overdue:
            return 'overdue'
        elif self.priority == 'urgent':
            return 'urgent'
        elif self.priority == 'high':
            return 'high'
        else:
            return 'normal'

    def start_preparation(self, cook_name=""):
        """Start preparing the order"""
        if self.status == 'received':
            self.status = 'preparing'
            self.preparation_started_at = timezone.now()
            self.assigned_cook = cook_name
            self.save()

            # Update waiter order
            self.waiter_order.preparation_started_at = self.preparation_started_at
            self.waiter_order.save()

    def mark_ready(self):
        """Mark order as ready for service"""
        if self.status == 'preparing':
            self.status = 'ready'
            self.ready_at = timezone.now()
            self.save()

            # Update waiter order
            self.waiter_order.mark_ready()

    def mark_served(self):
        """Mark order as served"""
        if self.status == 'ready':
            self.status = 'served'
            self.served_at = timezone.now()
            self.save()

            # Update waiter order
            self.waiter_order.mark_served()

    def mark_completed(self):
        """Mark order as completed"""
        if self.status == 'served':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()

    def __str__(self):
        return f"Kitchen Order - {self.order_number} (Table {self.table_number})"

    class Meta:
        db_table = 'mobile_kitchen_orders'
        verbose_name = 'Kitchen Order'
        verbose_name_plural = 'Kitchen Orders'
        ordering = ['priority', 'received_at']

# Signals for automatic management
@receiver(post_save, sender=WaiterOrder)
def handle_order_creation(sender, instance, created, **kwargs):
    """Handle new order creation"""
    if created and instance.status in ['pending', 'confirmed']:
        # Ensure table has active session
        if not instance.table.current_session_id:
            session_id = instance.table.start_new_session(instance.customer_count, instance.waiter)
            instance.session_id = session_id
            instance.save()

@receiver(post_save, sender=WaiterOrder)
def update_session_totals(sender, instance, **kwargs):
    """Update session totals when order changes"""
    if instance.session_id:
        try:
            session = TableSession.objects.get(session_id=instance.session_id)
            session.calculate_totals()
        except TableSession.DoesNotExist:
            pass

@receiver(pre_delete, sender=WaiterOrder)
def cleanup_kitchen_orders(sender, instance, **kwargs):
    """Clean up kitchen orders when waiter order is deleted"""
    KitchenOrder.objects.filter(waiter_order=instance).delete()

