from django.db import models

class MenuItem(models.Model):
    CATEGORY_CHOICES = (
        ("main", "Main Course"),
        ("snack", "Snack"),
        ("beverage", "Beverage"),
    )

    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    def __str__(self):
        return self.name

