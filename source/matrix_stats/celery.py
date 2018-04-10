from __future__ import absolute_import, unicode_literals
import os

import celery
import raven
from raven.contrib.celery import register_signal, register_logger_signal

RAVEN_DSN = os.environ.get('RAVEN_DSN')
# Separate logs by enviroments (dev/prod)
RELEASE_NAME = os.environ.get('DJANGO_SETTINGS_MODULE').split('.')[-1]

print(RELEASE_NAME, RAVEN_DSN)

class Celery(celery.Celery):
    def on_configure(self):
        client = raven.Client(
            dsn=RAVEN_DSN,
            release=RELEASE_NAME
        )
        register_logger_signal(client)
        register_signal(client)

app = Celery(
    app='matrix_stats',
    broker='redis://%s:%s/4' % (
        os.environ.get('REDIS_HOST'),
        os.environ.get('REDIS_PORT'),
    )
)

app.autodiscover_tasks(['matrix_bot.tasks'])
