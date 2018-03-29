import requests
import os
from time import sleep
from room_stats.models import Room

token = os.environ.get("GITTER_API_TOKEN")
rs = requests.Session()
rs.headers.update({
    'User-Agent': 'Matrixbot/1.0 (+https://matrixstats.org)',
    'Authorization': 'Bearer %s' % token,
})
room_endpoint = "https://api.gitter.im/v1/rooms?q=%s"


class GitterException(Exception):
    pass

def update_gitter_rooms(skip_inactive=True):
    """ Update gitter rooms descriptions using gitter API """
    if skip_inactive:
        rooms = Room.objects.filter(aliases__iregex="gitter_", inactive=False)
    else:
        rooms = Room.objects.filter(aliases__iregex="gitter_")

    for room in rooms:
        sleep(3)
        r = rs.get(room_endpoint % room.name)
        print (room.name, r.status_code)
        if r.status_code == 401:
            raise GitterException("Invalid API token")
        data = r.json().get('results', [])
        data = [item for item in data if item['name'].lower() == room.name.lower() ] # narrow search results using strict filter
        if len(data) == 0:
            room.inactive = True
            room.save(update_fields=['inactive'])
            continue
        gitter_room = data[0]
        room.topic = gitter_room['topic']
        room.avatar_url = gitter_room['avatarUrl']
        room.inactive = False
        room.save(update_fields=['topic', 'avatar_url', 'inactive'])
