from celery_once import QueueOnce
from matrix_stats.celery import app

from room_stats.models import Server
from matrix_bot.core import MatrixHomeserver

import time
@app.task(base=QueueOnce, once={'timeout': 60})
def register(server_id):
    s = MatrixHomeserver(server_id)
    if s.server.status == 'a':
        s.verify_existence()
    if s.server.status == 'c':
        s.register()

@app.task
def register_new_servers():
    """ Check the newly added servers and register on them if possible """
    statuses = ['a', 'c']
    servers = Server.objects.filter(status__in=statuses)
    for server in servers:
        register.apply_async((server.id,))


