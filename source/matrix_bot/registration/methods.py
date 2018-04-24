import json
import os
from hashlib import md5
from requests.exceptions import RequestException
from matrix_bot.resources import rs
from matrix_bot import exception
from matrix_bot.utils import serialize, critical

from .constants import AUTH_FLOW_WEIGHTS, PROGRESS
from .handlers import recaptcha_handler, dummy_handler

STAGE_HANDLERS = {
    'm.login.password': None,
    'm.login.recaptcha': recaptcha_handler,
    'm.login.oauth2': None,
    'm.login.email.identity': None,
    'm.login.token': None,
    'm.login.dummy': dummy_handler,
}

def get_best_flow(flows):
    """ Get the most easy flow for registration """
    min_flow_score = 10000
    best_flow = None
    for flow in flows:
        flow_score = 0
        for item in flow['stages']:
            flow_score += AUTH_FLOW_WEIGHTS[item]
        if flow_score < min_flow_score:
            min_flow_score = flow_score
            best_flow = flow['stages']
    return best_flow


def set_registration_data(self, username=None, password=None):
    """ Set registration data for the new account """
    reg_data = {
        "bind_email": True,
        "username": username or self.server.login or os.environ.get("MATRIX_BOT_USERNAME"),
        "password": password or self.server.password or md5((os.environ.get("MATRIX_BOT_SEED") + self.server.hostname).encode()).hexdigest(),
        "initial_device_display_name": "MatrixBot",
    }
    self.server.update_data({'reg_data': reg_data})
    return reg_data


def continue_registration(self, username=None, password=None):
    """ Register a new account on the server, or continue an old registration """

    # If registration was already started, lets continue from the last point
    chosen_flow = self.server.data.get("reg_chosen_flow", [])
    if chosen_flow:
        return complete_remaining_stages(self)

    # If registration is not started yet, we need to prepare for it

    # Get or create registration data
    reg_data = self.server.data.get("reg_data") or set_registration_data(self, username, password)

    # Get registration metadata from the server
    r = self.api_call("POST", '/register', json=reg_data, auth=False)
    data = r.json()

    # There are few reasons that registration may fail
    # like M_USER_IN_USE and M_UNKNOWN server errors.
    # Registration should be finished by hand in this case.
    if data.get('errcode'):
        self.server.last_response_data = data
        self.server.last_resonse_code = r.status_code
        self.server.status = 'd'
        self.server.data = {}
        self.server.save(update_fields=['last_response_data', 'last_response_code', 'status', 'data'])
        return

    # Get best possible registration flow
    best_flow = get_best_flow(data.get('flows', []))

    # Save server response and chosen flow for futher usage
    self.server.update_data({
        'flows': data.get('flows', []),
        'params': data.get('params', {}),
        'session': data.get('session', {}),
        'reg_chosen_flow': best_flow,
        'reg_active_stage_index': 0,
        'reg_active_stage_progress': PROGRESS.NEW,
    })

    # Actual registration process here
    return complete_remaining_stages(self)


def complete_remaining_stages(self):
    """ Perform up to 5 registration stages, including repeats onon  failed ones """
    token = None
    try:
        for a in range(1,5):
            token = complete_next_stage(self)
            if token:
                break

    # this is not an error, just user input required
    # FIXME maybe send some notifications here later
    except exception.UserActionRequired as ex:
        return "CAPTCHA_REQUIRED"

    # this errors are acceptable, but should be logged
    except RequestException as ex:
        err = self.server.data.get('err_failed_requests', 0)
        self.server.update_data({'err_failed_requests': err + 1})
        return "REQUEST_FAILED"

    # this errors definetely should be logged and investigated
    except (exception.HandlerNotImplemented, exception.RecaptchaError) as ex:
        self.server.status = 'u'
        self.server.last_response_data = serialize(ex)
        self.server.save(update_fields=['status', 'last_response_data'])
        return "HANDLER_FAILED"

    # this errors are critical
    except Exception as ex:
        self.server.status = 'u'
        self.server.last_response_data = serialize(ex)
        self.server.save(update_fields=['status', 'last_response_data'])
        critical(ex)
        raise(ex)

    # all attempts were done, token is not guaranted
    return token


