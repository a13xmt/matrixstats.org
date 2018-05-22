import re
from time import sleep

def parse_invites(self, data):
    """
    Extract invites information to compact list
    """
    invites = data.get('rooms', {}).get('invite')
    result = []
    for room_id in invites.keys():
        events = invites[room_id].get('invite_state', {}).get('events', [])
        events = {e['type']: e for e in events}
        meta = {
            'id': room_id,
            'name': events.get('m.room.name', {}).get('content', {}).get('name'),
            'scope': events.get('m.room.join_rules', {}).get('content', {}).get('join_rule'),
            'ts': events.get('m.room.member', {}).get('origin_server_ts'),
            'sender': events.get('m.room.member', {}).get('sender'),
        }
        result.append(meta)
    return result

def process_invites(self, data):
    """ Process invites and prepare to accept/decline them.

    Args:
        data (dict): /sync api response data
    """
    invites = parse_invites(self, data)
    if len(invites) > 0:
        pass

    accept = []
    decline = []
    pattern = "(.*ChanServ.*|.*rizon.*|.*irc.*|.*snoonet.*|.*freenode.*)"
    for invite in invites:
        if re.match(pattern, invite['sender']):
            decline.append(invite)
        else:
            accept.append(invite)
    return accept, decline
