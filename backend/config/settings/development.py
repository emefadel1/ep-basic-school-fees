# config/settings/development.py

"""
Development settings - DO NOT USE IN PRODUCTION
"""

from .base import *

# Debug mode
DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Installed apps - add debug toolbar
INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

# Middleware - add debug toolbar
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

# Debug Toolbar
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Use SQLite for quick development (optional)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Email - console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable caching in development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# More permissive CORS for development
CORS_ALLOW_ALL_ORIGINS = True

# Logging - more verbose
LOGGING['root']['level'] = 'DEBUG'