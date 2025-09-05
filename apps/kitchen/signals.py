from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.bills.models import Bill
from .models import KitchenOrder, KitchenItemStatus

@receiver(post_save, sender=Bill)
def create_kitchen_order(sender, instance, created, **kwargs):
    """Automatically create kitchen order when restaurant bill is created"""
    if created and instance.bill_type == 'restaurant':
        # Create kitchen order
        kitchen_order = KitchenOrder.objects.create(
            bill=instance,
            status='received',
            special_instructions=getattr(instance, 'notes', '')
        )
        
        # Create kitchen item status for each bill item
        for bill_item in instance.items.all():
            KitchenItemStatus.objects.create(
                kitchen_order=kitchen_order,
                bill_item=bill_item,
                status='pending'
            )
        
        # Trigger audio alert (you could add WebSocket here)
        print(f"🍳 NEW KITCHEN ORDER: {instance.receipt_number}")
