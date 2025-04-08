from django.apps import AppConfig

class AdminDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.admin_dashboard'

    def ready(self):
        import apps.admin_dashboard.signals  # register signals

