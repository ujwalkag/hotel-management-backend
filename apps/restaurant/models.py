# apps/restaurant/models.py - COMPLETE Enhanced Kitchen Display System Models with ALL FIXES INTEGRATED
from django.db import models
from apps.users.models import CustomUser
from decimal import Decimal
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import uuid
import json

class Table(models.Model):
    """Restaurant table management with enhanced admin functionality"""
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
    # Enhanced fields for better management
    qr_code_url = models.URLField(blank=True, help_text='QR code for mobile ordering')
    notes = models.TextField(blank=True, help_text='Admin notes about the table')
    priority_level = models.IntegerField(default=1, help_text='1=Normal, 2=VIP, 3=Premium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

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
        """Mark table as free after billing is completed - FIXED"""
        from django.utils import timezone
        self.status = 'free'
        self.last_billed_at = timezone.now()
        self.save(update_fields=['status', 'last_billed_at'])

        # Broadcast table update
        try:
            from .utils import broadcast_table_update
            broadcast_table_update(self, 'occupied')
        except Exception:
            pass  # Don't fail if broadcasting fails

    def get_active_orders(self):
        """Get all active orders for this table - FIXED"""
        return self.orders.filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        )
    def get_session_orders(self):
        """Get orders for billing scoped to the active session timeframe."""
        from django.utils import timezone

        active_session = self.order_sessions.filter(is_active=True).first()
        if active_session:
            start_time = active_session.created_at
            end_time = active_session.completed_at or timezone.now()
            return (
                self.orders
                    .filter(
                        created_at__gte=start_time,
                        created_at__lte=end_time,
                        status__in=['pending', 'confirmed', 'preparing', 'ready', 'served']
                    )
                    .exclude(status='cancelled')
                    .order_by('created_at')
            )

        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.orders
                .filter(
                    created_at__gte=today,
                    status__in=['pending', 'confirmed', 'preparing', 'ready', 'served']
                )
                .exclude(status='cancelled')
                .order_by('created_at')
        )

    def get_total_bill_amount(self):
        """Calculate total bill amount for session orders - ENHANCED"""
        session_orders = self.get_session_orders()
        total = sum(order.total_price for order in session_orders)
        return Decimal(str(total)) if total else Decimal('0.00')

    def can_be_billed(self):
        """Check if table can be billed - NEW METHOD"""
        session_orders = self.get_session_orders()
        return session_orders.exists() and session_orders.count() > 0

    def has_served_orders(self):
        """Check if table has served orders - NEW METHOD"""
        return self.orders.filter(status='served').exists()

    def get_occupied_duration(self):
        """Get current occupancy duration in minutes - ENHANCED"""
        if self.status == 'occupied' and self.last_occupied_at:
            duration = timezone.now() - self.last_occupied_at
            return int(duration.total_seconds() / 60)
        return 0
    def get_occupancy_duration(self):
        """Get current occupancy duration in minutes - ALIAS for serializer compatibility"""
        return self.get_occupied_duration()

    # Add this property for easier access
    @property
    def time_occupied(self):
        """Property for template access"""
        return self.get_occupied_duration()

class MenuCategory(models.Model):
    """Menu item categories"""
    name = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=255, blank=True, help_text='English name for compatibility')
    name_hi = models.CharField(max_length=255, blank=True, help_text='Hindi name for compatibility')
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
    
    def save(self, *args, **kwargs):
        # Auto-populate compatibility fields
        if not self.name_en and self.name:
            self.name_en = self.name
        if not self.name_hi:
            self.name_hi = self.name_en or self.name
        if not self.name and self.name_en:
            self.name = self.name_en
        super().save(*args, **kwargs)

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
    name_en = models.CharField(max_length=255, blank=True, help_text='English name for compatibility')
    name_hi = models.CharField(max_length=255, blank=True, help_text='Hindi name for compatibility') 
    description_en = models.TextField(blank=True, help_text='English description for compatibility')
    description_hi = models.TextField(blank=True, help_text='Hindi description for compatibility')
    available = models.BooleanField(default=True, help_text='Backward compatibility field')
    

    class Meta:
        db_table = 'menu_item'
        ordering = ['category__display_order', 'display_order', 'name']

    def __str__(self):
        return f"{self.name} - ₹{self.price}"
    
    def save(self, *args, **kwargs):
        # Auto-populate compatibility fields
        if not self.name_en and self.name:
            self.name_en = self.name
        if not self.name_hi:
            self.name_hi = self.name_en or self.name
        if not self.name and self.name_en:
            self.name = self.name_en
            
        if not self.description_en and self.description:
            self.description_en = self.description
        if not self.description_hi:
            self.description_hi = self.description_en or self.description
        if not self.description and self.description_en:
            self.description = self.description_en
            
        # Sync availability fields
        self.available = self.availability == 'available' and self.is_active
        
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        return self.availability == 'available' and self.is_active

    @property
    def profit_margin(self):
        if self.cost_price:
            return ((self.price - self.cost_price) / self.price) * 100
        return 0

