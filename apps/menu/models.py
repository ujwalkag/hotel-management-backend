from django.db import models

class MenuCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class MenuItem(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_veg = models.BooleanField(default=True)
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='items')
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.name

