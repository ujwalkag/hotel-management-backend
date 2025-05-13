from django.db import models
from apps.users.models import CustomUser
from apps.menu.models import MenuItem
from apps.rooms.models import RoomService

class Bill(models.Model):
    BILL_TYPE_CHOICES = (
        ('restaurant', 'Restaurant'),
        ('room', 'Room'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    bill_type = models.CharField(max_length=20, choices=BILL_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.bill_type} bill by {self.user.email} at {self.created_at}"

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, related_name='items', on_delete=models.CASCADE)
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"

