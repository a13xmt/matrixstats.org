import json
import os
from hashlib import md5
from requests.exceptions import RequestException
from matrix_bot.resources import rs
from matrix_bot import exception

from matrix_bot.utils import serialize, critical

# weights for preferred registration flow stages
auth_flow_weights = {
    'm.login.password': 5,
    'm.login.recaptcha': 10,
    'm.login.oauth2': 500,
    'm.login.email.identity': 500,
    'm.login.token': 500,
    'm.login.dummy': 1,
}

# possible progress values for each stage
class PROGRESS:
    NEW = "NEW"
    USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED"
    USER_ACTION_COMPLETE = "USER_ACTION_COMPLETE"
    COMPLETE = "COMPLETE"


def get_best_flow(flows):
    """ Get the most easy flow for registration """
    min_flow_score = 10000
    best_flow = None
    for flow in flows:
        flow_score = 0
        for item in flow['stages']:
            flow_score += auth_flow_weights[item]
        if flow_score < min_flow_score:
            min_flow_score = flow_score
            best_flow = flow['stages']
    return best_flow


def set_registration_data(server):
    """ Set registration data for the new account """
    reg_data = {
        "bind_email": True,
        "username": os.environ.get("MATRIX_BOT_USERNAME"),
        "password": md5((os.environ.get("MATRIX_BOT_SEED") + server.hostname).encode()).hexdigest(),
        "initial_device_display_name": "MatrixBot",
    }
    server.update_data({'reg_data': reg_data})
    return reg_data


def continue_registration(server):
    """ Register a new account on the server, or continue an old registration """

    # If registration was already started, lets continue from the last point
    chosen_flow = server.data.get("reg_chosen_flow", [])
    if chosen_flow:
        return complete_remaining_stages(server)

    # If registration is not started yet, we need to prepare for it

    # Get or create registration data
    reg_data = server.data.get("reg_data") or set_registration_data(server)

    # Get registration metadata from the server
    r = rs.post(
        server.api('/register'),
        json=reg_data
    )
    data = r.json()

    # There are few reasons that registration may fail
    # like M_USER_IN_USE and M_UNKNOWN server errors.
    # Registration should be finished by hand in this case.
    if data.get('errcode'):
        server.last_response_data = data
        server.last_resonse_code = r.status_code
        server.status = 'd'
        server.data = {}
        server.save(update_fields=['last_response_data', 'last_response_code', 'status', 'data'])
        return

    # Get best possible registration flow
    best_flow = get_best_flow(data.get('flows', []))

    # Save server response and chosen flow for futher usage
    server.update_data({
        'flows': data.get('flows', []),
        'params': data.get('params', {}),
        'session': data.get('session', {}),
        'reg_chosen_flow': best_flow,
        'reg_active_stage_index': 0,
        'reg_active_stage_progress': PROGRESS.NEW,
    })

    # Actual registration process here
    return complete_remaining_stages(server)


def complete_remaining_stages(server):
    """ Perform up to 5 registration stages, including repeats onon  failed ones """
    token = None
    try:
        for a in range(1,5):
            token = complete_next_stage(server)
            if token:
                break

    # this is not an error, just user input required
    # FIXME maybe send some notifications here later
    except exception.UserActionRequired as ex:
        pass

    # this errors are acceptable, but should be logged
    except RequestException as ex:
        err = server.data.get('err_failed_requests', 0)
        server.update_data({'err_failed_requests': err + 1})

    # this errors definetely should be logged and investigated
    except (exception.HandlerNotImplemented, exception.RecaptchaError) as ex:
        server.status = 'u'
        server.last_response_data = serialize(ex)
        server.save(update_fields=['status', 'last_response_data'])

    # this errors are critical
    except Exception as ex:
        server.status = 'u'
        server.last_response_data = serialize(ex)
        server.save(update_fields=['status', 'last_response_data'])
        critical(ex)
        raise(ex)

    # all attempts were done, token is not guaranted
    return token


def complete_next_stage(server):
    """ Performs single registration stage """

    stage_handlers = {
        'm.login.password': None,
        'm.login.recaptcha': recaptcha_handler,
        'm.login.oauth2': None,
        'm.login.email.identity': None,
        'm.login.token': None,
        'm.login.dummy': dummy_handler,
    }

    # Get chosen registration flow and its progress state
    flow = server.data['reg_chosen_flow']
    stage_index = server.data['reg_active_stage_index']
    stage = flow[stage_index]
    stage_handler = stage_handlers[stage]
    if not stage_handler:
        raise exception.HandlerNotImplemented()

    # Perform corresponding stage
    response = stage_handler(server)
    data = response.json()

    # Save received data
    server.last_response_data = data
    server.last_response_code = response.status_code

    # If username was already taken, fallback to manual registration
    if response.status_code == 400 and data.get('errcode') == "M_USER_IN_USE":
        server.status = 'd'
        server.save(update_fields=['last_response_data', 'last_response_code', 'status'])
        raise exception.UserActionRequired()

    # If another error occurs it's hard to say what happened here,
    # so we try to finish all the planned stages, but prevent server for additional ones
    elif 'errcode' in data:
        server.status = 'd'

    # The current stage is complete, but we need to perform an additional one
    if response.status_code == 401 and not 'errcode' in data:
        server.update_data({
            'reg_active_stage_index':  server.data.get('reg_active_stage_index') + 1,
            'reg_active_stage_progress': PROGRESS.NEW
        })

    # If the stage was the last one, we can finish the registration
    if response.status_code == 200:
        finalize_registration(server, data)
        return data.get('access_token')
    # If its not, let's save the obtained data
    else:
        server.save(update_fields=['last_response_data', 'last_response_code', 'status'])


