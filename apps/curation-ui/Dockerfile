# Built from the repository root as context (mirrors the service Dockerfiles):
#   docker build -f apps/curation-ui/Dockerfile -t sa-curation-ui .
# The gateway base URL is baked at build time (Vite), so the browser talks to the
# host-published gateway port. Override with --build-arg VITE_API_BASE_URL=...
FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /app
COPY apps/curation-ui/package.json apps/curation-ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/curation-ui/ ./
ARG VITE_API_BASE_URL=http://localhost:8080
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm build

FROM nginx:1.27-alpine
COPY apps/curation-ui/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
