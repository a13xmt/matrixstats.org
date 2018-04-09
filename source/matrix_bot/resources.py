import requests
import os
import redis

rs = requests.Session()
rs.headers.update({'User-Agent': 'Matrixbot-dev-experimental/1.1 (+https://matrixstats.org)'})

rds = redis.StrictRedis(
    host=os.environ.get("REDIS_HOST"),
    port=os.environ.get("REDIS_PORT", 6379),
    db=0,
)