class Order(models.Model):
    """Restaurant orders with enhanced tracking"""
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
    SOURCE_CHOICES = [
        ('dine_in', 'Dine In'),
        ('mobile', 'Mobile Order'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery')
    ]

    # Order identification
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order_number = models.CharField(max_length=50, unique=True, blank=True)

    # Order details
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Order management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='dine_in')
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

    # Admin fields
    admin_notes = models.TextField(blank=True, help_text='Admin notes for this order')
    is_kds_notified = models.BooleanField(default=False, help_text='Whether KDS was notified')
    backup_data = models.JSONField(default=dict, help_text='Backup data for offline orders')

    class Meta:
        db_table = 'restaurant_order'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Auto-generate order number
        if not self.order_number:
            self.order_number = f"ORD{timezone.now().strftime('%Y%m%d')}{Order.objects.count() + 1:04d}"

        # Auto-calculate total price
        if self.menu_item_id:  # Make sure menu_item exists
            self.unit_price = self.menu_item.price
            self.total_price = self.unit_price * self.quantity

        # Set estimated times
        if not self.estimated_preparation_time and self.menu_item_id:
            self.estimated_preparation_time = self.menu_item.preparation_time

        if self.status == 'preparing' and not self.preparation_started_at:
            self.preparation_started_at = timezone.now()
            self.estimated_ready_time = timezone.now() + timezone.timedelta(
                minutes=self.estimated_preparation_time or 15
            )
        # DEBUG LOGGING - ADD THIS
        if not self.pk:  # Only for new orders
            print(f"\n🆕 CREATING NEW ORDER:")
            print(f"   Item: {self.menu_item.name}")
            print(f"   Table: {self.table.table_number}")
            print(f"   Table Status: {self.table.status}")

            # Check if table has active session
            existing_sessions = self.table.order_sessions.filter(is_active=True)
            print(f"   Existing Active Sessions: {existing_sessions.count()}")

            if not existing_sessions.exists():
                print("   🎫 Creating NEW OrderSession...")
                try:
                    new_session = OrderSession.objects.create(
                        table=self.table,
                        created_by=self.created_by,
                        is_active=True
                    )
                    print(f"   ✅ Session Created: ID={new_session.id}")
                except Exception as e:
                    print(f"   ❌ Session Creation FAILED: {e}")
            else:
                print(f"   ✅ Using Existing Session: ID={existing_sessions.first().id}")

            # Mark table as occupied
            if self.table.status == 'free':
                print("   🏓 Marking table as OCCUPIED")
                self.table.mark_occupied()
            else:
                print(f"   🏓 Table already {self.table.status}")

        super().save(*args, **kwargs)

        if not hasattr(self, '_session_debug_done'):
            # Verify session after save
            active_sessions = self.table.order_sessions.filter(is_active=True)
            print(f"   🔍 After Save - Active Sessions: {active_sessions.count()}")
            self._session_debug_done = True

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
        """Update order status with proper tracking - FIXED"""
        from django.utils import timezone

        old_status = self.status
        self.status = new_status

        # Update timestamps and user tracking
        if new_status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
            if user:
                self.confirmed_by = user

        elif new_status == 'preparing' and not self.preparation_started_at:
            self.preparation_started_at = timezone.now()
            if user:
                self.prepared_by = user
            # Set estimated ready time
            if self.estimated_preparation_time:
                self.estimated_ready_time = timezone.now() + timezone.timedelta(
                    minutes=self.estimated_preparation_time
                )

        elif new_status == 'ready' and not self.ready_at:
            self.ready_at = timezone.now()

        elif new_status == 'served' and not self.served_at:
            self.served_at = timezone.now()
            if user:
                self.served_by = user

        self.save()

        # Broadcast status update
        try:
            from .utils import broadcast_order_update
            broadcast_order_update(self, old_status)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error broadcasting order update: {e}")

