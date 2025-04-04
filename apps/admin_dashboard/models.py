from django.db import models
from apps.bookings.models import Order, MenuItem

class SalesSummary(models.Model):
    date = models.DateField(auto_now_add=True)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    completed_orders = models.IntegerField(default=0)
    failed_orders = models.IntegerField(default=0)

    def __str__(self):
        return f"Sales Summary for {self.date}"


class BestSellingItem(models.Model):
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    sales_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.item.name} - {self.sales_count} Sold"

