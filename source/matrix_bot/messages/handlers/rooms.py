from datetime import datetime
from .messages import message_event_handlers

def room_message_handler(self, event, room_id):
    msg_type = event.get("content", {}).get("msgtype")
    msg_handler = message_event_handlers.get(msg_type)
    result = msg_handler(self, event, room_id) if msg_handler else None

def room_message_feedback_handler(self, event):
    pass

def room_name_handler(self, event, room_id):
    pass

def room_topic_handler(self, event, room_id):
    pass

def room_avatar_handler(self, event, room_id):
    pass

def room_pinned_events_handler(self, event, room_id):
    pass

room_event_handlers = {
    "m.room.message": room_message_handler,
    "m.room.message.feedback": room_message_feedback_handler,
    "m.room.name": room_name_handler,
    "m.room.topic": room_topic_handler,
    "m.room.avatar": room_avatar_handler,
    "m.room.pinned_events": room_pinned_events_handler,
}
