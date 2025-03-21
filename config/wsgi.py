import os
import sys
import django
from django.core.wsgi import get_wsgi_application

print("==> WSGI loading...")  # Track startup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    django.setup()
    print("==> Django setup complete!")  # Confirm setup
    application = get_wsgi_application()
    print("==> WSGI application loaded successfully!")  # Confirm app load
except Exception as e:
    print(f"WSGI error: {e}")  # Print any error that happens
    raise

