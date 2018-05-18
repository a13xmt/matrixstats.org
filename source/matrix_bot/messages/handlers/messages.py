from datetime import datetime

def getkey(event_type, room_id, datestr):
    return "e__%s__%s__%s" % (
        event_type,
        room_id,
        datestr
    )

def m_text_handler(self, event, room_id):
    # msg = event.get('content', {}).get('body')
    sender = event.get('sender')
    timestamp = event.get('origin_server_ts') / 1000
    created_at = datetime.fromtimestamp(timestamp)
    event_id = event.get('event_id')

    datestr = created_at.strftime("%Y-%m-%d")

    key = getkey("m.text", room_id, datestr)
    self._to_set(key, event_id, 86400*2)

    key = getkey("c.dm", room_id, datestr)
    self._to_set(key, sender, 86400*2)

    key = "active_rooms__%s" % datestr
    self._to_set(key, room_id,  86400*2)


def m_emote_handler(self, event, room_id):
    pass

def m_notice_handler(self, event, room_id):
    pass

def m_image_handler(self, event, room_id):
    pass

def m_file_handler(self, event, room_id):
    pass

def m_location_handler(self, event, room_id):
    pass

def m_audio_handler(self, event, room_id):
    pass

message_event_handlers = {
    "m.text": m_text_handler,
    "m.emote": m_emote_handler,
    "m.notice": m_notice_handler,
    "m.image": m_image_handler,
    "m.file": m_file_handler,
    "m.location": m_location_handler,
    "m.audio": m_audio_handler
}
