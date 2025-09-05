from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.bills.models import Bill, BillItem
from apps.tables.models import Table
from django.utils import timezone

class KitchenOrder(models.Model):
    """Kitchen order management"""
    STATUS_CHOICES = [
        ('received', 'Order Received'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready to Serve'),
        ('served', 'Served'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Normal'),
        (3, 'High'),
        (4, 'Urgent'),
    ]

    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name='kitchen_order')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    estimated_time = models.IntegerField(help_text="Estimated preparation time in minutes", default=30)
    actual_prep_time = models.IntegerField(null=True, blank=True)
    
    # Kitchen staff assignment
    assigned_chef = models.CharField(max_length=100, blank=True)
    
    # Timing information
    received_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    kitchen_notes = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Audio alert settings
    audio_played = models.BooleanField(default=False)
    audio_acknowledged = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kitchen_orders'
        verbose_name = 'Kitchen Order'
        verbose_name_plural = 'Kitchen Orders'
        ordering = ['priority', 'received_at']

    def __str__(self):
        return f"Kitchen Order {self.bill.receipt_number} - {self.get_status_display()}"

    def start_preparation(self):
        """Mark order as being prepared"""
        if self.status == 'received':
            self.status = 'preparing'
            self.started_at = timezone.now()
            self.save()

    def mark_ready(self):
        """Mark order as ready to serve"""
        if self.status == 'preparing':
            self.status = 'ready'
            self.completed_at = timezone.now()
            
            # Calculate actual prep time
            if self.started_at:
                prep_time = (self.completed_at - self.started_at).total_seconds() / 60
                self.actual_prep_time = int(prep_time)
            
            self.save()

    def mark_served(self):
        """Mark order as served"""
        if self.status == 'ready':
            self.status = 'served'
            self.served_at = timezone.now()
            self.save()

class KitchenItemStatus(models.Model):
    """Track individual item preparation status"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    ]

    kitchen_order = models.ForeignKey(KitchenOrder, on_delete=models.CASCADE, related_name='item_status')
    bill_item = models.OneToOneField(BillItem, on_delete=models.CASCADE, related_name='kitchen_status')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    preparation_notes = models.TextField(blank=True)
    estimated_time = models.IntegerField(default=15, help_text="Time in minutes")
    actual_time = models.IntegerField(null=True, blank=True, help_text="Actual time in minutes")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kitchen_item_status'
        verbose_name = 'Kitchen Item Status'
        verbose_name_plural = 'Kitchen Item Status'

    def __str__(self):
        return f"{self.bill_item.item_name} - {self.get_status_display()}"

    def start_preparation(self):
        """Start preparing this item"""
        self.status = 'preparing'
        self.started_at = timezone.now()
        self.save()

    def mark_ready(self):
        """Mark this item as ready"""
        self.status = 'ready'
        self.completed_at = timezone.now()
        
        if self.started_at:
            prep_time = (self.completed_at - self.started_at).total_seconds() / 60
            self.actual_time = int(prep_time)
        
        self.save()
        
        # Check if all items in the order are ready
        kitchen_order = self.kitchen_order
        all_items_ready = all(
            item.status == 'ready' 
            for item in kitchen_order.item_status.all()
        )
        
        if all_items_ready and kitchen_order.status == 'preparing':
            kitchen_order.mark_ready()

class AudioAlert(models.Model):
    """Audio alert configurations for kitchen notifications"""
    ALERT_TYPE_CHOICES = [
        ('new_order', 'New Order Alert'),
        ('priority_order', 'Priority Order Alert'),
        ('order_ready', 'Order Ready Alert'),
        ('kitchen_timer', 'Kitchen Timer Alert'),
    ]

    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    audio_file = models.FileField(upload_to='kitchen_audio/', null=True, blank=True)
    text_to_speech = models.TextField(blank=True, help_text="Text to be converted to speech")
    volume = models.IntegerField(default=80, validators=[MinValueValidator(0), MaxValueValidator(100)])
    repeat_count = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    repeat_interval = models.IntegerField(default=5, help_text="Seconds between repeats")
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1, help_text="Higher number = higher priority")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kitchen_audio_alerts'
        verbose_name = 'Audio Alert'
        verbose_name_plural = 'Audio Alerts'
        ordering = ['-priority', 'alert_type']

    def __str__(self):
        return f"{self.name} ({self.get_alert_type_display()})"
