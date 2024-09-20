FROM jwilder/nginx-proxy:0.9

COPY ./compose/production/nginx/vhost.d/default /etc/nginx/vhost.d/default
COPY ./compose/production/nginx/nginx.conf /etc/nginx/conf.d/nginx.conf
RUN echo "client_max_body_size 100m;" >> /etc/nginx/conf.d/nginx.conf
RUN echo "client_body_buffer_size 100m;" >> /etc/nginx/conf.d/nginx.conf