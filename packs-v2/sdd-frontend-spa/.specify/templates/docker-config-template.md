# Docker Configuration Templates
# Static SPA hosting — multi-stage build (build app → serve with nginx)

---

## Dockerfile — Multi-Stage Build

```dockerfile
# Multi-stage build — no Node/build tooling in the final image

# Stage 1 — Build static assets
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Build-time env vars (NOT secrets) — injected by CI, never hardcoded
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Stage 2 — Serve static assets with nginx
FROM nginx:1.27-alpine AS runtime
WORKDIR /usr/share/nginx/html

# Remove default nginx static content
RUN rm -rf ./*

# Copy built static assets from build stage (dist/ for Vite, build/ for CRA)
COPY --from=build /app/dist .

# Custom nginx config — SPA fallback + compression + cache headers + CSP
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Non-root: nginx-alpine already runs worker processes as `nginx` user;
# ensure writable dirs are owned correctly for non-root operation
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid
USER nginx

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8080/ || exit 1

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

---

## docker/nginx.conf — SPA Static Serving

```nginx
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # ── Gzip / Brotli compression ──────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/javascript
        application/json
        application/manifest+json
        image/svg+xml
        font/woff2;
    # If the nginx build includes ngx_brotli, enable brotli the same way:
    # brotli on;
    # brotli_comp_level 5;
    # brotli_types <same list as gzip_types above>;

    # ── Security headers (security-design.md §1) ───────────────
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    # CSP — tune connect-src/script-src per third-party scripts in use;
    # avoid 'unsafe-inline' for script-src wherever possible (constitution
    # OPS-7). frame-ancestors 'none' reinforces clickjacking protection
    # alongside X-Frame-Options above.
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ${API_BASE_URL}; frame-ancestors 'none'; base-uri 'self'" always;

    # ── Cache-Control: hashed assets vs index.html ──────────────
    # Hashed build assets (e.g. main.abc123.js) — safe to cache forever,
    # filename changes on every release.
    location ~* \.(?:js|css|woff2?|png|jpg|jpeg|gif|svg|ico)$ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }

    # index.html — never cache, always fetch latest so SPA picks up the
    # newest asset hashes after a deploy.
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        try_files $uri =404;
    }

    # ── SPA fallback routing ─────────────────────────────────────
    # All non-asset routes (client-side router paths) fall back to
    # index.html so the SPA router resolves the path.
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## .env.example

```bash
# Build-time configuration (injected by CI — never committed with real values)
VITE_API_BASE_URL=https://api.staging.example.com

# Runtime config alternative (if using /config.json fetched at boot
# instead of build-time env vars — see constitution.md OPS-7 "Env config")
# CONFIG_JSON_PATH=/config.json
```

---

## docker-compose.yml — Local Preview

```yaml
version: "3.9"

services:

  # ── SPA (built + served by nginx) ──────────────────────────
  web:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: ${VITE_API_BASE_URL:-http://localhost:8081}
    container_name: ${APP_NAME:-spa}-web
    ports:
      - "${WEB_PORT:-8080}:8080"
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s
    networks:
      - app-network
    restart: unless-stopped

  # ── Mock backend API (MSW/json-server) — Remove if not used ─
  mock-api:
    image: node:20-alpine
    container_name: ${APP_NAME:-spa}-mock-api
    working_dir: /app
    volumes:
      - ./mocks:/app
    command: ["npx", "json-server", "--watch", "db.json", "--port", "8081", "--host", "0.0.0.0"]
    ports:
      - "${MOCK_API_PORT:-8081}:8081"
    networks:
      - app-network
    restart: unless-stopped

# ── Networks ──────────────────────────────────────────────
networks:
  app-network:
    driver: bridge
```

---

## Useful Commands

```bash
# Build the production image
docker build -t ${APP_NAME:-spa}:local --build-arg VITE_API_BASE_URL=https://api.staging.example.com .

# Run locally
docker run --rm -p 8080:8080 ${APP_NAME:-spa}:local

# Start preview stack (SPA + mock API)
docker-compose up -d --build

# View logs
docker-compose logs -f web

# Check health
curl -I http://localhost:8080/

# Verify SPA fallback (deep link should return index.html, not 404)
curl -I http://localhost:8080/some/deep/route

# Verify cache headers on a hashed asset
curl -I http://localhost:8080/assets/main.$(ls dist/assets | grep -m1 '\.js$' | sed 's/.*\.\(.*\)\.js/\1/').js 2>/dev/null || true

# Stop and remove
docker-compose down
```

---

## Constitution Reference
These templates implement the rules in constitution.md Part 1 →
"## Containerization & Hosting (OPS-7)" table. That table is the source
of truth — do not duplicate or diverge from it here. Key rules it
covers: static build output, nginx/CDN serving, SPA fallback to
`/index.html`, runtime/build-time env config (no secrets in the bundle),
CSP headers, Cache-Control split between `index.html` and hashed assets,
SRI on third-party scripts, and a serving-container health check.
