import json
from datetime import datetime, timedelta
from .handlers import room_event_handlers
from matrix_bot.exception import TimeoutError

def sync(self, filter_obj=None, since=None):
    filter_value = json.dumps(filter_obj) if filter_obj else self.server.data.get('filter_id')
    cached_since = self._from_cache('next_batch')
    since = since or cached_since.decode() if cached_since else None
    qs = ""
    if filter_value:
        qs += "filter=%s&" % filter_value
    if since:
        qs += "since=%s&" % since
    r = self.api_call(
        "GET",
        "/sync?%s" % qs,
    )
    data = r.json()
    next_batch = data.get('next_batch')
    with open("sync.json", "w") as f:
        f.write(json.dumps(data))
    result = process_messages(self, data)
    if next_batch:
        self._to_cache('next_batch', next_batch)
    return result

def sync2(self, filter_obj={}, since=None):
    with open("sync.json", "r") as f:
        data = f.read()
    process_messages(self, json.loads(data))

def process_messages(self, data):
    events_total = 0
    self._open_transaction()
    rooms = data.get('rooms', {}).get('join',{})
    for room_id, room in rooms.items():
        highlights = room.get('unread_notifications', {}).get('highlight_count', 0)
        if highlights:
            events = room.get('timeline', {}).get('events', [{}])
            last_event_id = events[-1].get('event_id', None)
            if last_event_id:
                print(self.mark_as_read(room_id, last_event_id))
                self.reply(room_id, "Somebody mentioned me. You can get my description here https://matrixstats.org/bot/")
        timeline = room.get('timeline', {})
        events = timeline.get('events', [])
        events_total += len(events)
        for event in events:
            event_handler = room_event_handlers.get(event.get('type'))
            result = event_handler(self, event, room_id) if event_handler else None
    self._commit_transaction()
    return events_total


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
from room_stats.models import Room, DailyMembers
@transaction.atomic
def save_rooms(self, rooms):

    rooms_list = rooms
    rooms_dict = {room['room_id']: room for room in rooms_list}
    room_ids = [ r['room_id'] for r in rooms_list ]
    print("Rooms found: %s" % len(rooms_list))

    # split rooms before bulk_create and bulk_update
    existing_rooms = Room.objects.filter(id__in=room_ids)
    existing_room_ids = [room.id for room in existing_rooms]
    new_room_ids = [id for id in room_ids if id not in existing_room_ids]
    print("new room ids: %s" % new_room_ids)

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

    return {'total': len(rooms_list)}
