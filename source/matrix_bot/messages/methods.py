from .handlers import room_event_handlers

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
