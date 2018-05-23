import json
from datetime import datetime, timedelta
from .handlers import parse_invites

STATS_LIMIT_PER_SERVER = 120

def encode(self, delta, sync_started, sync_ended):
    data = [
        int(delta),
        int(sync_started.timestamp()),
        int(sync_ended.timestamp())
    ]
    data = ":".join([str(d) for d in data])
    return data

def decode(self, data):
    data = data.decode().split(':') if data else [0,0,0]
    data = [int(d) for d in data]
    data = (data[0], datetime.fromtimestamp(data[1]), datetime.fromtimestamp(data[2]))
    return data

def get_sync_stats(self):
    key = self._prefixed("sync_stats")
    stats = self.rds.lrange(key, 0, STATS_LIMIT_PER_SERVER)
    data = [decode(self, s) for s in stats]
    data = [
        [ str(item) for item in d ] for d in data
    ]
    return data

def get_last_sync_stats(self):
    key = self._prefixed("sync_stats")
    data = self.rds.lindex(key, 0)
    return decode(self, data)

def set_last_sync_stats(self, sync_started, sync_ended):
    key = self._prefixed("sync_stats")
    delta = (sync_ended - sync_started).total_seconds()
    data = encode(self, delta, sync_started, sync_ended)
    self.rds.lpush(key, data)
    self.rds.ltrim(key, 0, STATS_LIMIT_PER_SERVER)

def sync(self, filter_obj=None, since=None, timeout=30, fast_forward=False):
    key = self._prefixed("sync_stats")
    sync_started = datetime.now()
    ls_delta, ls_started, ls_ended = get_last_sync_stats(self)
    delta = sync_started - ls_ended
    if delta > timedelta(days=1):
        fast_forward = True

    cached_since = self._from_cache('next_batch')
    since = since or cached_since.decode() if cached_since else None

    if fast_forward:
        timeout = 0
        since = None
        filter_obj = {'room': {'rooms': [], 'state': {'limit': 1,}, 'timeline': {'limit': 1,}}}
    filter_value = json.dumps(filter_obj) if filter_obj is not None else self.server.data.get('filter_id')
    qs = "timeout=%s&" % (timeout * 1000)
    if filter_value:
        qs += "filter=%s&" % filter_value
    if since:
        qs += "since=%s&" % since
    r = self.api_call(
        "GET",
        "/sync?%s" % qs,
    )
    sync_ended = datetime.now()
    data = r.json()
    next_batch = data.get('next_batch')
    self._to_cache('next_batch', next_batch)
    set_last_sync_stats(self, sync_started, sync_ended)
    return data

def sync_invites(self):
    filter_obj = {'room': {'rooms': [], 'state': {'limit': 1,}, 'timeline': {'limit': 1,}}}
    filter_value = json.dumps(filter_obj)
    r = self.api_call(
        "GET",
        "/sync?full_state=true&filter=%s" % filter_value
    )
    data = r.json()
    return data

def get_rooms(self, timeout=60, chunk_size=2000, limit=None):
    """ Get all public rooms from the homeserver
    and upload them to the database"""
    params = {
        'limit': limit if (limit and limit <= chunk_size) else chunk_size
    }
    upper_time_bound = datetime.now() + timedelta(seconds=timeout)
    rooms = []
    next_chunk = None
    while True:
        if next_chunk:
            params['since'] = next_chunk
        r = self.api_call(
            "GET",
            "/publicRooms",
            params=params
        )
        data = r.json()
        rooms.extend(data.get('chunk'))
        next_chunk = data.get('next_batch', None)
        if next_chunk is None or (limit and len(rooms) >= limit):
            break
        if datetime.now() > upper_time_bound:
            raise TimeoutError()
    return rooms

from django_bulk_update.helper import bulk_update
from django.db import transaction
from room_stats.models import Room, DailyMembers, Server
@transaction.atomic
def save_rooms(self, rooms):

    obtained = len(rooms)
    print("Rooms obtained: %s" % obtained)
    # Exclude known primary homeservers
    # They would update their rooms individually
    exclude_servers = [
        s.get('hostname') for s in
        Server.objects.filter(status='r').exclude(hostname=self.server.hostname).values('hostname')
    ]
    rooms = [
        room for room in rooms if (room.get('room_id').split(':')[-1] not in exclude_servers)
    ]

    rooms_list = rooms
    rooms_dict = {room['room_id']: room for room in rooms_list}
    room_ids = [ r['room_id'] for r in rooms_list ]
    covered = len(rooms_list)
    print("Rooms covered: %s" % covered)

    # split rooms before bulk_create and bulk_update
    existing_rooms = Room.objects.filter(id__in=room_ids)
    existing_room_ids = [room.id for room in existing_rooms]
    new_room_ids = [id for id in room_ids if id not in existing_room_ids]
    new = len(new_room_ids)
    print("New rooms: %s" % new_room_ids)

    avatar_url_template = "https://" + self.server.hostname + "/_matrix/media/r0/thumbnail/%s?width=128&height=128"
    date_now = datetime.now()
    for room in existing_rooms:
        r = rooms_dict.get(room.id)
        topic = r.get('topic')

        # Avatars part is a bit tricky, since some servers
        # have weak media servers. We will prefer
        # matrix.org CDN server whenever it's possible
        avatar_url = None
        avatar_path = r.get('avatar_url', '')[6:]
        old_avatar = room.avatar_url or ""
        # Rewrite avatar path ONLY if it's not belong to matrix.org CDN
        if not "matrix.org" in old_avatar:
            avatar_url = avatar_url_template % avatar_path if avatar_path else ''

        room.name = r.get('name', '')
        room.aliases = ", ".join(r.get('aliases', []))
        room.topic = topic if topic else room.topic
        room.members_count = r.get('num_joined_members', 0)
        room.avatar_url = avatar_url if avatar_url else room.avatar_url
        room.is_public_readable = r.get('world_readable', False)
        room.is_guest_writeable = r.get('guest_can_join', False)
        room.updated_at = date_now
        room.federated_with[self.server.hostname] = str(datetime.now())
    bulk_update(existing_rooms)

    new_rooms = []
    for room_id in new_room_ids:
        r = rooms_dict.get(room_id)
        avatar_path = r.get('avatar_url', '')[6:]
        avatar_url = avatar_url_template % avatar_path if avatar_path else ''
        room = Room(
            id=r['room_id'],
            name=r.get('name',''),
            aliases=", ".join(r.get('aliases', [])),
            topic=r.get('topic',''),
            members_count=r.get('num_joined_members', 0),
            avatar_url=avatar_url,
            is_public_readable=r.get('world_readable'),
            is_guest_writeable=r.get('guest_can_join'),
            created_at=date_now,
            updated_at=date_now
        )
        new_rooms.append(room)
    Room.objects.bulk_create(new_rooms)


    # Update room members
    rooms = Room.objects.filter(id__in=room_ids)

    date_for_id = date_now.strftime("%Y%m%d")

    # Delete old records
    dm_ids = ["%s-%s" % (room.id, date_for_id) for room in rooms]
    DailyMembers.objects.filter(
        id__in=dm_ids
    ).delete()

    daily_members = [
        DailyMembers(
            id="%s-%s" % ( room.id, date_for_id),
            room_id=room.id,
            members_count=room.members_count
        ) for room in rooms
    ]
    DailyMembers.objects.bulk_create(daily_members)

    self.server.update_data({
        'total_rooms': obtained,
        'owned_rooms': covered
    })

    result = {
        'obtained': obtained,
        'covered': covered,
        'new': new
    }
    return result
