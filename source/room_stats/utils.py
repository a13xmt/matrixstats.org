import json
import re
import os
import requests
from datetime import datetime, timedelta
from django.db import transaction

from room_stats.models import Room, DailyMembers, Tag, ServerStats

rs = requests.Session()
rs.headers.update({'User-Agent': 'Matrixbot/1.0 (+https://matrixstats.org)'})

class MatrixClientError(Exception):
    pass

class MatrixClientTimeoutError(MatrixClientError):
    pass

class MatrixClient:
    def __init__(self, server, username=None, password=None, token=None):
        self.server = server
        self.username = username
        self.password = password
        self.token = token

    def __get_url(self, path):
        return "%s%s" % (self.server, path)

    def get_token(self):
        return self.token if self.token else self.login()

    def login(self, username=None, password=None):
        username = username or self.username
        password = password or self.password
        payload = {
            'user': username,
            'password': password,
            'type': 'm.login.password',
        }
        r = rs.post(
            self.__get_url('/login'),
            json=payload
        )
        if r.status_code == 200:
            self.token = r.json()['access_token']
            return self.token
        else:
            raise MatrixClientError(r.text)

    def get(self, path, params={}):
        params['access_token'] = self.get_token()
        r = rs.get(
            self.__get_url(path),
            params=params
        )
        if r.status_code == 200:
            return r.json()
        else:
            raise MatrixClientError(r.text)

    def get_public_rooms(self, timeout=30, chunk_size=2000, limit=None, args={}):
        upper_time_bound = datetime.now() + timedelta(seconds=timeout)
        if limit and limit <= chunk_size:
            args['limit'] = limit
        else:
            args['limit'] = chunk_size
        rooms = []
        next_chunk = None
        while True:
            if next_chunk:
                args['since'] = next_chunk
            data = self.get('/publicRooms', args)
            rooms.extend(data.get('chunk'))
            next_chunk = data.get('next_batch', None)
            if next_chunk is None:
                break
            if limit and len(rooms) >= limit:
                break
            if datetime.now() > upper_time_bound:
                raise MatrixClientTimeoutError()
        return rooms




# @transaction.atomic
# def update_rooms():
#     date = datetime.now().strftime("%d%m%y")
#     f = open('room_stats/matrix-rooms-%s.json' % date, 'r')
#     rooms = json.loads(f.read())['chunk']
#     print("Rooms found: %s" % len(rooms))
#     for room in rooms:
#         r = Room(
#             id=room['room_id'],
#             name=room.get('name',''),
#             aliases=", ".join(room.get('aliases', [])),
#             topic=room.get('topic',''),
#             members_count=room['num_joined_members'],
#             avatar_url=room.get('avatar_url', ''),
#             is_public_readable=room['world_readable'],
#             is_guest_writeable=room['guest_can_join']
#         )
#         r.save()


# def daily_stats_to_file():
#     TOKEN = os.environ.get("MATRIX_TOKEN", "")
#     date = datetime.now().strftime("%d%m%y")
#     c = MatrixClient("https://matrix.org/_matrix/client/r0", token=TOKEN)
#     result = c.api("/publicRooms")
#     f = open('room_stats/matrix-rooms-%s.json' % date, 'w')
#     f.write(json.dumps(result))
#     f.close()

def get_all_rooms_to_file(filename, limit=None):
    rooms = []
    username = os.environ.get("MATRIX_USERNAME")
    password = os.environ.get("MATRIX_PASSWORD")
    token = os.environ.get("MATRIX_TOKEN")
    c = MatrixClient("https://matrix.org/_matrix/client/r0",
                     username, password, token)
    rooms = c.get_public_rooms(limit=limit)
    f = open(filename, 'w')
    f.write(json.dumps(rooms))
    f.close()

