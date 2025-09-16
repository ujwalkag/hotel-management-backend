# apps/restaurant/models.py - Kitchen Display System Models
from django.db import models
from apps.users.models import CustomUser
from decimal import Decimal
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import uuid

class Table(models.Model):
    """Restaurant table management"""
    STATUS_CHOICES = [
        ('free', 'Free'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance')
    ]

    table_number = models.CharField(max_length=10, unique=True)
    capacity = models.IntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='free')
    location = models.CharField(max_length=100, blank=True, help_text='Table location/section')
    last_occupied_at = models.DateTimeField(null=True, blank=True)
    last_billed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'restaurant_table'
        ordering = ['table_number']

    def __str__(self):
        return f"Table {self.table_number} ({self.get_status_display()})"

    @property
    def is_available(self):
        return self.status == 'free' and self.is_active

    def mark_occupied(self):
        """Mark table as occupied when first order is placed"""
        if self.status == 'free':
            self.status = 'occupied'
            self.last_occupied_at = timezone.now()
            self.save(update_fields=['status', 'last_occupied_at'])

    def mark_free(self):
        """Mark table as free after billing is completed"""
        self.status = 'free'
        self.last_billed_at = timezone.now()
        self.save(update_fields=['status', 'last_billed_at'])

    def get_active_orders(self):
        """Get all active orders for this table"""
        return self.orders.filter(status__in=['pending', 'preparing', 'ready'])

    def get_total_bill_amount(self):
        """Calculate total bill amount for active orders"""
        return self.orders.filter(
            status__in=['pending', 'preparing', 'ready', 'served']
        ).aggregate(
            total=models.Sum(models.F('quantity') * models.F('menu_item__price'))
        )['total'] or Decimal('0.00')

class MenuCategory(models.Model):
    """Menu item categories"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Icon class or emoji')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'menu_category'
        ordering = ['display_order', 'name']
        verbose_name_plural = 'Menu Categories'

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    """Restaurant menu items"""
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock'),
        ('discontinued', 'Discontinued'),
        ('seasonal', 'Seasonal')
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='items')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    preparation_time = models.PositiveIntegerField(default=15, help_text='Preparation time in minutes')
    is_veg = models.BooleanField(default=True)
    is_spicy = models.BooleanField(default=False)
    allergens = models.CharField(max_length=500, blank=True, help_text='Comma-separated allergens')
    image_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'menu_item'
        ordering = ['category__display_order', 'display_order', 'name']

    def __str__(self):
        return f"{self.name} - ₹{self.price}"

    @property
    def is_available(self):
        return self.availability == 'available' and self.is_active

    @property
    def profit_margin(self):
        if self.cost_price:
            return ((self.price - self.cost_price) / self.price) * 100
        return 0

class Order(models.Model):
    """Restaurant orders"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('cancelled', 'Cancelled')
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]

    # Order identification
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order_number = models.CharField(max_length=20, unique=True, blank=True)

    # Order details
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Order management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    special_instructions = models.TextField(blank=True)

    # Staff tracking
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='orders_created')
    confirmed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_confirmed')
    prepared_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_prepared')
    served_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_served')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    preparation_started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)

    # Estimated times
    estimated_preparation_time = models.PositiveIntegerField(null=True, blank=True)
    estimated_ready_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'restaurant_order'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Auto-generate order number
        if not self.order_number:
            self.order_number = f"ORD{timezone.now().strftime('%Y%m%d')}{Order.objects.count() + 1:04d}"

        # Auto-calculate total price
        self.unit_price = self.menu_item.price
        self.total_price = self.unit_price * self.quantity

        # Set estimated times
        if not self.estimated_preparation_time:
            self.estimated_preparation_time = self.menu_item.preparation_time

        if self.status == 'preparing' and not self.preparation_started_at:
            self.preparation_started_at = timezone.now()
            self.estimated_ready_time = timezone.now() + timezone.timedelta(
                minutes=self.estimated_preparation_time
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.table.table_number} - {self.menu_item.name}"

    @property
    def preparation_time_remaining(self):
        """Calculate remaining preparation time in minutes"""
        if self.estimated_ready_time and self.status == 'preparing':
            remaining = self.estimated_ready_time - timezone.now()
            return max(0, remaining.total_seconds() / 60)
        return 0

    @property
    def is_overdue(self):
        """Check if order is overdue"""
        if self.estimated_ready_time and self.status == 'preparing':
            return timezone.now() > self.estimated_ready_time
        return False

    @property
    def total_time_elapsed(self):
        """Total time since order was placed"""
        return (timezone.now() - self.created_at).total_seconds() / 60

    def update_status(self, new_status, user=None):
        """Update order status with proper tracking"""
        old_status = self.status
        self.status = new_status

        if new_status == 'confirmed' and user:
            self.confirmed_by = user
            self.confirmed_at = timezone.now()
        elif new_status == 'preparing' and user:
            self.prepared_by = user
            self.preparation_started_at = timezone.now()
        elif new_status == 'ready':
            self.ready_at = timezone.now()
        elif new_status == 'served' and user:
            self.served_by = user
            self.served_at = timezone.now()

        self.save()

        # Trigger real-time update
        from .utils import broadcast_order_update
        broadcast_order_update(self, old_status)

class OrderSession(models.Model):
    """Track order sessions for billing"""
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='order_sessions')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'restaurant_order_session'
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.session_id} - Table {self.table.table_number}"

    def calculate_totals(self):
        """Calculate session totals"""
        orders = self.table.orders.filter(
            created_at__gte=self.created_at,
            status__in=['confirmed', 'preparing', 'ready', 'served']
        )

        self.total_amount = orders.aggregate(
            total=models.Sum('total_price')
        )['total'] or Decimal('0.00')

        # Calculate tax (assuming 18% GST)
        self.tax_amount = self.total_amount * Decimal('0.05')
        self.final_amount = self.total_amount + self.tax_amount - self.discount_amount
        self.save()

    def complete_session(self):
        """Complete the order session and free the table"""
        self.is_active = False
        self.completed_at = timezone.now()
        self.payment_status = 'completed'
        self.save()

        # Free the table
        self.table.mark_free()

# Signal handlers for automatic table management
@receiver(post_save, sender=Order)
def handle_order_created(sender, instance, created, **kwargs):
    """Automatically mark table as occupied when first order is placed"""
    if created and instance.table.status == 'free':
        instance.table.mark_occupied()

@receiver(post_save, sender=OrderSession)
def handle_session_completed(sender, instance, **kwargs):
    """Handle session completion"""
    if not instance.is_active and instance.payment_status == 'completed':
        # Additional cleanup can be added here
        pass

class KitchenDisplaySettings(models.Model):
    """Settings for Kitchen Display System"""
    name = models.CharField(max_length=100, unique=True)
    audio_enabled = models.BooleanField(default=True)
    auto_refresh_interval = models.PositiveIntegerField(default=30, help_text='Refresh interval in seconds')
    display_completed_orders = models.BooleanField(default=False)
    completed_order_display_time = models.PositiveIntegerField(default=300, help_text='Time in seconds')
    priority_color_coding = models.BooleanField(default=True)
    show_preparation_time = models.BooleanField(default=True)
    show_order_notes = models.BooleanField(default=True)
    max_orders_per_screen = models.PositiveIntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kitchen_display_settings'

    def __str__(self):
        return self.name

