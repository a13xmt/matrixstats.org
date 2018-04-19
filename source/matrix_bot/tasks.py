from celery_once import QueueOnce
from matrix_stats.celery import app

from room_stats.models import Server
from matrix_bot.core import MatrixHomeserver

import time
@app.task(base=QueueOnce, once={'timeout': 60})
def register(server_id):
    """ Register new account on the chosen server and
    set username, avatar and filter for futher sync requests.
    """
    s = MatrixHomeserver(server_id)
    if s.server.status == 'a':
        s.verify_existence()
    if s.server.status == 'c':
        s.register()
    if s.server.status == 'r':
        filter_id = s.server.data.get("filter_id", None)
        profile_data = s.server.data.get("profile_data", None)
        if not filter_id:
            s.upload_filter()
        if not profile_data:
            s.update_profile()

@app.task
def register_new_servers():
    """ Check newly added servers and register new account for them if possible """
    statuses = ['a', 'c']
    servers = Server.objects.filter(status__in=statuses)
    for server in servers:
        register.apply_async((server.id,))


