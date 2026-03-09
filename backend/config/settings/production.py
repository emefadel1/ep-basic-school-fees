from .base import *

DEBUG = False

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=True)

CORS_ALLOW_ALL_ORIGINS = False

MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING['root']['level'] = env('DJANGO_LOG_LEVEL', default='INFO')
LOGGING['loggers']['django']['level'] = env('DJANGO_LOG_LEVEL', default='INFO')
LOGGING['loggers']['apps']['level'] = env('APP_LOG_LEVEL', default='INFO')
LOGGING['handlers']['file']['filename'] = BASE_DIR / 'logs' / 'django.log'
