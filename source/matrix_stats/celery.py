from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

app = Celery(
    app='matrix_stats',
    broker='redis://%s:%s/4' % (
        os.environ.get('REDIS_HOST'),
        os.environ.get('REDIS_PORT'),
    )
)

app.autodiscover_tasks(['matrix_bot.tasks'])
