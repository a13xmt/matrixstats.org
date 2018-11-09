from requests.exceptions import ConnectionError

from matrix_bot.resources import rs

def get_server_version(hostname):
    schemes = ['https', 'http']
    for scheme in schemes:
        path = "%s://%s/_matrix/client/versions" % (scheme, hostname)
        try:
            response = rs.get(path, timeout=10)
        except (ConnectionError,) as ex:
            pass
        else:
            try:
                return response.json()['versions']
            except:
                return False
    return False

