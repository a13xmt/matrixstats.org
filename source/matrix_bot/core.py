import requests
import json
import django
import os
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix_stats.settings.dev")
django.setup()

from matrix_bot.utils import serialize, critical, prettify
from room_stats.models import Server
from matrix_bot.resources import rs, rds

from matrix_bot.login import login
from matrix_bot.registration import continue_registration, update_profile, upload_filter, verify_existence, set_displayname
from matrix_bot.join import join, leave, get_banned_rooms, get_joined_rooms, fetch_joined_rooms, update_banned_rooms, get_rooms_to_join
from matrix_bot.sync import sync, get_rooms, save_rooms
from matrix_bot.statistics import get_unique_messages, get_unique_senders, get_active_rooms, save_daily_stats
from matrix_bot.reply import reply, mark_as_read

def handle_server_instance(server_id):
    """ Check the server instance for uncompleted registration
    and finish it if neccessary"""
    server = Server.objects.get(pk=server_id)
    if server.status == 'a':
        verify_server_existence(server)
    if server.status == 'c':
        continue_registration(server)


class MatrixHomeserver():
    def __init__(self, server_id):
        self.server = Server.objects.get(pk=server_id)
        self.rs = rs
        self.rds = rds
        self._in_transaction = False

    def _prefixed(self, key):
        """ Expand redis key with server name """
        return "%s__%s" % (self.server.hostname, key)

    def _open_transaction(self):
        """ Open redis pipeline """
        self._in_transaction = True
        self._transaction = self.rds.pipeline()

    def _commit_transaction(self):
        """ Execute redis pipeline """
        self._in_transaction = False
        self._transaction.execute()

    def _scan_keys(self, glob='*'):
        """ Search redis keys by pattern """
        n = 0
        keys = []
        while(True):
            n, k = self.rds.scan(n, match=self._prefixed(glob))
            keys.extend(k)
            if n == 0:
                break
        return keys

    def _cache(self, glob='*', expand=False):
        """ Display keys (and values) by pattern (debug only) """
        keys = self.rds.keys(self._prefixed(glob))
        if not expand:
            keys = [k.decode() for k in keys]
            keys.sort()
            print(prettify(keys))
            return
        result = {}
        for key in keys:
            result[key.decode()] = [
                self.rds.get(key).decode(),
                self.rds.ttl(key)
            ]
        print(prettify(result))

    def _from_cache(self, key):
        """ Get server-related data from redis """
        return self.rds.get(self._prefixed(key))

    def _to_cache(self, key=None, value=None, expire=None, **kwargs):
        """ Set server-related data to redis """
        target = self._transaction if self._in_transaction else self.rds
        if key and value:
            return target.set(self._prefixed(key), value, ex=expire)
        else:
            result = []
            for key in kwargs:
                result.append(target.set(self._prefixed(key), kwargs[key], ex=expire))
            return result

    def _to_set(self, key, value, expire=None):
        target = self._transaction if self._in_transaction else self.rds
        target.sadd(self._prefixed(key), value)
        if expire:
            target.expire(self._prefixed(key), expire)

    def _count_set(self, key):
        return self.rds.scard(key)

    def _get_access_token(self):
        """ Get access_token or obtain it if possible """
        access_token = (
            self.server.data.get('access_token') or
            self._from_cache('access_token') or
            self.login()
        )
        return str(access_token)

    def _log_request_meta(self, success=True, code=None, path=None):
        date = datetime.now()
        day = date.strftime("%Y-%m-%d")
        if success:
            success_counter_key = self._prefixed("sc__%s" % day)
            self.rds.incr(success_counter_key)
            self.rds.expire(success_counter_key, 60 * 60 * 72)
        else:
            err_counter_key = self._prefixed("ec__%s" % day)
            err_details_key = self._prefixed("ed__%s" % day)
            err_details_data = "%s_%s_%s" % (
                code,
                path,
                date.strftime("%H:%M:%S")
            )
            self.rds.incr(err_counter_key)
            self.rds.expire(err_counter_key, 60 * 60 * 72)
            self.rds.rpush(err_details_key, err_details_data)
            self.rds.expire(err_details_key, 60 * 60 * 72)


    def api_call(self, method, path, data=None, json=None, suffix=None, params=None, auth=True, headers=None, forward_error_codes=None):
        """ Performs an API call to homeserver.
        Last response data can be cached, if required.
        """
        suffix = suffix or "/_matrix/client/r0"
        headers = headers or {}
        forward_error_codes = forward_error_codes or []
        url = "https://%s%s%s" % (self.server.hostname, suffix, path)
        if auth:
            access_token = self._get_access_token()
            headers['Authorization'] = 'Bearer %s' % access_token
        response = None
        try:
            response = rs.request(method=method, url=url, data=data, json=json, params=params, headers=headers)
        except requests.exceptions.ConnectionError as ex:
            self._log_request_meta(success=False, code=0, path=path.split('?')[0])
            raise ex
        if response.status_code in forward_error_codes:
            pass
        elif response.status_code != 200 and path != "/register":
            self._log_request_meta(success=False, code=response.status_code, path=path.split('?')[0])
            raise ConnectionError("Server responds with bad code %s" % response.status_code)
        self._log_request_meta(success=True)
        return response

    def login(self):
        return login(self)

    def register(self, username=None, password=None):
        return continue_registration(self, username, password)

    def finalize_manual_registration(self):
        self.login()
        return self.update_profile(), self.upload_filter()

    def verify_existence(self):
        return verify_existence(self)

    def update_profile(self, visible_name=None, avatar_path=None):
        return update_profile(self, visible_name, avatar_path)

    def set_displayname(self, name):
        return set_displayname(self, name)

    def upload_filter(self):
        return upload_filter(self)

    def join(self, room_id):
        return join(self, room_id)

    def leave(self, room_id):
        return leave(self, room_id)

    def reply(self, room_id, msg):
        return reply(self, room_id, msg)

    def mark_as_read(self, room_id, event_id):
        return mark_as_read(self, room_id, event_id)

    def sync(self, filter_obj=None, since=None, fast_forward=False):
        return sync(self, filter_obj, since, fast_forward)

    def get_unique_messages(self, room_id, datestr):
        return get_unique_messages(self, room_id, datestr)

    def get_unique_senders(self, room_id, datestr):
        return get_unique_senders(self, room_id, datestr)

    def get_active_rooms(self, datestr):
        return get_active_rooms(self, datestr)

    def save_daily_stats(self, room_id, date):
        return save_daily_stats(self, room_id, date)

    def get_rooms(self):
        return get_rooms(self)

    def save_rooms(self, rooms):
        return save_rooms(self, rooms)

    def joined_rooms(self):
        r = self.api_call("GET", "/joined_rooms")
        return r.json().get('joined_rooms', []) if r.status_code == 200 else r.content

    def get_banned_rooms(self):
        return get_banned_rooms(self)

    def get_joined_rooms(self):
        return get_joined_rooms(self)

    def fetch_joined_rooms(self):
        return fetch_joined_rooms(self)

    def update_banned_rooms(self):
        return update_banned_rooms(self)

    def get_rooms_to_join(self):
        return get_rooms_to_join(self)

