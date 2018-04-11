
def join_room(self, room_id):
    response = self.api_call("POST", "/rooms/%s/join" % room_id, json={})
    if response.status_code == 200:
        return response.json().get('room_id')
