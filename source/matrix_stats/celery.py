from __future__ import absolute_import, unicode_literals
import os
import celery
import raven
from raven.contrib.celery import register_signal, register_logger_signal
from celery.schedules import crontab


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
    'save-statistics-daily':  {
        'task': 'matrix_bot.tasks.save_statistics',
        'schedule': crontab(hour=1, minute=0),
    },
    'register-new-servers': {
        'task': 'matrix_bot.tasks.register_new_servers',
        'schedule': crontab(hour='*/1', minute=0)
    },
    'update-rooms-3h': {
        'task': 'matrix_bot.tasks.get_all_rooms',
        'schedule': crontab(hour='*/3', minute=12)
    },
    'update-joined-rooms-3h': {
        'task': 'matrix_bot.tasks.update_all_joined_rooms',
        'schedule': crontab(hour='*/3', minute=16),
    },
    'extract-tags-24h': {
        'task': 'matrix_bot.tasks.extract_tags',
        'schedule': crontab(hour='2', minute=0)
    },
    'compress-statistical-data-1w': {
        'task': 'matrix_bot.tasks.compress_statistical_data',
        'schedule': crontab(hour=3, minute=0, day_of_week='mon')
    },
    'delete-inactive-rooms-1d': {
        'task': 'matrix_bot.tasks.delete_inactive_rooms',
        'schedule': crontab(hour=4, minute=18)
    },
    'verify-bound-servers': {
        'task':  'user_area.tasks.verify_bound_servers',
        'schedule': crontab(hour='*/1', minute='*/15'),
    }
}

app.conf.task_routes = {
    'matrix_bot.tasks.sync': {'queue': 'sync'},
    'matrix_bot.tasks.join_rooms': {'queue': 'sync'},
    'matrix_bot.tasks.process_awaiting_invites': {'queue': 'sync'},
    'matrix_bot.tasks.accept_invites': {'queue': 'sync'},
    'matrix_bot.tasks.decline_invites': {'queue': 'sync'},
    'matrix_bot.tasks.reply': {'queue': 'sync'},
    'matrix_bot.tasks.process': {'queue': 'processing'},
    'matrix_bot.tasks.register': {'queue': 'service'},
    'matrix_bot.tasks.save_statistics': {'queue': 'service'},
    'matrix_bot.tasks.get_rooms': {'queue': 'service'},
    'matrix_bot.tasks.delete_inactive_rooms': {'queue': 'service'},
    'matrix_bot.tasks.extract_tags': {'queue': 'service'},
    'matrix_bot.tasks.update_joined_rooms': {'queue': 'service'},
    'matrix_bot.tasks.compress_statistical_data': {'queue': 'service'},
    'matrix_bot.tasks.sync_all': {'queue': 'control'},
    'matrix_bot.tasks.register_new_servers': {'queue': 'control'},
    'matrix_bot.tasks.get_all_rooms': {'queue': 'control'},
    'matrix_bot.tasks.update_all_joined_rooms': {'queue': 'control'},
    'matrix_bot.tasks.join_all_rooms': {'queue': 'control'},

    'user_area.tasks.verify_bound_servers': {'queue': 'sync'},
}

app.autodiscover_tasks(['matrix_bot.tasks', 'user_area.tasks', 'djcelery_email'])

