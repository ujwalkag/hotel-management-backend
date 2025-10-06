# apps/menu/management/commands/sync_menu_models.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Copy data from apps.menu.MenuItem to apps.restaurant.MenuItem
        from apps.menu.models import MenuItem as MenuMenuItem
        from apps.restaurant.models import MenuItem as RestaurantMenuItem
        
        for menu_item in MenuMenuItem.objects.all():
            restaurant_item, created = RestaurantMenuItem.objects.get_or_create(
                name=menu_item.name_en,  # Use English name as primary
                defaults={
                    'description': menu_item.description_en or menu_item.description_hi,
                    'price': menu_item.price,
                    'category': self.get_or_create_category(menu_item.category),
                    'is_active': menu_item.is_active,
                    'availability': 'available' if menu_item.available else 'out_of_stock'
                }
            )
            if not created:
                # Update existing
                restaurant_item.price = menu_item.price
                restaurant_item.description = menu_item.description_en or menu_item.description_hi
                restaurant_item.save()
