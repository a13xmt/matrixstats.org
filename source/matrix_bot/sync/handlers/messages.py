def m_text_handler(self, event):
    pass

def m_emote_handler(self, event):
    pass

def m_notice_handler(self, event):
    pass

def m_image_handler(self, event):
    pass

def m_file_handler(self, event):
    pass

def m_location_handler(self, event):
    pass

def m_audio_handler(self, event):
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
