from uuid import uuid4

def reply(self, room_id, msg):
    data = {
        "msgtype": "m.notice",
        "body": msg
    }
    response = self.api_call(
        "PUT",
        "/rooms/%s/send/%s/%s" % (room_id, "m.room.message", str(uuid4())[0:8]),
        json=data
    )
    return response.json()

def mark_as_read(self, room_id, event_id):
    response = self.api_call(
        "POST",
        "/rooms/%s/receipt/%s/%s" % (room_id, "m.read", event_id),
        json={}
    )
    return response.json()
