import requests
import os
import redis

rs = requests.Session()
rs.headers.update({'User-Agent': 'Matrixbot-dev-experimental/1.1 (+https://matrixstats.org)'})

redis_settings = {
    'db': 0
}

REDIS_SOCKET = os.environ.get("REDIS_SOCKET")
if REDIS_SOCKET:
    redis_settings['unix_socket_path'] = REDIS_SOCKET
else:
    redis_settings['host'] = os.environ.get("REDIS_HOST")
    redis_settings['port'] = os.environ.get("REDIS_PORT")

rds = redis.StrictRedis(**redis_settings)
