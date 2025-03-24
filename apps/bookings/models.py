from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    availability = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class RoomService(models.Model):
    service_name = models.CharField(max_length=100)
    service_price = models.DecimalField(max_digits=10, decimal_places=2)
    room_type = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.service_name


class Order(models.Model):
    ORDER_TYPE_CHOICES = (
        ('restaurant', 'Restaurant'),
        ('room', 'Room Service'),
    )
    STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    items = models.ManyToManyField(MenuItem, blank=True)
    room_service = models.ManyToManyField(RoomService, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_total_price(self):
        item_total = sum(item.price for item in self.items.all())
        service_total = sum(service.service_price for service in self.room_service.all())
        self.total_price = item_total + service_total
        self.save()

    def __str__(self):
        return f"Order #{self.id} - {self.order_type}"

