from matrix_bot import exception
from matrix_bot.registration.constants import PROGRESS

def recaptcha_handler(self):
    """ Performs ReCaptcha interactive challenge """

    def break_until_solved(self):
        """ Break registration process until captcha would be solved """
        self.server.update_data({'reg_active_stage_progress': PROGRESS.USER_ACTION_REQUIRED })
        raise exception.UserActionRequired()

    # Get current stage progress
    stage_progress = self.server.data['reg_active_stage_progress']

    # Ensure captcha can be rendered
    if stage_progress == PROGRESS.NEW:
        public_key = self.server.data.get('params', {}).get("m.login.recaptcha", {}).get("public_key", None)
        # Recaptcha wasn't presented in the server response
        if not public_key:
            raise exception.RecaptchaError()
        # Recaptcha should be solved by user
        break_until_solved(self)

    # Recaptcha should be solved by user
    elif stage_progress == PROGRESS.USER_ACTION_REQUIRED:
        raise exception.UserActionRequired()

    # Recaptcha was solved and should be validated
    elif stage_progress == PROGRESS.USER_ACTION_COMPLETE:
        captcha_response = self.server.data.get('reg_captcha_response', None)
        if not captcha_response:
            break_until_solved(self)

        # Validate the captcha on the homeserver
        session = self.server.data.get('session', None)
        reg_data = self.server.data.get('reg_data', [])
        auth_data = {
            "type": "m.login.recaptcha",
            "response": captcha_response,
            "session": session,
        }
        reg_data['auth'] = auth_data
        response = self.api_call(
            "POST",
            "/register",
            json=reg_data,
            auth=False
        )
        data = response.json()
        # Wrong captcha or timeout occurs, the new one should be solved
        if response.status_code == 401 and data.get("errcode") == "M_UNAUTHORIZED":
            break_until_solved(self)
        # At this point captcha most likely solved
        return response