def finalize_registration(server, data):
    """ Save registration data to the database and remove unrequired fields """

    server.update_data({
        'access_token': data.get('access_token'),
        'home_server': data.get('home_server'),
        'user_id': data.get('user_id'),
        'device_id': data.get('device_id'),
    })

    server.status = 'r'
    server.login = server.data.get('reg_data', {}).get('username')
    server.password = server.data.get('reg_data', {}).get('password')
    server.save(update_fields=['status', 'login', 'password', 'last_response_data', 'last_response_code'])

    server.delete_data([
        'reg_active_stage_index', 'reg_active_stage_progress', 'reg_captcha_response',
        'reg_chosen_flow', 'reg_data', 'flows', 'params'])


def recaptcha_handler(server):
    """ Performs ReCaptcha interactive challenge """

    def break_until_solved(server):
        """ Break registration process until captcha would be solved """
        server.update_data({'reg_active_stage_progress': PROGRESS.USER_ACTION_REQUIRED })
        raise exception.UserActionRequired()

    # Get current stage progress
    stage_progress = server.data['reg_active_stage_progress']

    # Ensure captcha can be rendered
    if stage_progress == PROGRESS.NEW:
        public_key = server.data.get('params', {}).get("m.login.recaptcha", {}).get("public_key", None)
        # Recaptcha wasn't presented in the server response
        if not public_key:
            raise exception.RecaptchaError()
        # Recaptcha should be solved by user
        break_until_solved(server)

    # Recaptcha should be solved by user
    elif stage_progress == PROGRESS.USER_ACTION_REQUIRED:
        raise exception.UserActionRequired()

    # Recaptcha was solved and should be validated
    elif stage_progress == PROGRESS.USER_ACTION_COMPLETE:
        captcha_response = server.data.get('reg_captcha_response', None)
        if not captcha_response:
            break_until_solved(server)

        # Validate the captcha on the homeserver
        session = server.data.get('session', None)
        reg_data = server.data.get('reg_data', [])
        auth_data = {
            "type": "m.login.recaptcha",
            "response": captcha_response,
            "session": session,
        }
        reg_data['auth'] = auth_data
        response = rs.post(
            server.api('/register'),
            json=reg_data
        )
        data = response.json()
        # Wrong captcha or timeout occurs, the new one should be solved
        if response.status_code == 401 and data.get("errcode") == "M_UNAUTHORIZED":
            break_until_solved(server)
        # At this point captcha most likely solved
        return response


def dummy_handler(server):
    """ Performs basic registration stage """
    reg_data = server.data.get('reg_data', [])
    session = server.data.get('session', None)
    auth_data = {
        "type": "m.login.dummy",
        "session": session
    }
    reg_data['auth'] = auth_data
    return rs.post(
        server.api('/register'),
        json=reg_data
    )

def update_profile(server, displayname=None, avatar_path=None):
    """ Update profile with displayname and avatar """
    if not displayname:
        displayname = os.environ.get("MATRIX_BOT_DISPLAYNAME", None)
    if not avatar_path:
        avatar_path = os.environ.get("MATRIX_BOT_AVATAR_PATH", None)
    try:
        f = open(avatar_path, 'rb')
    except FileNotFoundError:
        raise exception.ConfigurationError("MATRIX_BOT_AVATAR_PATH is incorrect")
    if not (displayname or avatar_path):
        raise exception.ConfigurationError("MATRIX_BOT_DISPLAYNAME or MATRIX_BOT_AVATAR_PATH are not set")

    access_token = server.data.get('access_token')
    user_id = server.data.get('user_id')

    if not (access_token or user_id):
        raise exception.AuthError("access_token or user_id not found for this server")

    profile_data = {
        'displayname': None,
        'avatar_uri': None,
        'avatar_set': False
    }

    # set display name
    data = {'displayname': displayname}
    r = rs.put(
        server.api("/profile/%s/displayname" % user_id),
        json=data,
        headers={'Authorization': 'Bearer %s' % access_token }
    )
    if r.status_code == 200:
        profile_data['displayname'] = displayname

    # upload avatar to media server
    r = rs.post(
        server.api("/upload?filename=matrixbot.png", "/_matrix/media/r0"),
        data=f.read(),
        headers={
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/json'
        }
    )
    content_uri = None
    if r.status_code == 200:
        content_uri = r.json().get('content_uri')
        profile_data['avatar_uri'] = content_uri

    # set avatar
    data = {'avatar_url': content_uri }
    r = rs.put(
        server.api('/profile/%s/avatar_url' % user_id),
        json=data,
        headers={'Authorization': 'Bearer %s' % access_token }
    )
    if r.status_code == 200:
        profile_data['avatar_set'] = True

    server.update_data({'profile_data': profile_data})


