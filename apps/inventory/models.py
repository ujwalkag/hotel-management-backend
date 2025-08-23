from django.db import models
from apps.users.models import CustomUser
from decimal import Decimal
from django.utils import timezone

class InventoryCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def total_entries(self):
        return self.entries.count()

    @property
    def total_spent(self):
        return self.entries.aggregate(
            total=models.Sum('total_cost')
        )['total'] or Decimal('0.00')

    class Meta:
        db_table = 'inventory_category'
        verbose_name = 'Inventory Category'
        verbose_name_plural = 'Inventory Categories'
        ordering = ['name']

class InventoryEntry(models.Model):
    category = models.ForeignKey(
        InventoryCategory, 
        on_delete=models.CASCADE, 
        related_name='entries'
    )
    item_name = models.CharField(max_length=200)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_date = models.DateField()
    supplier_name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-calculate total cost
        self.total_cost = self.price_per_unit * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} - {self.category.name} - ₹{self.total_cost}"

    class Meta:
        db_table = 'inventory_entry'
        verbose_name = 'Inventory Entry'
        verbose_name_plural = 'Inventory Entries'
        ordering = ['-created_at']
