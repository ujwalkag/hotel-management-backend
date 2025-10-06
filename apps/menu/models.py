from django.db import models

class MenuCategory(models.Model):
    name_en = models.CharField(max_length=255)
    name_hi = models.CharField(max_length=255)

    def __str__(self):
        return self.name_en
    
class MenuItem(models.Model):
    name_en = models.CharField(max_length=255)
    name_hi = models.CharField(max_length=255)
    description_en = models.TextField(blank=True, null=True)
    description_hi = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    category = models.ForeignKey(MenuCategory, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    
    # Add these fields for soft delete
    is_active = models.BooleanField(default=True, help_text="Item is available for ordering")
    is_discontinued = models.BooleanField(default=False, help_text="Item is permanently discontinued")
    discontinued_at = models.DateTimeField(null=True, blank=True)
    discontinue_reason = models.TextField(blank=True, help_text="Reason for discontinuation")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name_en
    
    class Meta:
        db_table = 'menu_menuitem'
    
    def soft_delete(self, reason=""):
        """Mark item as discontinued instead of deleting"""
        from django.utils import timezone
        self.is_active = False
        self.is_discontinued = True
        self.discontinued_at = timezone.now()
        self.discontinue_reason = reason
        self.save()
    
    def can_be_hard_deleted(self):
        """Check if item can be safely deleted"""
        # Check if item is referenced in any orders
        from apps.restaurant.models import Order  # Adjust import as needed
        return not Order.objects.filter(menu_item=self).exists()

