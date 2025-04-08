from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.bookings.models import Order
from apps.admin_dashboard.models import SalesSummary, BestSellingItem
from django.utils.timezone import now

@receiver(post_save, sender=Order)
def update_sales_and_best_sellers(sender, instance, created, **kwargs):
    if instance.status != 'completed':
        return

    today = now().date()

    # Update or create SalesSummary
    summary, _ = SalesSummary.objects.get_or_create(date=today)
    summary.total_sales += instance.total_amount
    summary.completed_orders += 1
    summary.save()

    # Update best-selling items count
    for item in instance.items.all():
        best_seller, _ = BestSellingItem.objects.get_or_create(item=item)
        best_seller.sales_count += 1
        best_seller.save()

