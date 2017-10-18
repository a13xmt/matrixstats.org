import json
from datetime import datetime
from django.db import transaction

from room_stats.models import Room, DailyMembers

@transaction.atomic
def update_rooms():
    f = open('room_stats/matrix-rooms-181017.json', 'r')
    rooms = json.loads(f.read())['chunk']
    for room in rooms:
        r = Room(
            id=room['room_id'],
            name=room.get('name',''),
            aliases=", ".join(room.get('aliases', [])),
            topic=room.get('topic',''),
            members_count=room['num_joined_members'],
            avatar_url=room.get('avatar_url', ''),
            is_public_readable=room['world_readable'],
            is_guest_writeable=room['guest_can_join']
        )
        r.save()

@transaction.atomic
def update_daily_members():
    rooms = Room.objects.all()
    daily_members_list = []
    for room in rooms:
        dm = DailyMembers(
            room_id=room.id,
            members_count=room.members_count
        )
        dm.save()

def extract_tags():
    import re
    hashtag = re.compile("#\w+")
    rooms = Room.objects.filter(members_count__gt=5, topic__iregex=r'#\w+')
    tags = []
    for room in rooms:
        tags.extend(hashtag.findall(room.topic))
    return tags

def daily_stats_to_file():
    import requests
    import json
    from datetime import datetime
    import os

    class MatrixClient:
        def __init__(self, server, token):
            self.server = server
            self.token = token

        def api(self, path):
            r = requests.get(
                "%s%s" % (self.server, path),
                params={'access_token': self.token}
            )
            result = r.json()
            print(r.status_code)
            return result

    TOKEN = os.environ.get("MATRIX_TOKEN", "")
    date = datetime.now().strftime("%d%m%y")
    c = MatrixClient("https://matrix.org/_matrix/client/r0", TOKEN)
    result = c.api("/publicRooms")
    f = open('room_stats/matrix-rooms-%s.json' % date, 'w')
    f.write(json.dumps(result))
    f.close()