from django_bulk_update.helper import bulk_update
@transaction.atomic
def update_rooms_from_file(filename):

    f = open(filename, 'r')
    rooms_list = json.loads(f.read())
    rooms_dict = {room['room_id']: room for room in rooms_list}
    room_ids = [ r['room_id'] for r in rooms_list ]
    print("Rooms found: %s" % len(rooms_list))

    # split rooms before bulk_create and bulk_update
    existing_rooms = Room.objects.filter(id__in=room_ids)
    existing_room_ids = [room.id for room in existing_rooms]
    new_room_ids = [id for id in room_ids if id not in existing_room_ids]
    print("new room ids: %s" % new_room_ids)

    date_now = datetime.now()
    for room in existing_rooms:
        r = rooms_dict.get(room.id)
        room.name = r.get('name', '')
        room.aliases = ", ".join(r.get('aliases', []))
        room.topic = r.get('topic','')
        room.members_count = r.get('num_joined_members', 0)
        room.avatar_url = r.get('avatar_url', '')
        room.is_public_readable = r.get('world_readable', False)
        room.is_guest_writeable = r.get('guest_can_join', False)
        room.updated_at = date_now
    bulk_update(existing_rooms)

    new_rooms = []
    for room_id in new_room_ids:
        r = rooms_dict.get(room_id)
        room = Room(
            id=r['room_id'],
            name=r.get('name',''),
            aliases=", ".join(r.get('aliases', [])),
            topic=r.get('topic',''),
            members_count=r.get('num_joined_members', 0),
            avatar_url=r.get('avatar_url', ''),
            is_public_readable=r.get('world_readable'),
            is_guest_writeable=r.get('guest_can_join'),
            created_at=date_now,
            updated_at=date_now
        )
        new_rooms.append(room)
    Room.objects.bulk_create(new_rooms)

@transaction.atomic
def update_tags():
    # clear previous relations
    Tag.objects.all().delete()
    hashtag = re.compile("#\w+")
    rooms = Room.objects.filter(members_count__gt=5, topic__iregex=r'#\w+')
    for room in rooms:
        room_tags = hashtag.findall(room.topic)
        for tag in room_tags:
            linked_tag = Tag(
                id=tag[1:],
            )
            linked_tag.save()
            linked_tag.rooms.add(room)


@transaction.atomic
def update_daily_members():
    rooms = Room.objects.all()

    date = datetime.now()
    date_for_id = date.strftime("%Y%m%d")

    # Delete old records
    DailyMembers.objects.filter(
        date__year=date.year,
        date__month=date.month,
        date__day=date.day
    ).delete()

    daily_members = [
        DailyMembers(
            id="%s-%s" % ( room.id, date_for_id),
            room_id=room.id,
            members_count=room.members_count
        ) for room in rooms
    ]
    DailyMembers.objects.bulk_create(daily_members)


def update():
    date = datetime.now().strftime("%d%m%y")

    app_stats_dir = os.environ.get("APP_STATS_DIR")
    filename = os.path.join(
        app_stats_dir,
        "matrix-rooms-%s.json" % date
    )

    get_all_rooms_to_file(filename)
    update_rooms_from_file(filename)

    update_tags()
    update_daily_members()

from requests.exceptions import Timeout
def update_server_stats():
    username = os.environ.get("MATRIX_USERNAME")
    password = os.environ.get("MATRIX_PASSWORD")

    payload = {
        'user': username,
        'password': password,
        'type': 'm.login.password',
    }
    latency = 0
    try:
        r = rs.post(
            'https://matrix.org/_matrix/client/r0/login',
            json=payload
        )
        latency = r.elapsed.microseconds / 1000
    except Timeout:
        latency = 0
    stats = ServerStats(
        server='matrix.org',
        latency=latency
    )
    stats.save()


def import_daily_members():
    """Update daily members stastistics from directory's files"""
    import glob
    app_stats_dir = os.environ.get('APP_STATS_DIR')
    pattern = os.path.join(
        app_stats_dir,
        "matrix-rooms-*.json"
    )
    for daily_stats_file in glob.glob(pattern):
        with open(daily_stats_file) as f:
            data = f.read()
            rooms = json.loads(data)
            rooms = rooms if type(rooms) is list else rooms['chunk'] # old format

            # parse date from file name
            date = daily_stats_file[-11:-5]
            date = datetime.strptime(date, "%d%m%y")

            # Delete old records
            DailyMembers.objects.filter(
                date__year=date.year,
                date__month=date.month,
                date__day=date.day
            ).delete()

            date_for_id = date.strftime("%Y%m%d")

            daily_members = [
                DailyMembers(
                    id="%s-%s" % ( room['room_id'], date_for_id),
                    room_id=room['room_id'],
                    members_count=room['num_joined_members'],
                    date=date
                ) for room in rooms
            ]

            DailyMembers.objects.bulk_create(daily_members)
            print("Rooms count: %s | %s" % (len(daily_members), date))

