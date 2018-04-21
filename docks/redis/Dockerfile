FROM redis
COPY redis.conf /usr/local/etc/redis/redis.conf
RUN mkdir /var/run/sockets
RUN chmod 777 /var/run/sockets
CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]