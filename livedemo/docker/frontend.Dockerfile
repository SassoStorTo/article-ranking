FROM node:20-alpine AS builder
WORKDIR /app
COPY livedemo/frontend/package.json livedemo/frontend/package-lock.json* ./
RUN npm install
COPY livedemo/frontend ./
RUN npm run build

FROM nginx:1.27-alpine
COPY livedemo/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
