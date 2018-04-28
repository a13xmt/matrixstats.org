import os
import re
import celery
from uuid import uuid4
from inspect import getcallargs
from celery_once import QueueOnce
from celery_once.tasks import AlreadyQueued
from matrix_stats.celery import app
from django.utils import timezone
from datetime import datetime, timedelta

from room_stats.models import Server, Tag, Room
from matrix_bot.resources import rds_sync
from matrix_bot.core import MatrixHomeserver
from matrix_bot.exception import StopSync

class AlreadyLocked(Exception):
    def __init__(self, countdown):
        self.message = "Expires in {} seconds".format(countdown)
        self.countdown = countdown

class RepeatableMutexTask(celery.Task):
    """
    Represents repeatable task that can be run only once.
    Any additional calls to the task would be rejected,
    based on selected task arguments.

    Class-wise arguments:
    continue_exceptions -- Set of exceptions that can be used to exit the task on its behalf.
    mutex_lock_keys -- List of unique task arguments that would be used for lock key.
    mutex_interval_key -- Name of the task argument with the next interval value.
    """

    continue_exceptions = set()
    terminate_exceptions = set()
    mutex_max_exec_time = 60
    mutex_lock_keys = None
    mutex_interval_key = None
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

    def raise_or_lock(self, key, uuid, interval):
        """
        Lock the given redis key, making another instances
        of the task with the same arguments unable to run.
        If the lock already exists, exception would be raised.
        """
        print("Attempting to lock for %ss key %s with uuid %s" % (interval, key, uuid))
        lock_uuid = self.rds.get(key)
        lock_uuid = lock_uuid.decode() if lock_uuid else None
        safe = not lock_uuid or lock_uuid == uuid
        if not safe:
            ttl = self.rds.ttl(key)
            raise AlreadyLocked(ttl)
        self.rds.set(key, uuid, ex=self.mutex_max_exec_time+interval)

    def __call__(self, *args, **kwargs):
        """
        We need to catch some exceptions before the worker
        can report that the task was failed. Some exceptions
        may be used to interrupt the task quietly on its behalf.
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
        Makes the current task run indefenetly with the given
        time interval. The task can only be stopped in case of
        critical exception, or special exit code from the worker.
        """

        if not self.mutex_lock_keys:
            raise RuntimeError("No mutex_lock_keys set for RepeatableMutexTask")
        if not self.mutex_interval_key:
            raise RuntimeError("No mutex_interval_key set for RepeatableMutexTask")

        args = args or {}
        kwargs = kwargs or {}
        call_args = getcallargs(self.run, *args, **kwargs)
        interval = call_args.get(self.mutex_interval_key)

        uuid = kwargs.get('mutex_uuid')
        if not uuid:
            uuid = str(uuid4())
            kwargs['mutex_uuid'] = uuid
        key = self.get_key(args, kwargs)
        self.raise_or_lock(key, uuid, interval)
        return super(RepeatableMutexTask, self).apply_async(args, kwargs, **options)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Reschedule the task in case it was completed successfully.

        The task itself can return an object with mutex_interval_key field set,
        to use the selected interval for the next call. For example, the task
        may return {'interval': 10} if 'interval' was used as a mutex_interval_key,
        and it would be used as the next countdown value.

        This allows to control task interval in a runtime instead of relying
        on a constant schedule.
        """
        # If the task was finished with an error,
        # just exit without rescheduling
        error = isinstance(retval, Exception) or (type(retval) is dict and retval.get("result") == "TERMINATE")
        if error:
            self.rds.delete(get_key(args,kwargs))
            return

        # Get the next task interval from the task return value, or from the initial task args
        call_args = getcallargs(self.run, *args, **kwargs)
        task_result_interval = retval.get(self.mutex_interval_key) if (type(retval) is dict) else None
        interval = task_result_interval or call_args.get(self.mutex_interval_key)

        # Now we can reschedule the task
        self.apply_async(args, kwargs, countdown=interval)


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
        try:
            sync.apply_async((server.id, server.sync_interval ))
        except AlreadyQueued:
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

