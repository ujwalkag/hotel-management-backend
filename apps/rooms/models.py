from django.db import models
from apps.users.models import CustomUser
from decimal import Decimal
from django.utils import timezone

class Room(models.Model):
    aadhaar_card = models.CharField(max_length=12, blank=True, null=True)  # optional Aadhaar at room level if needed
    type_en = models.CharField(max_length=100)
    type_hi = models.CharField(max_length=100)
    description_en = models.TextField(blank=True, null=True)
    description_hi = models.TextField(blank=True, null=True)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.type_en

class RoomBooking(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    check_in = models.DateField(blank=True, null=True)  # if needed
    check_out = models.DateField(blank=True, null=True) # if needed
    aadhaar_card = models.CharField(max_length=12, blank=True, null=True)  # optional per booking
    created_at = models.DateTimeField(auto_now_add=True)

class BookingItem(models.Model):
    booking = models.ForeignKey(RoomBooking, related_name="items", on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)