class OrderSession(models.Model):
    """Enhanced order sessions for comprehensive billing"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('completed', 'Completed')  # Added this status
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('online', 'Online'),
        ('mixed', 'Mixed Payment')
    ]

    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='order_sessions')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    # Financial details
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Payment details
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_details = models.JSONField(default=dict, help_text='Payment breakdown for mixed payments')
    apply_gst = models.BooleanField(default=True, help_text='Whether to apply GST to this session')

    # Admin and operational
    notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True, help_text='Admin notes for billing')
    receipt_number = models.CharField(max_length=50, blank=True)
    printed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    billed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions_billed')

    class Meta:
        db_table = 'restaurant_order_session'
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.receipt_number or self.session_id} - Table {self.table.table_number}"

    def get_session_orders(self):
        """Get all orders in this session timeframe."""
        from django.utils import timezone

        end_time = self.completed_at or timezone.now()
        return (
            self.table.orders
                .filter(
                    created_at__gte=self.created_at,
                    created_at__lte=end_time,
                    status__in=['pending', 'confirmed', 'preparing', 'ready', 'served']
                )
                .exclude(status='cancelled')
                .order_by('created_at')
        )


    def calculate_totals(self):
        """Calculate session totals with GST - ENHANCED"""
        from decimal import Decimal

        orders = self.get_session_orders()
        subtotal = sum(order.total_price for order in orders)

        # Apply percentage discount first
        if self.discount_percentage > 0:
            percentage_discount = subtotal * (self.discount_percentage / 100)
            self.discount_amount = max(self.discount_amount, percentage_discount)

        # Calculate taxable amount
        taxable_amount = subtotal - self.discount_amount

        # Calculate GST (18% for restaurants in India)
        if getattr(self, 'apply_gst', True):  # Default to True for backward compatibility
            gst_rate = Decimal('0.05')  # 18%
            self.tax_amount = taxable_amount * gst_rate
        else:
            self.tax_amount = Decimal('0.00')  # No GST

        # Calculate final amount
        self.subtotal_amount = subtotal
        self.final_amount = taxable_amount + self.tax_amount + self.service_charge

        # Generate receipt number if not exists
        if not self.receipt_number:
            self.receipt_number = f"RCP-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        self.save()
        return self.final_amount

    def complete_session(self, billed_by=None):
        """Complete the billing session - FIXED"""
        from django.utils import timezone

        if not self.receipt_number:
            self.receipt_number = f"RCP-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        self.is_active = False
        self.completed_at = timezone.now()
        self.payment_status = 'completed'

        if billed_by:
            self.billed_by = billed_by

        self.save()

        try:
            from apps.bills.models import Bill, BillItem

            # Create Bill record
            bill = Bill.objects.create(
                receipt_number=self.receipt_number,
                customer_name=self.notes or 'Guest',
                customer_phone='',  # You can add phone field to OrderSession if needed
                bill_type='restaurant',
                total_amount=self.final_amount,
                payment_method=self.payment_method or 'cash',
                user=billed_by or self.created_by
            )

            # Create BillItems from session orders
            orders = self.get_session_orders()
            for order in orders:
                BillItem.objects.create(
                    bill=bill,
                    item_name=f"{order.menu_item.name} (Table {self.table.table_number})",
                    quantity=order.quantity,
                    price=order.unit_price
                )

            print(f"✅ Created Bill record {bill.receipt_number} for table management session")

        except Exception as e:
            print(f"❌ Error creating Bill record: {e}")
            # Don't fail the session completion if Bill creation fails

        # Mark table as free

        # Mark table as free
        self.table.mark_free()

    def print_bill(self):
        """Mark bill as printed - FIXED"""
        from django.utils import timezone
        self.printed_at = timezone.now()
        self.save()

class KitchenDisplaySettings(models.Model):
    """Enhanced settings for Kitchen Display System"""
    name = models.CharField(max_length=100, unique=True)
    audio_enabled = models.BooleanField(default=True)
    auto_refresh_interval = models.PositiveIntegerField(default=30, help_text='Refresh interval in seconds')
    display_completed_orders = models.BooleanField(default=False)
    completed_order_display_time = models.PositiveIntegerField(default=300, help_text='Time in seconds')
    priority_color_coding = models.BooleanField(default=True)
    show_preparation_time = models.BooleanField(default=True)
    show_order_notes = models.BooleanField(default=True)
    max_orders_per_screen = models.PositiveIntegerField(default=20)

    # Enhanced features
    offline_mode_enabled = models.BooleanField(default=True, help_text='Store orders when offline')
    notification_sound_volume = models.DecimalField(max_digits=3, decimal_places=2, default=0.8)
    auto_confirm_orders = models.BooleanField(default=False)
    group_orders_by_table = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kitchen_display_settings'

    def __str__(self):
        return self.name

# New model for offline order backup
class OfflineOrderBackup(models.Model):
    """Backup for orders when kitchen display is offline"""
    order_data = models.JSONField(help_text='Complete order data')
    table_number = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)

    class Meta:
        db_table = 'offline_order_backup'
        ordering = ['created_at']

# CRITICAL FIX: Enhanced Signal handlers
@receiver(post_save, sender=Order)
def handle_order_created(sender, instance, created, **kwargs):
    """FIXED: Only handle table status, not broadcasting (done in views)"""
    if created:
        # Mark table as occupied if it's the first order
        if instance.table.status == 'free':
            instance.table.mark_occupied()

        # Only create backup if KDS is offline - don't broadcast here
        try:
            from .utils import is_kds_connected, create_order_backup

            if not is_kds_connected():
                create_order_backup(instance)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in order signal handler: {e}")

@receiver(post_save, sender=OrderSession)
def handle_session_completed(sender, instance, **kwargs):
    """Handle session completion with enhanced features"""
    if not instance.is_active and instance.payment_status in ['paid', 'partial', 'completed']:
        # Additional cleanup and notifications can be added here
        try:
            from .utils import broadcast_table_update
            broadcast_table_update(instance.table, 'occupied')
        except Exception:
            pass



