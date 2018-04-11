def dummy_handler(self):
    """ Performs basic registration stage """
    reg_data = self.server.data.get('reg_data', [])
    session = self.server.data.get('session', None)
    auth_data = {
        "type": "m.login.dummy",
        "session": session
    }
    reg_data['auth'] = auth_data
    return self.api_call(
        "POST",
        "/register",
        json=reg_data
    )
