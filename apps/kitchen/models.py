# apps/kitchen/models.py - FIXED VERSION
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.bills.models import Bill
from apps.tables.models import RestaurantTable  # FIXED: Import RestaurantTable, not Table
from django.utils import timezone

class KitchenOrder(models.Model):
    """Kitchen orders from restaurant bills"""
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
    table = models.ForeignKey(RestaurantTable, on_delete=models.SET_NULL, null=True, blank=True)  # FIXED: RestaurantTable
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    estimated_time = models.IntegerField(default=30, help_text="Estimated time in minutes")
    actual_prep_time = models.IntegerField(null=True, blank=True)
    
    # Kitchen staff
    assigned_chef = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    
    # Special instructions
    special_instructions = models.TextField(blank=True)
    kitchen_notes = models.TextField(blank=True)
    
    # Audio alerts
    audio_played = models.BooleanField(default=False)
    audio_acknowledged = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kitchen_orders'
        ordering = ['priority', 'received_at']

    def __str__(self):
        table_info = "Takeaway"
        if self.table:
            table_info = f"Table {self.table.table_number}"
        elif 'Table' in self.bill.customer_name:
            table_info = self.bill.customer_name.split(' - ')[0]
        return f"{self.bill.receipt_number} - {table_info} - {self.get_status_display()}"

    @property
    def table_number(self):
        """Get table number for kitchen display"""
        if self.table:
            return self.table.table_number
        elif 'Table' in self.bill.customer_name:
            return self.bill.customer_name.split('Table ')[1].split(' -')[0]
        return "Takeaway"

    def start_preparation(self, chef_name=''):
        if self.status == 'received':
            self.status = 'preparing'
            self.started_at = timezone.now()
            self.assigned_chef = chef_name
            self.audio_acknowledged = True
            self.save()

    def mark_ready(self):
        if self.status == 'preparing':
            self.status = 'ready'
            self.ready_at = timezone.now()
            
            if self.started_at:
                prep_time = (self.ready_at - self.started_at).total_seconds() / 60
                self.actual_prep_time = int(prep_time)
            
            self.save()

    def mark_served(self):
        """Mark order as served and make table available"""
        if self.status == 'ready':
            self.status = 'served'
            self.served_at = timezone.now()
            
            # Mark table as available when order is served
            if self.table:
                self.table.release_table()
                
            self.save()

class AudioAlert(models.Model):
    """Kitchen audio alert settings"""
    ALERT_TYPES = [
        ('new_order', 'New Order'),
        ('order_ready', 'Order Ready'),
        ('priority_order', 'Priority Order'),
    ]

    name = models.CharField(max_length=100)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    audio_file = models.FileField(upload_to='kitchen_audio/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    volume = models.IntegerField(default=80, validators=[MinValueValidator(0), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'kitchen_audio_alerts'

    def __str__(self):
        return f"{self.name} - {self.get_alert_type_display()}"
