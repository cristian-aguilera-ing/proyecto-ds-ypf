FROM nginx:1.29-alpine
COPY presentacion/ /usr/share/nginx/html/
# Sin caché heurística (cada cambio se ve al recargar) y con el proxy del control remoto (/control-api/)
COPY docker/presentacion.nginx.conf /etc/nginx/conf.d/default.conf
HEALTHCHECK --interval=15s --timeout=3s CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
