# apps/rooms/models.py
from django.db import models

class Room(models.Model):
    type_en = models.CharField(max_length=100)
    type_hi = models.CharField(max_length=100)
    description_en = models.TextField(blank=True, null=True)
    description_hi = models.TextField(blank=True, null=True)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.type_en  # fallback to English for admin display

