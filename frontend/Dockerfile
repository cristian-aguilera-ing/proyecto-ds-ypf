# Frontend estatico servido por nginx; reenvia /api/ al backend
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html estilos.css app.js /usr/share/nginx/html/

EXPOSE 80
