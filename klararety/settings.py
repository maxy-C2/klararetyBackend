"""
Django settings for klararety project.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

# Load environment variables before using them
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'drf_yasg',
    'rest_framework.authtoken',
    'django_nose',

    # Project apps
    'analytics',
    'audit',
    'billing',
    'communication',
    'consent',
    'healthcare',
    'pharmco',
    'telemedicine',
    'users',
    'wearables',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditLoggingMiddleware',  # Add audit logging
    'telemedicine.middleware.HIPAAComplianceMiddleware',
]

#TEST_RUNNER = 'django.test.runner.DiscoverRunner'
""" TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = [
    '--with-coverage',
    '--cover-package=users',
    '--cover-html',
] """

# HIPAA Audit Logging
# Add this right before the LOGGING configuration
log_path = os.getenv('HIPAA_AUDIT_LOG_PATH', 'logs/hipaa_audit.log')
# Strip any comments if present
if '#' in log_path:
    log_path = log_path.split('#')[0].strip()
# Convert to absolute path if it's relative
if not os.path.isabs(log_path):
    log_path = os.path.join(BASE_DIR, log_path)
# Ensure directory exists
os.makedirs(os.path.dirname(log_path), exist_ok=True)

# Then use this path in the LOGGING configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'hipaa': {
            'format': '{asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'hipaa_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_path,  # Use the resolved path
            'formatter': 'hipaa',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        },
    },
    'loggers': {
        'hipaa_audit': {
            'handlers': ['hipaa_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
log_dir = BASE_DIR / 'logs'
if not log_dir.exists():
    log_dir.mkdir(parents=True, exist_ok=True)

ROOT_URLCONF = 'klararety.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'klararety.wsgi.application'

# Database configuration
if os.getenv('DB_ENGINE') == 'django.db.backends.postgresql':
    DATABASES = {
        'default': {
            'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.getenv('DB_NAME', 'klararety_db'),
            'USER': os.getenv('DB_USER', 'klararety_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    # SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS settings - cross-origin requests
CORS_ALLOWED_ORIGINS = [
    os.getenv('REACT_HOST', 'http://localhost:3000'),  # React frontend
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Swagger settings
SWAGGER_SETTINGS = {
    'DEFAULT_INFO': 'klararety.urls.api_info',
    'DEFAULT_AUTO_SCHEMA_CLASS': 'drf_yasg.inspectors.SwaggerAutoSchema',
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
    'PERSIST_AUTH': True,
    'REFETCH_SCHEMA_WITH_AUTH': True,
    'REFETCH_SCHEMA_ON_LOGOUT': True,
    'DEFAULT_MODEL_RENDERING': 'model',
    'TAGS_SORTER': 'alpha',
    'OPERATIONS_SORTER': 'alpha',
    'DEFAULT_GENERATOR_CLASS': 'drf_yasg.generators.OpenAPISchemaGenerator',
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files and media
STATIC_URL = 'static/'
STATIC_ROOT = os.getenv('STATIC_ROOT', BASE_DIR / 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.getenv('MEDIA_ROOT', BASE_DIR / 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Zoom API Credentials
ZOOM_API_KEY = os.getenv('ZOOM_API_KEY')
ZOOM_API_SECRET = os.getenv('ZOOM_API_SECRET')

# Security settings
# For HIPAA compliance, ensure secure connections
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'

# Always enable these security settings regardless of environment
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session timeout (15 minutes of inactivity)
SESSION_COOKIE_AGE = 900  # seconds
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSP Headers
CSP_DEFAULT_SRC = ("'self'", "*.zoom.us")
CSP_SCRIPT_SRC = ("'self'", "*.zoom.us", "*.zoomdev.com")
CSP_CONNECT_SRC = ("'self'", "*.zoom.us", "*.zoomdev.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # Often needed for Zoom
CSP_IMG_SRC = ("'self'", "data:", "*.zoom.us")
CSP_FONT_SRC = ("'self'", "data:")

# Email settings
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Withings Configuration
WITHINGS_CLIENT_ID = os.getenv('WITHINGS_CLIENT_ID')
WITHINGS_CLIENT_SECRET = os.getenv('WITHINGS_CLIENT_SECRET')
WITHINGS_REDIRECT_URI = os.getenv('WITHINGS_REDIRECT_URI')

# Custom user model
AUTH_USER_MODEL = 'users.CustomUser'
