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
        user_id = data.get('user_id')
        home_server = data.get('home_server')
        self.server.update_data({'access_token': access_token, 'device_id': device_id, 'user_id': user_id, 'home_server': home_server })
        self._to_cache(**{"access_token": access_token, "device_id": device_id})
        return access_token
