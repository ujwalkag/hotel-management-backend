from django.apps import AppConfig

class AdvanceBookingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.advance_booking'
    verbose_name = 'Advance Booking Management'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.advance_booking.signals

