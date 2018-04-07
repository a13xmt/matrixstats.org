import requests
import json
import traceback
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix_stats.settings.dev")
django.setup()

from matrix_bot.registration import continue_registration
from matrix_bot.utils import serialize, critical
from room_stats.models import Server
from matrix_bot.resources import rs

def handle_server_instance(server_id):
    """ Check the server instance for uncompleted registration
    and finish it if neccessary"""
    server = Server.objects.get(pk=server_id)
    if server.status == 'a':
        verify_server_existence(server)
    if server.status == 'c':
        continue_registration(server)


def verify_server_existence(server):
    """ Check the server existance and set the status accordingly"""
    response_data, response_code = None, None
    server.last_response_code = -1
    try:
        r = rs.get(server.api(suffix="/_matrix/client/versions"))
        response_data = r.json()
        response_code = r.status_code
    except json.decoder.JSONDecodeError as ex:
        server.last_response_data = serialize(ex)
        server.status = 'u'
    except requests.exceptions.RequestException as ex:
        server.last_response_data = serialize(ex)
        server.status = 'u'
    except ex:
        server.last_response_data = serialize(ex)
        server.status = 'u'
        critical(ex)
    else:
        server.last_response_data = response_data
        server.last_response_code = response_code
        if response_code == 200 and "versions" in response_data:
            server.status = 'c'
        elif r.status_code >= 400:
            server.status = 'u'
        else:
            server.status = 'n'
    server.save(update_fields=['last_response_data', 'last_response_code', 'status'])


def test():
    s = Server.objects.last()
    handle_server_instance(s.id)
