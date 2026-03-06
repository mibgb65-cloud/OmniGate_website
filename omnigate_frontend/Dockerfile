FROM node:22-alpine AS builder

WORKDIR /app

ARG VITE_API_BASE_URL=/api
ARG VITE_TASK_LOG_WS_URL=/ws/task-log

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_TASK_LOG_WS_URL=${VITE_TASK_LOG_WS_URL}

COPY package.json package-lock.json ./
RUN npm ci

COPY public ./public
COPY src ./src
COPY index.html jsconfig.json vite.config.js ./

RUN npm run build

FROM nginx:1.29-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
