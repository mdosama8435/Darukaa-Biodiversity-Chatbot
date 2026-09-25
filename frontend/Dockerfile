FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
ENV PORT=80

COPY --from=builder /app/dist /usr/share/nginx/html
# COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Lightweight container startup validation to verify rendered Nginx configuration
RUN printf '#!/bin/sh\nset -e\nnginx -t\n' > /docker-entrypoint.d/40-validate-config.sh && chmod +x /docker-entrypoint.d/40-validate-config.sh

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
