import json
from room_stats.models import Room

def load_data():
    f = open('room_stats/matrix-rooms.json', 'r')
    rooms = json.loads(f.read())['chunk']
    rooms_list = []
    for room in rooms:
        rooms_list.append(Room(
            id=room['room_id'],
            name=room.get('name',''),
            aliases=", ".join(room.get('aliases', [])),
            topic=room.get('topic',''),
            members_count=room['num_joined_members'],
            avatar_url=room.get('avatar_url', ''),
            is_public_readable=room['world_readable'],
            is_guest_writeable=room['guest_can_join']
        ))
    Room.objects.bulk_create(rooms_list)
