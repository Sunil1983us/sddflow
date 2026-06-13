# Runbook
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Input: plan.summary.md + arch.summary.md
> Scope: MVP+ only — skip for pilot
> Covers: Backend service ops (§1-7) AND Frontend ops (§1a-7a)

---

## 1. Local Setup — Backend

```bash
git clone {repo}
cd {service}
cp .env.example .env          # fill values
docker-compose up -d           # start dependencies
{build command}                # e.g. mvn clean install
{run command}                  # e.g. mvn spring-boot:run -Dspring-boot.run.profiles=mock
```

**Health check:** `GET /actuator/health` → expect `{"status":"UP"}`

---

## 1a. Local Setup — Frontend

```bash
cd {frontend-app}
cp .env.example .env.local     # fill values (API base URL, etc.)
npm ci                         # install dependencies
npm run dev                     # start dev server with hot reload
```

**Health check:** open `http://localhost:{port}` → app shell renders, no
console errors

---

## 2. Profiles

| Profile | Purpose | Dependencies |
|---|---|---|
| mock | Local dev / unit-test | All integrations mocked, H2/Testcontainers |
| test | CI pipeline | Testcontainers — real DB, mocked external systems |
| prod | Production | Real DB, real integrations |

---

## 2a. Frontend Environments

| Environment | API Base URL | Purpose |
|---|---|---|
| local | `http://localhost:{backend-port}/api/v1` | Local dev against local/mock backend |
| staging | `{staging-api-url}` | Pre-production verification |
| prod | `{prod-api-url}` | Production |

---

## 3. Common Operations — Backend

| Task | Command |
|---|---|
| Run unit tests | `{test command}` |
| Run integration tests | `{integration test command}` |
| Check coverage | `{coverage command}` |
| Run DB migration | `{migration command}` |
| View logs | `docker-compose logs -f app` |
| Rebuild after change | `docker-compose up -d --build app` |

---

## 3a. Common Operations — Frontend

| Task | Command |
|---|---|
| Run unit tests | `npm test` |
| Run component tests | `{component test command}` |
| Run E2E tests | `{e2e command, e.g. npx playwright test}` |
| Check coverage | `npm test -- --coverage` |
| Lint | `npm run lint` |
| Production build | `npm run build` |
| Preview production build | `npm run preview` |
| View frontend container logs | `docker-compose logs -f frontend` |
| Rebuild after change | `docker-compose up -d --build frontend` |

---

## 4. Troubleshooting — Backend

| Symptom | Likely Cause | Resolution |
|---|---|---|
| {symptom} | {cause} | {fix} |
| Health check failing | DB not ready | `docker-compose ps` — wait for healthy, check logs |
| {integration} timeout in mock | Wrong profile active | Confirm `SPRING_PROFILES_ACTIVE=mock` |

---

## 4a. Troubleshooting — Frontend

| Symptom | Likely Cause | Resolution |
|---|---|---|
| Blank screen / app shell only | API base URL misconfigured | Check `.env.local` / build-time env var |
| CORS error in browser console | Backend CORS policy missing origin | Update backend CORS config for frontend origin |
| Stale content after deploy | CDN cache not invalidated | Run CDN invalidation (§6a) |
| {component} fails to render | Missing/changed prop from API response | Check api-spec.md vs component-spec.md contract |

---

## 5. Key Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| {VAR_NAME} | {purpose} | {example — no real secrets} |
| {FRONTEND_API_BASE_URL} | Frontend → backend API base URL | `https://api.example.com/api/v1` |

---

## 6. Rollback — Backend

```bash
# Application rollback (previous image tag)
{rollback command, e.g. kubectl rollout undo deployment/{service}}

# DB migration rollback (if down-script exists)
{down-migration command}
```

If no down-migration exists for the latest version: {documented manual recovery steps}.

---

## 6a. Rollback — Frontend

```bash
# Static asset rollback — redeploy previous build artifact
{rollback command, e.g. revert to previous CDN/static-host deployment}

# CDN cache invalidation after rollback
{cdn invalidation command, e.g. aws cloudfront create-invalidation --distribution-id {id} --paths "/*"}
```

If the frontend is served as static resources by the backend service
(see docker-config-template.md), a frontend rollback requires
redeploying the previous backend image tag (§6) — the two are coupled.

---

## 7. On-Call Quick Reference — Backend

| Alert | First Action | Escalation |
|---|---|---|
| {alert name} | {first responder action} | {who/when to escalate} |

---

## 7a. On-Call Quick Reference — Frontend

| Alert | First Action | Escalation |
|---|---|---|
| RUM error rate spike | Check error tracking dashboard for stack trace + affected screen/component | Escalate to frontend on-call if traced to recent deploy |
| Core Web Vital regression (LCP/INP/CLS) | Check recent frontend deploy + CDN status | Escalate to frontend on-call |

---
*Generated from: plan.summary.md + arch.summary.md*
