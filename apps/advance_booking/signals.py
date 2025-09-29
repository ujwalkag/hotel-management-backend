from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AdvanceBooking, BookingStatusHistory

@receiver(post_save, sender=AdvanceBooking)
def log_booking_creation(sender, instance, created, **kwargs):
    """Log when a new booking is created"""
    if created:
        BookingStatusHistory.objects.create(
            booking=instance,
            old_status='',
            new_status=instance.status,
            changed_by=instance.created_by,
            reason='Initial booking creation'
        )
