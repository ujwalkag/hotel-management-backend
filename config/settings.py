import os
from pathlib import Path
from datetime import timedelta

# Define BASE_DIR correctly
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "lcik4moxnx@g+n!3r5sr0!=u47zjwbz7#)=2#db1g#g%fl3myz"
ALLOWED_HOSTS = [
    'hotelrshammad.co.in',
    'www.hotelrshammad.co.in',
    '144.24.127.172',
    '127.0.0.1',
    'localhost',
]
CSRF_TRUSTED_ORIGINS = [
    'https://hotelrshammad.co.in',
    'https://www.hotelrshammad.co.in',
    'http://127.0.0.1',
    'http://localhost',
]


INSTALLED_APPS = [
    'django_extensions',
    'drf_yasg',
    'rest_framework',  # Add this line
    'rest_framework_simplejwt',  # Add this line
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Our applications
    'apps.authentication',
    'apps.menu',
    'apps.bookings',
    'apps.notifications',
    'apps.payments',
    'apps.bills',
    'apps.admin_dashboard',
]
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/home/ubuntu/hotel-management-backend/logs/debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}


ROOT_URLCONF = 'config.urls'
DEBUG = True
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'apps.utils.renderers.PrettyJSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DEFAULT_FORMAT_SUFFIXES': {
        'json': 'json',
    },
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'hotel_db',  # Change this if you use a different database name
        'USER': 'hotel_admin',  # Your PostgreSQL username
        'PASSWORD': 'new_secure_ujjaval',  # Your PostgreSQL password
        'HOST': 'localhost',  # or your database server IP
        'PORT': '5432',
    }
}
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),  # Global static folder
    os.path.join(BASE_DIR, 'styles'),  # If styles contains CSS
]

# Automatically collect static files from all apps
for app in os.listdir(os.path.join(BASE_DIR, "apps")):
    app_static_path = os.path.join(BASE_DIR, "apps", app, "static")
    if os.path.exists(app_static_path):
        STATICFILES_DIRS.append(app_static_path)

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}
