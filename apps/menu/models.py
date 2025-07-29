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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name_en

