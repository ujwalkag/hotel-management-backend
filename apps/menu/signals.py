# apps/menu/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=MenuItem)
def sync_menu_item(sender, instance, **kwargs):
    """Auto-sync menu items between apps"""
    from apps.restaurant.models import MenuItem as RestaurantMenuItem
    
    restaurant_item, created = RestaurantMenuItem.objects.get_or_create(
        name=instance.name_en,
        defaults={
            'description': instance.description_en or instance.description_hi,
            'price': instance.price,
            'is_active': instance.is_active,
        }
    )
    if not created:
        restaurant_item.price = instance.price
        restaurant_item.description = instance.description_en or instance.description_hi
        restaurant_item.is_active = instance.is_active
        restaurant_item.save()
