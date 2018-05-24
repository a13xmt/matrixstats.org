import os
import re
import celery
import requests
from uuid import uuid4
from inspect import getcallargs
from celery_once import QueueOnce
from celery_once.tasks import AlreadyQueued
from matrix_stats.celery import app
from django.utils import timezone
from datetime import datetime, timedelta
from eventlet import sleep

from room_stats.models import Server, Tag, Room, RoomStatisticalData
from matrix_bot.resources import rds_sync
from matrix_bot.core import MatrixHomeserver
from matrix_bot.exception import StopSync, DiscardTask

class AlreadyLocked(Exception):
    def __init__(self, countdown):
        self.message = "Expires in {} seconds".format(countdown)
        self.countdown = countdown

class RepeatableMutexTask(celery.Task):
    """
    Represents repeatable task that can be run only once.
    Any additional calls to the task would be rejected.

    Class-wise arguments:
    continue_exceptions -- Set of exceptions that shouldn't break the schedule.
    terminate_exceptions -- Set of exceptions that would finish the schedule after the task returns.
    mutex_max_exec_time -- Upper time limit to consider task as alive.
    mutex_lock_keys -- List of unique task arguments that forms an lock.
    """

    continue_exceptions = set()
    terminate_exceptions = set()
    mutex_max_exec_time = 60
    mutex_lock_keys = None
    rds = rds_sync

    def get_key(self, args, kwargs):
        """
        Build a lock key based on the task name and its arguments
        """
        args = args or {}
        kwargs = kwargs or {}
        call_args = getcallargs(self.run, *args, **kwargs)
        if isinstance(call_args.get('self'), celery.Task):
            del call_args['self']

        keys = sorted(self.mutex_lock_keys) if type(self.mutex_lock_keys) is list else [self.mutex_lock_keys]
        accum = []
        for key in keys:
            accum.append("%s-%s" % (key, call_args[key]))
        key = "m:%s:%s" % (self.name, ":".join(accum))
        return key

    def raise_or_lock(self, key, uuid):
        """
        Lock the given redis key, making another instances
        of the task with the same arguments unable to run.
        If the lock already exists, exception raised.
        """
        print("Attempting to lock key %s with uuid %s" % (key, uuid))
        lock_uuid = self.rds.get(key)
        lock_uuid = lock_uuid.decode() if lock_uuid else None
        safe = not lock_uuid or lock_uuid == uuid
        if not safe:
            ttl = self.rds.ttl(key)
            raise AlreadyLocked(ttl)
        self.rds.set(key, uuid, ex=self.mutex_max_exec_time)

    def __call__(self, *args, **kwargs):
        """
        We need to catch some exceptions before the worker
        can report task as failed. Some exceptions
        may be used to interrupt the task quietly if required.
        """
        try:
            retval = super(RepeatableMutexTask, self).__call__(*args, **kwargs)
        except self.continue_exceptions:
            retval = {'result': 'RECOVERED'}
        except self.terminate_exceptions:
            retval = {'result': 'TERMINATE'}
        return retval

    def apply_async(self, args=None, kwargs=None, **options):
        """
        Makes the current task run indefenetly. The task can only
        be stopped in case of critical exception, or special exit
        code from the worker.
        """

        if not self.mutex_lock_keys:
            raise RuntimeError("No mutex_lock_keys set for RepeatableMutexTask")

        args = args or {}
        kwargs = kwargs or {}
        call_args = getcallargs(self.run, *args, **kwargs)

        uuid = kwargs.get('mutex_uuid')
        if not uuid:
            uuid = str(uuid4())
            kwargs['mutex_uuid'] = uuid
        key = self.get_key(args, kwargs)
        self.raise_or_lock(key, uuid)
        return super(RepeatableMutexTask, self).apply_async(args, kwargs, **options)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Repreat the task in case it was completed successfully.
        """
        # If the task was finished with an error,
        # just exit without rescheduling
        error = isinstance(retval, Exception) or (type(retval) is dict and retval.get("result") == "TERMINATE")
        if error:
            self.rds.delete(self.get_key(args,kwargs))
            return

        call_args = getcallargs(self.run, *args, **kwargs)
        if isinstance(call_args.get('self'), celery.Task):
            del call_args['self']

        # don't call the task immediately in case of errors
        if type(retval) is dict and retval.get("result") == "RECOVERED":
            sleep(30)

        # Now we can repeat the task
        self.apply_async(None, call_args)


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
        sync.apply_async((s.server.id,))
    return result

@app.task
def register_new_servers():
    """ Check newly added servers and register new account for them if possible """
    statuses = ['a', 'c']
    servers = Server.objects.filter(status__in=statuses)
    for server in servers:
        register.apply_async((server.id,))
    return {'queried': len(servers)}

@app.task(
    base=RepeatableMutexTask,
    continue_exceptions=(
        DiscardTask,
        TimeoutError,
        ConnectionError,
        requests.exceptions.ConnectionError,
    ),
    terminate_exceptions=(StopSync,),
    mutex_exec_timeout=120,
    mutex_interval_key='interval',
    mutex_lock_keys=['server_id'])
def sync2(server_id, interval, mutex_uuid=None):
    """
    Synchronize last messages from the given server.
    Adjust sync interval, if changed.
    """
    s = MatrixHomeserver(server_id)

    result = { 'interval': s.server.sync_interval }
    if s.server.sync_allowed and s.server.status == 'r':
        events_received = s.sync()
        result['events'] = events_received
        s.server.last_sync_time = timezone.now()
        s.server.save()
        return result
    else:
        raise StopSync()

@app.task(
    base=RepeatableMutexTask,
    continue_exceptions=(
        DiscardTask,
        TimeoutError,
        ConnectionError,
        requests.exceptions.ConnectionError,
    ),
    terminate_exceptions=(StopSync,),
    mutex_max_exec_time=120,
    mutex_lock_keys=['server_id'])
def sync(server_id, mutex_uuid=None):
    s = MatrixHomeserver(server_id)
    if s.server.sync_allowed and s.server.status == 'r':
        data = s.sync()
        process.apply_async((server_id, data))
        return "OK"
    else:
        raise StopSync()

@app.task
def process(server_id, data):
    s = MatrixHomeserver(server_id)
    accept, decline = s.process_invites(data)
    if accept:
        accept_invites.apply_async((server_id, accept))
    if decline:
        decline_invites.apply_async((server_id, decline))
    s.process_messages(data)

@app.task
def process_awaiting_invites(server_id):
    s = MatrixHomeserver(server_id)
    data = s.sync_invites()
    process.apply_async((server_id, data))

@app.task
def accept_invites(server_id, rooms_list):
    s = MatrixHomeserver(server_id)
    for room in rooms_list:
        s.join(room['id'], room['sender'])
        if len(rooms_list) > 1:
            sleep(10)
    return rooms_list

@app.task
def decline_invites(server_id, rooms_list):
    s = MatrixHomeserver(server_id)
    for room in rooms_list:
        s.leave(room['id'])
        if len(rooms_list) > 1:
            sleep(10)
    return rooms_list

@app.task
def reply(server_id, room_id, message):
    pass


@app.task
def sync_all():
    servers = Server.objects.filter(status='r', sync_allowed=True)
    for server in servers:
        try:
            sync.apply_async((server.id,))
        except AlreadyLocked:
            pass


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
    try:
        rooms = s.get_rooms()
    except (ConnectionError, TimeoutError, requests.exceptions.ConnectionError):
        return {'result': 'CONN_ERR'}
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


@app.task
def update_joined_rooms(server_id):
    s = MatrixHomeserver(server_id)
    try:
        joined_rooms = s.fetch_joined_rooms()
    except (ConnectionError, TimeoutError, requests.exceptions.ConnectionError):
        return {'result': 'CONN_ERR'}
    banned_rooms = s.update_banned_rooms()
    result = {
        'joined': len(joined_rooms),
        'banned': len(banned_rooms)
    }
    return result

@app.task
def update_all_joined_rooms():
    servers = Server.objects.filter(status='r', sync_allowed=True)
    for server in servers:
        update_joined_rooms.apply_async((server.id, ))

# disabled in result of 15.05.18 incedent
# @app.task
# def join_rooms(server_id, limit=100):
#     s = MatrixHomeserver(server_id)
#     rooms = s.get_rooms_to_join()[:limit]
#     joined = []
#     for room_id in rooms:
#         try:
#             joined.append(s.join(room_id))
#         except (ConnectionError, TimeoutError, requests.exceptions.ConnectionError):
#             pass
#         sleep(3)
#     result = {'joined': len(joined)}
#     return result

# @app.task
# def join_all_rooms():
#     servers = Server.objects.filter(status='r', sync_allowed=True)
#     for server in servers:
#         join_rooms.apply_async((server.id, ))

@app.task
def compress_statistical_data():
    date = datetime.now()
    # remove daily data older than 14 days
    RoomStatisticalData.objects.filter(
        period='d',
        starts_at__lte=(date - timedelta(days=14))
    ).delete()
    # remove daily event data older than 7 days
    RoomStatisticalData.objects.filter(
        period='d',
        starts_at__lte=(date - timedelta(days=7))
    ).update(data={})
    # remove weekly event data older than 30 days
    RoomStatisticalData.objects.filter(
        period='w',
        starts_at__lte=(date - timedelta(days=30))
    ).update(data={})
    # remove monthly event data older than 90 days
    RoomStatisticalData.objects.filter(
        period='m',
        starts_at__lte=(date - timedelta(days=90))
    ).update(data={})

@app.task
def delete_inactive_rooms(days=7):
    Room.objects.filter(
        updated_at__lte=(datetime.now() - timedelta(days=days))
    ).delete()

