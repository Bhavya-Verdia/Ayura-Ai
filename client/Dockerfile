# Build stage — Debian (not alpine) so Playwright's Chromium can run the
# prerender step. Final runtime image is still nginx:alpine (see below).
FROM node:20-bookworm-slim AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Chromium for the prerender (postbuild) step that snapshots public routes to
# static HTML for crawlers. Non-fatal: if install fails, prerender.mjs degrades
# gracefully and the SPA still renders client-side.
RUN npx playwright install --with-deps chromium || true

# Vite bakes VITE_* vars at build time — inject them via --build-arg
ARG VITE_API_URL=/api
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_GITHUB_CLIENT_ID
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID
ARG VITE_FIREBASE_MEASUREMENT_ID
ARG VITE_SENTRY_DSN

RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
