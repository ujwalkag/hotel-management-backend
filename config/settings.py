import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Secret Key and Debug
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'unsafe-default-secret')
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# Allowed Hosts
ALLOWED_HOSTS = [
    'hotelrshammad.co.in',
    'www.hotelrshammad.co.in',
    '144.24.127.172',
    '127.0.0.1',
    'localhost',
]

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    'https://hotelrshammad.co.in',
    'https://www.hotelrshammad.co.in',
    'http://127.0.0.1',
    'http://localhost',
]

# Installed Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    
    'apps.users',
    'apps.menu',
    'apps.rooms',
    'apps.bills',
    'apps.notifications',
    'apps.tables',
    'apps.staff',
]

# Middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URL Configuration
ROOT_URLCONF = 'config.urls'

# Templates
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

# WSGI Application
WSGI_APPLICATION = 'config.wsgi.application'

# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'hotel_db'),
        'USER': os.getenv('POSTGRES_USER', 'hotel_admin'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'new_secure_ujjaval'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Password Validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'styles'),
]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Automatically collect static from app/static
for app in os.listdir(os.path.join(BASE_DIR, "apps")):
    app_static_path = os.path.join(BASE_DIR, "apps", app, "static")
    if os.path.exists(app_static_path):
        STATICFILES_DIRS.append(app_static_path)

# Default Auto Field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "https://hotelrshammad.co.in",
    "https://www.hotelrshammad.co.in",
    "http://127.0.0.1:3000",  # local frontend dev if needed
    "http://localhost:3000",
]

CORS_ALLOW_CREDENTIALS = True

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.users.authentication.CustomJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'SIGNING_KEY': SECRET_KEY,
}

# Oracle Cloud Storage (for backup/upload)
ORACLE_STORAGE_REGION = os.getenv('ORACLE_STORAGE_REGION')
ORACLE_STORAGE_NAMESPACE = os.getenv('ORACLE_STORAGE_NAMESPACE')
ORACLE_BUCKET_NAME = os.getenv('ORACLE_BUCKET_NAME')
ORACLE_ACCESS_KEY = os.getenv('ORACLE_ACCESS_KEY')
ORACLE_SECRET_KEY = os.getenv('ORACLE_SECRET_KEY')

AUTH_USER_MODEL = 'users.CustomUser'
