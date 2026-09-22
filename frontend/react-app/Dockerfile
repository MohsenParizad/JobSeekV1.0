# Frontend image: builds the React app, then serves the static bundle with
# nginx. Build from the repo root (needs files outside frontend/react-app/
# in scope for a consistent build context with the backend image):
#
#   docker build -f frontend/react-app/Dockerfile \
#     --build-arg VITE_API_BASE_URL=http://localhost:8000 \
#     -t jobseek-frontend .
#
# VITE_API_BASE_URL is baked into the built JS at build time (Vite env vars
# are compile-time, not runtime) — pass the URL the browser will use to
# reach the backend, not a Docker-internal service name.

# mirror.gcr.io instead of docker.io: avoids Docker Hub's anonymous-pull
# rate limit (hit this repeatedly in CI/local testing).
FROM mirror.gcr.io/library/node:20-slim AS build
WORKDIR /app
COPY frontend/react-app/package.json frontend/react-app/package-lock.json ./
RUN npm ci
COPY frontend/react-app/ ./
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM mirror.gcr.io/library/nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/react-app/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
