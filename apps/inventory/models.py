# apps/inventory/models.py
from django.db import models
from apps.users.models import CustomUser
from decimal import Decimal
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

class InventoryCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def items_count(self):
        return self.items.filter(is_active=True).count()
    
    @property
    def total_value(self):
        return sum(item.total_value for item in self.items.filter(is_active=True))

    class Meta:
        db_table = 'inventory_category'
        verbose_name = 'Inventory Category'
        verbose_name_plural = 'Inventory Categories'
        ordering = ['name']

class InventoryItem(models.Model):
    UNIT_CHOICES = (
        ('kg', 'Kilogram'),
        ('gm', 'Gram'),
        ('ltr', 'Liter'), 
        ('ml', 'Milliliter'),
        ('pcs', 'Pieces'),
        ('box', 'Box'),
        ('bottle', 'Bottle'),
        ('packet', 'Packet'),
        ('bag', 'Bag'),
        ('dozen', 'Dozen'),
    )

    category = models.ForeignKey(InventoryCategory, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True, blank=True)  # Stock Keeping Unit
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    min_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=10, validators=[MinValueValidator(0)])
    max_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=1000, validators=[MinValueValidator(0)])
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    supplier_name = models.CharField(max_length=200, blank=True)
    supplier_contact = models.CharField(max_length=15, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)  # Storage location
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.sku:
            # Auto-generate SKU if not provided
            self.sku = f"INV-{self.category.name[:3].upper()}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock_level

    @property
    def is_out_of_stock(self):
        return self.current_stock <= 0

    @property
    def is_overstocked(self):
        return self.current_stock >= self.max_stock_level

    @property
    def total_value(self):
        return self.current_stock * self.cost_per_unit

    @property
    def stock_status(self):
        if self.is_out_of_stock:
            return "Out of Stock"
        elif self.is_low_stock:
            return "Low Stock"
        elif self.is_overstocked:
            return "Overstocked"
        else:
            return "In Stock"

    @property
    def stock_status_class(self):
        """CSS class for stock status"""
        if self.is_out_of_stock:
            return "danger"
        elif self.is_low_stock:
            return "warning"
        elif self.is_overstocked:
            return "info"
        else:
            return "success"

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def is_expiring_soon(self, days=7):
        """Check if item expires within specified days"""
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return 0 <= delta.days <= days
        return False

    def __str__(self):
        return f"{self.name} ({self.current_stock} {self.unit})"

    class Meta:
        db_table = 'inventory_item'
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        ordering = ['name']

class StockMovement(models.Model):
    MOVEMENT_TYPES = (
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Stock Adjustment'),
        ('waste', 'Waste/Damage'),
        ('expired', 'Expired Items'),
        ('returned', 'Returned Items'),
    )

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    supplier_name = models.CharField(max_length=200, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=200, blank=True)  # Order number, bill number, etc.
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_cost(self):
        return self.quantity * self.cost_per_unit

    @property
    def movement_direction(self):
        """Returns + for in movements, - for out movements"""
        return "+" if self.movement_type in ['in', 'returned'] else "-"

    def save(self, *args, **kwargs):
        # Don't auto-update stock here - do it in the signal
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movement_type} - {self.item.name} - {self.quantity} {self.item.unit}"

    class Meta:
        db_table = 'inventory_stock_movement'
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        ordering = ['-created_at']

class LowStockAlert(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='alerts')
    alert_date = models.DateTimeField(auto_now_add=True)
    stock_level_at_alert = models.DecimalField(max_digits=10, decimal_places=2)
    threshold_level = models.DecimalField(max_digits=10, decimal_places=2)
    is_resolved = models.BooleanField(default=False)
    resolved_date = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    @property
    def days_since_alert(self):
        delta = timezone.now() - self.alert_date
        return delta.days

    def resolve_alert(self, user=None, notes=""):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_date = timezone.now()
        self.resolved_by = user
        self.notes = notes
        self.save()

    def __str__(self):
        status = "Resolved" if self.is_resolved else "Active"
        return f"{self.item.name} - Low Stock Alert ({status})"

    class Meta:
        db_table = 'inventory_low_stock_alert'
        verbose_name = 'Low Stock Alert'
        verbose_name_plural = 'Low Stock Alerts'
        ordering = ['-alert_date']

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    payment_terms = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_purchase_amount(self):
        """Total amount purchased from this supplier"""
        movements = StockMovement.objects.filter(
            supplier_name=self.name,
            movement_type='in'
        )
        return sum(movement.total_cost for movement in movements)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'inventory_supplier'
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['name']

class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed'),
        ('partial', 'Partially Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    order_number = models.CharField(max_length=50, unique=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"PO-{timezone.now().strftime('%Y%m%d')}-{timezone.now().microsecond}"
        super().save(*args, **kwargs)

    def calculate_total(self):
        total = sum(item.total_amount for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

    def __str__(self):
        return f"{self.order_number} - {self.supplier.name}"

    class Meta:
        db_table = 'inventory_purchase_order'
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-created_at']

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity_ordered = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    @property
    def total_amount(self):
        return self.quantity_ordered * self.unit_price
    
    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity_ordered
    
    @property
    def pending_quantity(self):
        return self.quantity_ordered - self.quantity_received

    def __str__(self):
        return f"{self.purchase_order.order_number} - {self.item.name}"

    class Meta:
        db_table = 'inventory_purchase_order_item'
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

# Signals for automatic stock updates and alerts
@receiver(post_save, sender=StockMovement)
def update_stock_on_movement(sender, instance, created, **kwargs):
    """Update item stock when stock movement is created"""
    if created:
        item = instance.item
        
        if instance.movement_type in ['in', 'returned']:
            item.current_stock += instance.quantity
        else:  # out, adjustment, waste, expired
            item.current_stock -= instance.quantity
        
        # Ensure stock doesn't go negative
        if item.current_stock < 0:
            item.current_stock = 0
            
        item.save(update_fields=['current_stock'])
        
        # Check for low stock alert
        if item.is_low_stock and not item.alerts.filter(is_resolved=False).exists():
            LowStockAlert.objects.create(
                item=item,
                stock_level_at_alert=item.current_stock,
                threshold_level=item.min_stock_level
            )
