FROM nginx:stable
RUN rm /etc/nginx/conf.d/default.conf
RUN apt-get update && apt-get install -y certbot
RUN mkdir -p /certbot/challenge/.well-known /certbot/certs
RUN chown www-data:www-data /certbot -R
ADD conf.d/ /etc/nginx/conf.d
