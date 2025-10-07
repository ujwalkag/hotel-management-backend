# File: apps/restaurant/management/commands/sync_menu_data.py
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.restaurant.models import MenuCategory as RestaurantMenuCategory, MenuItem as RestaurantMenuItem

class Command(BaseCommand):
    help = 'Sync data from menu app to restaurant app'
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be synced without actually doing it')
        parser.add_argument('--force', action='store_true', help='Force sync even if data already exists')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write("🔄 Starting menu data synchronization...")
        
        try:
            # Try to import menu models
            from apps.menu.models import MenuCategory as MenuMenuCategory, MenuItem as MenuMenuItem
            
            with transaction.atomic():
                # Sync categories
                menu_categories = MenuMenuCategory.objects.all()
                self.stdout.write(f"📋 Found {menu_categories.count()} categories in menu app")
                
                category_mapping = {}
                categories_created = 0
                categories_updated = 0
                
                for menu_cat in menu_categories:
                    if dry_run:
                        self.stdout.write(f"  Would sync category: {menu_cat.name_en}")
                        continue
                    
                    # Check if category exists
                    existing_cat = RestaurantMenuCategory.objects.filter(
                        name=menu_cat.name_en
                    ).first()
                    
                    if existing_cat and not force:
                        # Update existing category
                        existing_cat.name_en = menu_cat.name_en
                        existing_cat.name_hi = menu_cat.name_hi
                        existing_cat.save()
                        category_mapping[menu_cat.id] = existing_cat
                        categories_updated += 1
                        self.stdout.write(f"  ✅ Updated category: {existing_cat.name}")
                    else:
                        # Create new category
                        new_cat = RestaurantMenuCategory.objects.create(
                            name=menu_cat.name_en,
                            name_en=menu_cat.name_en,
                            name_hi=menu_cat.name_hi,
                            description=f'Synced from menu app',
                            is_active=True,
                            display_order=RestaurantMenuCategory.objects.count()
                        )
                        category_mapping[menu_cat.id] = new_cat
                        categories_created += 1
                        self.stdout.write(f"  ✅ Created category: {new_cat.name}")
                
                # Sync menu items
                menu_items = MenuMenuItem.objects.all()
                self.stdout.write(f"📦 Found {menu_items.count()} items in menu app")
                
                items_created = 0
                items_updated = 0
                
                for menu_item in menu_items:
                    if dry_run:
                        self.stdout.write(f"  Would sync item: {menu_item.name_en}")
                        continue
                    
                    # Map category
                    category = category_mapping.get(menu_item.category.id) if menu_item.category else None
                    
                    # Check if item exists
                    existing_item = RestaurantMenuItem.objects.filter(
                        name=menu_item.name_en,
                        category=category
                    ).first()
                    
                    if existing_item and not force:
                        # Update existing item
                        existing_item.name_en = menu_item.name_en
                        existing_item.name_hi = menu_item.name_hi
                        existing_item.description_en = menu_item.description_en or ''
                        existing_item.description_hi = menu_item.description_hi or ''
                        existing_item.price = menu_item.price
                        existing_item.available = menu_item.available
                        existing_item.availability = 'available' if menu_item.available else 'out_of_stock'
                        existing_item.is_active = menu_item.available
                        if menu_item.image:
                            existing_item.image = menu_item.image
                        existing_item.save()
                        items_updated += 1
                        self.stdout.write(f"  ✅ Updated item: {existing_item.name}")
                    else:
                        # Create new item
                        new_item = RestaurantMenuItem.objects.create(
                            name=menu_item.name_en,
                            name_en=menu_item.name_en,
                            name_hi=menu_item.name_hi,
                            description=menu_item.description_en or '',
                            description_en=menu_item.description_en or '',
                            description_hi=menu_item.description_hi or '',
                            category=category,
                            price=menu_item.price,
                            available=menu_item.available,
                            availability='available' if menu_item.available else 'out_of_stock',
                            is_active=menu_item.available,
                            image=menu_item.image,
                            preparation_time=15,
                            is_veg=True,
                            display_order=RestaurantMenuItem.objects.count()
                        )
                        items_created += 1
                        self.stdout.write(f"  ✅ Created item: {new_item.name}")
                
                if not dry_run:
                    self.stdout.write(f"\n🎉 Sync completed successfully!")
                    self.stdout.write(f"Categories: {categories_created} created, {categories_updated} updated")
                    self.stdout.write(f"Items: {items_created} created, {items_updated} updated")
                else:
                    self.stdout.write(f"\n📊 Dry run completed - no changes made")
                    
        except ImportError:
            self.stdout.write("❌ Menu app not available - nothing to sync")
        except Exception as e:
            self.stdout.write(f"❌ Sync failed: {e}")
            raise

