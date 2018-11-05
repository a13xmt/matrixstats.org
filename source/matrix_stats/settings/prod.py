from .base import *

DEBUG = False

EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
CELERY_EMAIL_TASK_CONFIG = {
    'queue' : 'sync',
    'rate_limit' : '20/m'
}

ALLOWED_HOSTS += [
    'matrixstats.org'
]
