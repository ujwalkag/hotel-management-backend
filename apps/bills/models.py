from django.db import models
from apps.users.models import CustomUser
from apps.rooms.models import Room
from hashlib import md5
from datetime import datetime


class Bill(models.Model):
    BILL_TYPE_CHOICES = (
        ('restaurant', 'Restaurant'),
        ('room', 'Room'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('online', 'Online'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    bill_type = models.CharField(max_length=20, choices=BILL_TYPE_CHOICES)
    receipt_number = models.CharField(max_length=64, unique=True, blank=True, null=True)
    customer_name = models.CharField(max_length=255, default="Guest")
    customer_phone = models.CharField(max_length=20, default="N/A")
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ✅ New field added for payment method
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )

    def __str__(self):
        return f"{self.receipt_number or 'UNSET'} - {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            now = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            hash_part = md5(f"{self.customer_name}{self.customer_phone}{now}".encode()).hexdigest()[:6].upper()
            self.receipt_number = f"RCPT-{now}-{hash_part}"
        super().save(*args, **kwargs)


class BillItem(models.Model):
    bill = models.ForeignKey(Bill, related_name='items', on_delete=models.CASCADE)
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"