def complete_next_stage(self):
    """ Performs single registration stage """

    # Get chosen registration flow and its progress state
    flow = self.server.data['reg_chosen_flow']
    stage_index = self.server.data['reg_active_stage_index']
    stage = flow[stage_index]
    stage_handler = STAGE_HANDLERS[stage]
    if not stage_handler:
        raise exception.HandlerNotImplemented()

    # Perform corresponding stage
    response = stage_handler(self)
    data = response.json()

    # Save received data
    self.server.last_response_data = data
    self.server.last_response_code = response.status_code

    # If username was already taken, fallback to manual registration
    if response.status_code == 400 and data.get('errcode') == "M_USER_IN_USE":
        self.server.status = 'd'
        self.server.save(update_fields=['last_response_data', 'last_response_code', 'status'])
        raise exception.UserActionRequired()

    # If another error occurs it's hard to say what happened here,
    # so we try to finish all the planned stages, but prevent server for additional ones
    elif 'errcode' in data:
        self.server.status = 'd'

    # The current stage is complete, but we need to perform an additional one
    if response.status_code == 401 and not 'errcode' in data:
        self.server.update_data({
            'reg_active_stage_index':  self.server.data.get('reg_active_stage_index') + 1,
            'reg_active_stage_progress': PROGRESS.NEW
        })

    # If the stage was the last one, we can finish the registration
    if response.status_code == 200:
        finalize_registration(self, data)
        return data.get('access_token')
    # If its not, let's save the obtained data
    else:
        self.server.save(update_fields=['last_response_data', 'last_response_code', 'status'])


def finalize_registration(self, data):
    """ Save registration data to the database and remove unrequired fields """

    self.server.update_data({
        'access_token': data.get('access_token'),
        'home_server': data.get('home_server'),
        'user_id': data.get('user_id'),
        'device_id': data.get('device_id'),
    })

    self.server.status = 'r'
    self.server.login = self.server.data.get('reg_data', {}).get('username')
    self.server.password = self.server.data.get('reg_data', {}).get('password')
    self.server.save(update_fields=['status', 'login', 'password', 'last_response_data', 'last_response_code'])

    self.server.delete_data([
        'reg_active_stage_index', 'reg_active_stage_progress', 'reg_captcha_response',
        'reg_chosen_flow', 'reg_data', 'flows', 'params'])


def update_profile(self, visible_name=None, avatar_path=None):
    """ Update profile with displayname and avatar """
    if not visible_name:
        visible_name = os.environ.get("MATRIX_BOT_DISPLAYNAME", None)
    if not avatar_path:
        avatar_path = os.environ.get("MATRIX_BOT_AVATAR_PATH", None)
    try:
        f = open(avatar_path, 'rb')
    except FileNotFoundError:
        raise exception.ConfigurationError("MATRIX_BOT_AVATAR_PATH is incorrect")
    if not (visible_name or avatar_path):
        raise exception.ConfigurationError("MATRIX_BOT_DISPLAYNAME or MATRIX_BOT_AVATAR_PATH are not set")

    user_id = self.server.data.get('user_id')

    if not user_id:
        raise exception.AuthError("user_id is not set for this server")

    profile_data = {
        'displayname': None,
        'avatar_uri': None,
        'avatar_set': False
    }

    # set display name
    data = {'displayname': visible_name}
    r = self.api_call(
        "PUT",
        "/profile/%s/displayname" % user_id,
        json=data
    )
    if r.status_code == 200:
        profile_data['displayname'] = visible_name

    # upload avatar to media server
    r = self.api_call(
        "POST",
        "/upload?filename=matrixbot.png",
        suffix="/_matrix/media/r0",
        data=f.read(),
        headers={'Content-Type': 'image/png'}
    )
    content_uri = None
    if r.status_code == 200:
        content_uri = r.json().get('content_uri')
        profile_data['avatar_uri'] = content_uri

    # set avatar
    data = {'avatar_url': content_uri }
    r = self.api_call(
        "PUT",
        "/profile/%s/avatar_url" % user_id,
        json=data
    )
    if r.status_code == 200:
        profile_data['avatar_set'] = True

    self.server.update_data({'profile_data': profile_data})
    return profile_data


def upload_filter(self):
    """ Upload filter to homeserver for futher usage for /sync requests """
    filter_obj = {
        'room': {
            "timeline": {
                'limit': 500
            },
            "state": {
                'rooms': []
            }
        },
    }
    user_id = self.server.data.get('user_id')
    r = self.api_call(
        "POST",
        "/user/%s/filter" % user_id,
        json=filter_obj
    )
    data = r.json()
    if r.status_code == 200:
        filter_id = data.get('filter_id')
        self.server.update_data({'filter_id': filter_id})
        return filter_id

def verify_existence(self):
    """ Check the server existance and set the status accordingly"""
    response_data, response_code = None, None
    self.server.last_response_code = -1
    self.server.status = 'u'
    try:
        r = self.api_call(
            "GET",
            "",
            suffix="/_matrix/client/versions",
            auth=False
        )
        response_data = r.json()
        response_code = r.status_code
    except json.decoder.JSONDecodeError as ex:
        self.server.last_response_data = serialize(ex)
    except RequestException as ex:
        self.server.last_response_data = serialize(ex)
    except ex:
        self.server.last_response_data = serialize(ex)
        critical(ex)
    else:
        self.server.last_response_data = response_data
        self.server.last_response_code = response_code
        if response_code == 200 and "versions" in response_data:
            self.server.status = 'c'
        elif r.status_code >= 400:
            self.server.status = 'u'
        else:
            self.server.status = 'n'
    self.server.save(update_fields=['last_response_data', 'last_response_code', 'status'])
    return self.server.status

