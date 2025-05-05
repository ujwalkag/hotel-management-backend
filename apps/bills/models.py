# apps/bills/models.py

from django.db import models
from apps.menu.models import MenuItem
from apps.bookings.models import Room
from django.contrib.auth import get_user_model

User = get_user_model()

class Bill(models.Model):
    BILL_TYPES = [
        ('restaurant', 'Restaurant'),
        ('room', 'Room'),
    ]

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    bill_type = models.CharField(max_length=20, choices=BILL_TYPES)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bill_type.capitalize()} Bill #{self.id} - ₹{self.total_amount}"
    

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, related_name="items", on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.item.name if self.item else 'Unknown'}"

