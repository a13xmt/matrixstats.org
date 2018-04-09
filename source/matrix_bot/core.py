import requests
import json
import traceback
import django
import os
import functools
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix_stats.settings.dev")
django.setup()

from matrix_bot.registration import continue_registration
from matrix_bot.utils import serialize, critical, prettify
from room_stats.models import Server
from matrix_bot.resources import rs, rds

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

def sync(server):
    r = rs.get(
        server.api("/sync"),
        json={'since': 's499291083_426347964_1064192_114962333_48751815_269211_5590083_5338311_7834'},
        headers={'Authorization': 'Bearer %s' % server.data.get('access_token')}
    )
    data = r.json()
    with open("sync.json", "w") as f:
        f.write(prettify(data))
    print(r.status_code, prettify(data))

class MatrixHomeserver():
    def __init__(self, server_id):
        self.server = Server.objects.get(pk=server_id)

    def _cache(self, glob='', expand=False):
        """ Scan redis for server-related data and display it. """
        keys = rds.keys("%s__%s*" % (self.server.hostname, glob))
        if not expand:
            keys = [k.decode() for k in keys]
            keys.sort()
            print(prettify(keys))
            return
        result = {}
        for key in keys:
            result[key.decode()] = [rds.get(key).decode(), rds.ttl(key)]
        print(prettify(result))

    def _from_cache(self, key):
        """ Get server-related data from redis """
        return rds.get("%s__%s" % (self.server.hostname, key))

    def _to_cache(self, key=None, value=None, expire=None, **kwargs):
        """ Set server-related data to redis """
        if key and value: return rds.set(
                "%s__%s" % (self.server.hostname, key),
                value, ex=expire
            )
        else:
            result = []
            for key in kwargs:
                result.append(rds.set(
                    "%s__%s" % (self.server.hostname, key),
                    kwargs[key], ex=expire
                ))
            return result

    def _get_access_token(self):
        """ Get access_token or obtain it if possible """
        access_token = (
            self.server.data.get('access_token') or
            self._from_cache('access_token') or
            self.login()
        )
        return str(access_token)

    def api_call(self, method, path, data=None, json=None, suffix=None, auth=True, headers={}, cache_errors=True, cache_timeout=60*60*24):
        """ Performs an API call to homeserver.
        Last response data can be cached, if required.
        """
        suffix = suffix or "/_matrix/client/r0"
        url = "https://%s%s%s" % (self.server.hostname, suffix, path)
        if auth:
            access_token = self._get_access_token()
            headers['Authorization'] = 'Bearer %s' % access_token
            response = rs.request(method=method, url=url, data=data, json=json, headers=headers)
        if cache_errors and response.status_code != 200:
            now = datetime.datetime.now().strftime("%Y-%m-%d+%H:%m")
            self._to_cache(**{
                'response__%s__%s__%s' % (now, response.status_code, path): response.json(),
            }, expire=cache_timeout)
        return response

    def login(self):
        device_id = self.server.data.get('device_id')
        login = self.server.login
        password = self.server.password
        if not (login or password):
            raise exception.AuthError("Login or Password not set for this server")
        auth_data = {
            'type': 'm.login.password',
            'user': login,
            'password': password,
            'device_id': device_id,
        }
        response = self.api_call("POST", "/login", json=auth_data, auth=False)
        data = response.json()
        if response.status_code == 403:
            self.server.status = 'u'
            self.server.save(update_fields=['status'])
            return
        if response.status_code == 200:
            access_token = data.get('access_token')
            device_id = data.get('device_id')
            self.server.update_data({'access_token': access_token, 'device_id': device_id})
            self._to_cache(**{"access_token": access_token, "device_id": device_id})
            return access_token

    def join(self, room_id):
        response = self.api_call("POST", "/rooms/%s/join" % room_id, json={})
        if response.status_code == 200:
            return response.json().get('room_id')
