import re
from celery_once import QueueOnce
from matrix_stats.celery import app
from django.utils import timezone
from datetime import datetime, timedelta

from room_stats.models import Server, Tag, Room
from matrix_bot.core import MatrixHomeserver

import time
@app.task(base=QueueOnce, once={'timeout': 60})
def register(server_id):
    """ Register new account on the chosen server and
    set username, avatar and filter for futher sync requests.
    """
    # result is used only for task debugging, it can be safely removed
    result = {}
    s = MatrixHomeserver(server_id)
    if s.server.status == 'a':
        server_status = s.verify_existence()
        result['verify'] = server_status
    if s.server.status == 'c':
        registration_status = s.register()
        result['register'] = registration_status
    if s.server.status == 'r':
        filter_id = s.server.data.get("filter_id", None)
        profile_data = s.server.data.get("profile_data", None)
        if not filter_id:
            filter_id = s.upload_filter()
            result['filter_id'] = filter_id
        if not profile_data:
            profile_data = s.update_profile()
            result['profile_data'] = profile_data
    return result

@app.task
def register_new_servers():
    """ Check newly added servers and register new account for them if possible """
    statuses = ['a', 'c']
    servers = Server.objects.filter(status__in=statuses)
    for server in servers:
        register.apply_async((server.id,))
    return {'queried': len(servers)}


def on_sync_success(self, retval, task_id, args, kwargs):
    # FIXME log every success for homeserver status map
    if retval == "BREAK_SYNC":
        return
    interval = args[1]
    sync.apply_async(args, kwargs, countdown=interval)


def on_sync_fail(self, exc, task_id, args, kwargs, einfo):
    # FIXME break sync in case of some specific errors
    # FIXME log every fail data for homeserver status map details
    interval = args[1]
    sync.apply_async(args, kwargs, countdown=interval)

@app.task(base=QueueOnce, once={'timeout': 60, 'unlock_before_run': True}, on_success=on_sync_success, on_failure=on_sync_fail)
def sync(server_id, interval):
    """ Synchronize server history and store it for later use """
    s = MatrixHomeserver(server_id)
    # FIXME START remove this later for performance reasons
    s.server.last_sync_time = timezone.now()
    s.server.save()
    # FIXME END remove this later for performance reasons
    if s.server.sync_allowed and s.server.status == 'r':
        events_received = s.sync()
        return {'events': events_received}
    else:
        return "BREAK_SYNC"


@app.task
def sync_all():
    servers = Server.objects.filter(status='r', sync_allowed=True)
    for server in servers:
        sync.apply_async((server.id, server.sync_interval ))


@app.task
def save_statistics():
    servers = Server.objects.filter(sync_allowed=True)
    date = datetime.now() - timedelta(days=1)
    datestr = date.strftime("%Y-%m-%d")
    results = {
        'total': len(servers),
        'active': 0,
        'details': {}
    }
    for server in servers:
        s = MatrixHomeserver(server.id)
        rcount, active_rooms = s.get_active_rooms(datestr)
        print("%s: %s active rooms for %s (%s)" % (datestr, rcount, server.hostname, server.id))
        if rcount:
            results['active'] += 1
            results['details'][server.hostname] = 0
        for room in active_rooms:
            s.save_daily_stats(room, date)
            results['details'][server.hostname] += 1
    return results


@app.task(base=QueueOnce, once={'timeout': 120, 'unlock_before_run': True})
def get_rooms(server_id):
    s = MatrixHomeserver(server_id)
    rooms = s.get_rooms()
    result = s.save_rooms(rooms)
    return result

@app.task
def get_all_rooms():
    servers = Server.objects.filter(status='r')
    for server in servers:
        get_rooms.apply_async((server.id, ))

@app.task
def extract_tags():
    Tag.objects.all().delete()
    hashtag = re.compile("#\w+")
    rooms = Room.objects.filter(topic__iregex=r'#\w+')
    for room in rooms:
        room_tags = hashtag.findall(room.topic)
        for tag in room_tags:
            linked_tag = Tag(
                id=tag[1:],
            )
            linked_tag.save()
            linked_tag.rooms.add(room)

