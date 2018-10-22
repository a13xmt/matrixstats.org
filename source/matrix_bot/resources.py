import eventlet
requests = eventlet.import_patched('requests')
redis = eventlet.import_patched('redis')
import os

rs = requests.Session()

version = "prod" if "prod" in os.environ.get("DJANGO_SETTINGS_MODULE", "") else "dev"
if version == "prod":
    rs.headers.update({'User-Agent': 'Matrixbot/1.1 (+https://matrixstats.org/bot/)'})
else:
    rs.headers.update({'User-Agent': 'Matrixbot-dev-experimental/1.1 (+https://matrixstats.org/bot/)'})

redis_settings = {
}

REDIS_SOCKET = os.environ.get("REDIS_SOCKET")
if REDIS_SOCKET:
    redis_settings['unix_socket_path'] = REDIS_SOCKET
else:
    redis_settings['host'] = os.environ.get("REDIS_HOST")
    redis_settings['port'] = os.environ.get("REDIS_PORT")

rds = redis.StrictRedis(db=0, **redis_settings)
rds_alias = redis.StrictRedis(db=1, **redis_settings)
rds_sync = redis.StrictRedis(db=4, socket_timeout=3600, **redis_settings)
