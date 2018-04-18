from __future__ import absolute_import, unicode_literals
import os
import celery
import raven
from raven.contrib.celery import register_signal, register_logger_signal


RAVEN_DSN = os.environ.get('RAVEN_DSN')
# Separate logs by enviroments (dev/prod)
RAVEN_ENVIRONMENT = os.environ.get('DJANGO_SETTINGS_MODULE').split('.')[-1]

CELERY_BROKER = None
REDIS_SOCKET = os.environ.get('REDIS_SOCKET')
if REDIS_SOCKET:
    CELERY_BROKER = 'redis+socket://%s?db=4' % REDIS_SOCKET
else:
    CELERY_BROKER = 'redis://%s:%s/4' % (
        os.environ.get('REDIS_HOST'),
        os.environ.get('REDIS_PORT'),
    )
print("Broker: ", CELERY_BROKER)

class Celery(celery.Celery):
    def on_configure(self):
        client = raven.Client(
            dsn=RAVEN_DSN,
            environment=RAVEN_ENVIRONMENT
        )
        register_logger_signal(client)
        register_signal(client)

app = Celery(
    app='matrix_stats',
    broker=CELERY_BROKER
)

app.conf.ONCE = {
  'backend': 'celery_once.backends.Redis',
  'settings': {
    'url': CELERY_BROKER,
    'default_timeout': 60 * 60
  }
}

app.conf.beat_schedule = {
}

app.autodiscover_tasks(['matrix_bot.tasks'])

