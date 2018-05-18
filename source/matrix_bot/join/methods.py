from room_stats.models import Room
from datetime import datetime

LOG_LIMIT_PER_SERVER = 100

def mark_as_banned(self, room_id):
    key = self._prefixed("banned_rooms")
    self.rds.sadd(key, room_id)

def mark_as_unbanned(self, room_id):
    key_banned = self._prefixed("banned_rooms")
    key_joined = self._prefixed("joined_rooms")
    key_was_joined = self._prefixed("was_joined_rooms")
    p = self.rds.pipeline()
    p.srem(key_banned)
    p.srem(key_joined)
    p.srem(key_was_joined)
    p.execute()

def mark_as_joined(self, room_id, invite_from):
    key = self._prefixed("joined_rooms")
    self.rds.sadd(key, room_id)
    key = self._prefixed("was_joined_rooms")
    self.rds.sadd(key, room_id)
    key = self._prefixed("room_join_log")
    data = ":".join([
        int(datetime.now().timestamp()),
        room_id,
        invite_from or ''
    ])
    self.rds.lpush(key, data)
    self.rds.ltrim(key, 0, LOG_LIMIT_PER_SERVER)

def get_banned_rooms(self):
    key = self._prefixed("banned_rooms")
    rooms = [ r.decode for r in self.rds.smembers(key)]
    return rooms

def get_joined_rooms(self):
    key = self._prefixed("joined_rooms")
    rooms = [ r.decode() for r in self.rds.smembers(key)]
    return rooms

def fetch_joined_rooms(self):
    r = self.api_call("GET", "/joined_rooms")
    rooms = r.json().get("joined_rooms")
    key_joined = self._prefixed("joined_rooms")
    key_was_joined = self._prefixed("was_joined_rooms")
    if rooms:
        p = self.rds.pipeline()
        p.delete(key_joined)
        p.sadd(key_joined, *rooms)
        p.sadd(key_was_joined, *rooms)
        p.execute()
        return rooms
    else:
        self.rds.delete(key_joined)
        return []

def join(self, room_id, invite_from=None):
    r = self.api_call("POST", "/rooms/%s/join" % room_id, json={}, forward_error_codes=[403])
    data = r.json()
    if r.status_code == 403:
        mark_as_banned(self, room_id)
    else:
        mark_as_joined(self, room_id, invite_from)
    return data.get('room_id')

def leave(self, room_id, reason=None):
    r = self.api_call("POST", "/rooms/%s/leave" % room_id, json={})
    data = r.json()
    key = self._prefixed("joined_rooms")
    self.rds.srem(key, room_id)
    key = self._prefixed("was_joined_rooms")
    self.rds.srem(key, room_id)
    key = self._prefixed("room_leave_log")
    data = ":".join([
        int(datetime.now().timestamp()),
        room_id,
        reason or ''
    ])
    self.rds.lpush(key, data)
    self.rds.ltrim(key, 0, LOG_LIMIT_PER_SERVER)

    return room_id

def update_banned_rooms(self):
    key_joined = self._prefixed("joined_rooms")
    key_was_joined = self._prefixed("was_joined_rooms")
    key_banned_rooms = self._prefixed("banned_rooms")
    rooms = self.rds.sdiff(key_was_joined, key_joined)
    if rooms:
        self.rds.sadd(key_banned_rooms, *rooms)
    return rooms

def get_rooms_to_join(self):
    hostname = self.server.hostname
    all_rooms = list(Room.objects.filter(id__endswith=hostname).order_by('-members_count').values_list('id', flat=True))
    key_was_joined = self._prefixed("was_joined_rooms")
    was_joined_rooms = [r.decode() for r in self.rds.smembers(key_was_joined)]
    candidates = [room for room in all_rooms if room not in was_joined_rooms]
    return candidates
