from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Environment-based configuration
DJANGO_ENV = os.getenv('DJANGO_ENV', 'development')
DEBUG = os.getenv("DEBUG", "False") == "True"

SECRET_KEY = 'de&sje#k$5g*+u3q&s)w5xu*m0h__l)98c4lf1)1j(=qswj7aj'

# Allowed hosts
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Together.ai API Key
TOGETHER_API_KEY = os.getenv('TOGETHER_API_KEY', 'tgp_v1_dStKLklKWfd-fP-MIhyjw58CcjZLSoG74xgGZ2wfoQg')

# Elasticsearch Configuration
ELASTICSEARCH_CONFIG = {
    'HOST': os.getenv('ELASTICSEARCH_HOST', 'localhost:9200'),
    'API_KEY': os.getenv('ELASTICSEARCH_API_KEY', ''),
    'USE_SSL': os.getenv('ELASTICSEARCH_SSL', 'false').lower() == 'true',
    'CLOUD_ID': os.getenv('ELASTICSEARCH_CLOUD_ID', ''),
}

# Auto-detect cloud vs local
IS_CLOUD_ES = (
    'cloud.es.io' in ELASTICSEARCH_CONFIG['HOST'] or
    ELASTICSEARCH_CONFIG['API_KEY'] or
    ELASTICSEARCH_CONFIG['CLOUD_ID']
)

print(f"🔧 Environment: {DJANGO_ENV}")
print(f"🔍 Elasticsearch: {'Cloud' if IS_CLOUD_ES else 'Local'} ({ELASTICSEARCH_CONFIG['HOST']})")
print(f"🤖 Together.ai: {'Enabled' if TOGETHER_API_KEY else 'Disabled'}")

INSTALLED_APPS = [
    'app',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'log_manager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'app' / 'templates'],
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

WSGI_APPLICATION = 'log_manager.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

ELASTICSEARCH_HOST = "https://3361399602e4406eb9fc6c6308f32ac8.us-central1.gcp.cloud.es.io"
ELASTICSEARCH_PORT = 443
ELASTICSEARCH_USERNAME = os.getenv('ELASTICSEARCH_USERNAME', 'elastic')
ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD', 'cWUYYw6EOEGYORUksdl85Jlq')
ELASTICSEARCH_URL = os.getenv(
    'ELASTICSEARCH_URL',
    f"https://{ELASTICSEARCH_USERNAME}:{ELASTICSEARCH_PASSWORD}@3361399602e4406eb9fc6c6308f32ac8.us-central1.gcp.cloud.es.io"
)

# Email Configuration for Gmail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'balaaditya.0808@gmail.com'
EMAIL_HOST_PASSWORD = 'qnsm curh fozh zepz'  # Your app password
DEFAULT_FROM_EMAIL = 'balaaditya.0808@gmail.com'

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'app' / 'static']
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Enhanced logging for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'services.elasticsearch_service': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'app.views': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

