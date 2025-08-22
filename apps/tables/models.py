# apps/tables/models.py
from django.db import models
from apps.users.models import CustomUser
from apps.menu.models import MenuItem
from django.utils.timezone import now
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

class RestaurantTable(models.Model):
    table_number = models.CharField(max_length=10, unique=True)
    capacity = models.PositiveIntegerField(default=4)
    location = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_occupied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Table {self.table_number}"

    @property
    def active_orders_count(self):
        return self.orders.filter(status__in=['pending', 'in_progress']).count()
    
    @property
    def current_order(self):
        return self.orders.filter(status__in=['pending', 'in_progress']).first()

    class Meta:
        db_table = 'tables_restaurant_table'
        ordering = ['table_number']
        verbose_name = 'Restaurant Table'
        verbose_name_plural = 'Restaurant Tables'

class TableOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'), 
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('billed', 'Billed'),
    )

    table = models.ForeignKey(RestaurantTable, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    waiter = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_count = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_instructions = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            self.order_number = f"T{self.table.table_number}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def calculate_total(self):
        """Calculate total amount from order items"""
        total = sum(item.quantity * item.price for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

    def mark_completed(self):
        """Mark order as completed"""
        self.status = 'completed'
        self.completed_at = now()
        self.save(update_fields=['status', 'completed_at'])
        
        # Update table occupancy if no more active orders
        if self.table.active_orders_count == 0:
            self.table.is_occupied = False
            self.table.save(update_fields=['is_occupied'])

    def __str__(self):
        return f"{self.order_number} - Table {self.table.table_number}"

    class Meta:
        db_table = 'tables_table_order'
        ordering = ['-created_at']
        verbose_name = 'Table Order'
        verbose_name_plural = 'Table Orders'

class OrderItem(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
        ('cancelled', 'Cancelled'),
    )

    table_order = models.ForeignKey(TableOrder, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_instructions = models.TextField(blank=True)
    order_time = models.DateTimeField(auto_now_add=True)
    preparation_started = models.DateTimeField(null=True, blank=True)
    ready_time = models.DateTimeField(null=True, blank=True)
    served_time = models.DateTimeField(null=True, blank=True)

    @property
    def total_price(self):
        return self.quantity * self.price
    
    @property
    def preparation_time_minutes(self):
        if self.preparation_started and self.ready_time:
            diff = self.ready_time - self.preparation_started
            return diff.total_seconds() / 60
        return None

    def mark_preparing(self):
        self.status = 'preparing'
        self.preparation_started = now()
        self.save(update_fields=['status', 'preparation_started'])

    def mark_ready(self):
        self.status = 'ready'
        self.ready_time = now()
        self.save(update_fields=['status', 'ready_time'])

    def mark_served(self):
        self.status = 'served'
        self.served_time = now()
        self.save(update_fields=['status', 'served_time'])

    def __str__(self):
        return f"{self.menu_item.name_en} x {self.quantity} - Table {self.table_order.table.table_number}"

    class Meta:
        db_table = 'tables_order_item'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

class KitchenDisplayItem(models.Model):
    """Items displayed on kitchen screen with additional display properties"""
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='kitchen_display')
    display_time = models.DateTimeField(auto_now_add=True)
    estimated_prep_time = models.PositiveIntegerField(default=15)  # minutes
    is_priority = models.BooleanField(default=False)
    is_highlighted = models.BooleanField(default=False)
    kitchen_notes = models.TextField(blank=True)

    @property
    def time_since_order(self):
        """Time elapsed since order was placed (in minutes)"""
        diff = now() - self.order_item.order_time
        return int(diff.total_seconds() / 60)
    
    @property
    def is_overdue(self):
        """Check if item is overdue based on estimated prep time"""
        return self.time_since_order > self.estimated_prep_time

    def __str__(self):
        return f"Kitchen Display: {self.order_item}"

    class Meta:
        db_table = 'tables_kitchen_display_item'
        ordering = ['-is_priority', 'display_time']
        verbose_name = 'Kitchen Display Item'
        verbose_name_plural = 'Kitchen Display Items'

# Signals
@receiver(post_save, sender=OrderItem)
def create_kitchen_display_item(sender, instance, created, **kwargs):
    """Automatically create kitchen display item when order item is created"""
    if created and instance.status == 'pending':
        KitchenDisplayItem.objects.get_or_create(
            order_item=instance,
            defaults={'estimated_prep_time': 15}
        )

@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    """Update table order total when order item changes"""
    instance.table_order.calculate_total()
