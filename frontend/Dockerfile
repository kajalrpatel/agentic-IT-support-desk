FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM nginxinc/nginx-unprivileged:1.28-alpine
USER root
RUN apk add --no-cache jq
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.d/40-config.sh /docker-entrypoint.d/40-config.sh
RUN chmod +x /docker-entrypoint.d/40-config.sh && chown -R 101:101 /usr/share/nginx/html /etc/nginx/conf.d
USER 101
ENV BACKEND_ORIGIN=http://backend:8000 API_BASE="" OIDC_AUTHORITY="" OIDC_CLIENT_ID=""
EXPOSE 8080
