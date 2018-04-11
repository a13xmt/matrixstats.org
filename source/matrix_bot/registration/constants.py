# weights for preferred registration flow stages
AUTH_FLOW_WEIGHTS = {
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



