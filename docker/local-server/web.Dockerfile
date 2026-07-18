FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app

RUN corepack enable

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ .
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm build

FROM caddy:2-alpine

COPY docker/local-server/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend-build /app/dist /srv
