import json
from .handlers import room_event_handlers

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
    if next_batch:
        self._to_cache('next_batch', next_batch)
    return process_messages(self, data)

def sync2(self, filter_obj={}, since=None):
    with open("sync.json", "r") as f:
        data = f.read()
    process_messages(self, json.loads(data))

def process_messages(self, data):
    self._open_transaction()
    rooms = data.get('rooms', {}).get('join',{})
    for room_id, room in rooms.items():
        highlights = room.get('unread_notifications', {}).get('highlight_count', 0)
        if highlights:
            events = room.get('timeline', {}).get('events', [{}])
            last_event_id = events[-1].get('event_id', None)
            if last_event_id:
                print(self.mark_as_read(room_id, last_event_id))
                self.reply(room_id, "test reply")
        timeline = room.get('timeline', {})
        events = timeline.get('events', [])
        for event in events:
            event_handler = room_event_handlers.get(event.get('type'))
            result = event_handler(self, event, room_id) if event_handler else None
    self._commit_transaction()
    return data

