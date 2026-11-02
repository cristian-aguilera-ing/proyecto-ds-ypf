FROM nginx:1.29-alpine
COPY presentacion/ /usr/share/nginx/html/
# Sin caché heurística: cada cambio del guion o de las escenas se ve al recargar
RUN sed -i 's|location / {|location / {\n        add_header Cache-Control "no-cache";|' /etc/nginx/conf.d/default.conf
HEALTHCHECK --interval=15s --timeout=3s CMD wget -qO- http://localhost/ >/dev/null || exit 1
