from django.contrib import admin
from .models import MenuItem, RoomService, Order, Category

admin.site.register(MenuItem)
admin.site.register(RoomService)
admin.site.register(Order)
admin.site.register(Category)

