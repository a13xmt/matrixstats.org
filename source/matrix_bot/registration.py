import json
from matrix_bot.resources import rs
from matrix_bot import exception

from matrix_bot.utils import prettify

auth_flow_weights = {
    'm.login.password': 1,
    'm.login.recaptcha': 10,
    'm.login.oauth2': 500,
    'm.login.email.identity': 500,
    'm.login.token': 500,
    'm.login.dummy': 500,
}

# generic constants
HANDLER_NOT_IMPLEMENTED = "HANDLER_NOT_IMPLEMENTED"

# possible progress values for each stage
class PROGRESS:
    NEW = "NEW"
    USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED"
    USER_ACTION_COMPLETE = "USER_ACTION_COMPLETE"
    COMPLETE = "COMPLETE"

def continue_registration(server):
    """ Perform the next step in registration process"""
    chosen_flow = server.data.get("reg_chosen_flow", [])
    if chosen_flow:
        complete_next_stage(server)
    else:
        step_1(server)

def get_next_handler(server):
    """ Get the next handler to continue registration"""
    data = server.data
    if not "registration" in data:
        pass # FIXME

def get_best_flow(flows):
    """ Get the most easy flow for registration"""
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


def step_1(server):
    """ Prepare for registration """
    r = rs.post(
        server.api('/register'),
        json=base_registration_data
    )
    data = r.json()

    server.data['flows'] = data.get('flows', [])
    server.data['params'] = data.get('params', {})
    server.data['session'] = data.get('session', {})

    reg_data = {
        "bind_email": False,
        # FIXME
        "username": None,
        # FIXME
        "password": None,
        "initial_device_display_name": "MatrixBot",
    }
    server.data['reg_data'] = reg_data

    best_flow = get_best_flow(data.get('flows', []))
    server.data['reg_chosen_flow'] = best_flow
    server.data['reg_active_stage_index'] = 0
    server.data['reg_active_stage_progress'] = PROGRESS.NEW
    server.save(update_fields=['data'])

    complete_next_stage(server)


def complete_next_stage(server):
    auth_flow_handler = {
        'm.login.password': None,
        'm.login.recaptcha': recaptcha_handler,
        'm.login.oauth2': None,
        'm.login.email.identity': None,
        'm.login.token': None,
        'm.login.dummy': None,
    }
    flow = server.data['reg_chosen_flow']
    stage_index = server.data['reg_active_stage_index']
    stage = flow[stage_index]
    stage_handler = auth_flow_handler[stage]
    if not stage_handler:
        # FIXME fallback to another authentication flow
        # ...
        # FIXME
        server.data['reg_error'] = HANDLER_NOT_IMPLEMENTED
        server.save(update_fields=['data'])
        return
    result = stage_handler(server)
    print("Stage result: ", result)


def recaptcha_handler(server):

    # get current status of captcha-solving stage
    stage_progress = server.data['reg_active_stage_progress']

    # ensure captcha can be rendered
    if stage_progress == PROGRESS.NEW:
        public_key = server.data.get('params', {}).get("m.login.recaptcha", {}).get("public_key", None)
        if not public_key:
            raise exception.RecaptchaError()
        server.data['reg_active_stage_progress'] = PROGRESS.USER_ACTION_REQUIRED
        server.save(update_fields=['data'])
        raise exception.UserActionRequired()

    # can't do anything
    elif stage_progress == PROGRESS.USER_ACTION_REQUIRED:
        raise exception.UserActionRequired()

    # captcha solved
    elif stage_progress == PROGRESS.USER_ACTION_COMPLETE:
        captcha_response = server.data.get('reg_captcha_response', None)
        session = server.data.get('session', None)
        print(captcha_response, session)
        # reset stage if captcha not solved
        if not captcha_response:
            server.data['reg_active_stage_progress'] == PROGRESS.USER_ACTION_REQUIRED
            server.save(update_fields=['data'])
            raise exception.UserActionRequired()
        reg_data = server.data.get('reg_data', [])
        auth_data = {
            "type": "m.login.recaptcha",
            "response": captcha_response,
            "session": session,
        }
        reg_data['auth'] = auth_data
        r = rs.post(
            server.api('/register'),
            json=reg_data
        )
        data = r.json()
        err = data.get("errcode", None)
        if err:
            pass

        print(r.status_code, prettify(data))

    elif stage_progress == PROGRESS.COMPLETE:
        pass

