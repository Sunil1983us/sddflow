# Runbook
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Scope: MVP+ only — skip for pilot

---

## References
| Source | Sections / IDs Used |
|---|---|
| plan.summary.md | {sections/IDs referenced} |
| arch.summary.md | {sections/IDs referenced} |

## 1. Local Setup

```bash
git clone {repo}
cd {app}
cp .env.example .env          # fill values
npm install
npm run dev                    # local dev server (mock API by default)
```

**Health check:** App loads at `http://localhost:{port}/`, no console
errors, API client reaches mock/staging backend.

---

## 2. Build Profiles

| Profile | Purpose | Backend Target |
|---|---|---|
| mock | Local dev / unit-test | MSW / mock service worker — all API calls mocked |
| staging | QA / UAT | Staging backend (api-spec.md) |
| production | Production deploy | Production backend |

---

## 3. Common Operations

| Task | Command |
|---|---|
| Run unit tests | `{test command}` |
| Run component tests | `{component test command}` |
| Run E2E tests | `{e2e command, e.g. playwright test}` |
| Check coverage | `{coverage command}` |
| Build production bundle | `{build command, e.g. npm run build}` |
| Preview production build locally | `{preview command, e.g. npm run preview}` |
| Lint + type-check | `{lint/typecheck command}` |

---

## 4. Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| Blank page after deploy | Stale `index.html` referencing old asset hashes (CDN cache not purged) | Purge CDN cache for `index.html` (section 6) |
| Chunk-load error / "Loading chunk N failed" | User has stale `index.html` cached, or new deploy removed old chunk files | Force-reload guidance to users; ensure old build artifacts retained for at least one release cycle |
| CORS failures calling backend API | API base URL misconfigured for this environment, or backend CORS allowlist missing this origin | Confirm `VITE_API_BASE_URL` / runtime config for this environment; check backend CORS config |
| Third-party script outage (analytics/widget) | Third-party CDN down or SRI hash mismatch after their update | Confirm error boundary/resilience.md fallback degrades gracefully; check SRI hash if script blocked |
| {symptom} | {cause} | {fix} |

---

## 5. Key Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| {VAR_NAME} | {purpose} | {example — no real secrets} |

---

## 6. Rollback

### CDN Cache Invalidation / Purge
```bash
# Example: CloudFront
aws cloudfront create-invalidation \
  --distribution-id {DISTRIBUTION_ID} \
  --paths "/index.html" "/"

# Example: Netlify/Vercel — trigger a redeploy of the previous build,
# or use the platform's instant-rollback UI/CLI
```

### Static Deploy Rollback (previous build artifact)
```bash
# Re-deploy the previous build artifact to the CDN/object storage
# (artifact retained from the prior release per constitution OPS-7)
{deploy command} --artifact {previous-build-id}

# Then re-run the cache invalidation above for index.html
```

If hashed assets from the previous build were deleted, restore them
from CI build artifacts before invalidating — `index.html` must never
reference a missing chunk.

---

## 7. On-Call Quick Reference

| Alert | First Action | Escalation |
|---|---|---|
| RUM error-rate spike (Sentry/Datadog RUM) | Check investigation.md INV-NNN playbook; correlate with latest deploy timestamp | devops_sre (roles.yml) → tech_lead |
| Blank page / chunk-load errors reported | Purge CDN cache for `index.html` (section 6); if unresolved, roll back static deploy | devops_sre (roles.yml) |
| CORS failures spike | Confirm environment API base URL + backend CORS allowlist | tech_lead → backend on-call |
| Third-party script outage | Confirm resilience.md degraded-mode fallback active; disable feature flag for affected widget if needed | tech_lead |
| Core Web Vitals regression (LCP/CLS/INP) | Check latest deploy for bundle-size regression; compare Lighthouse CI report | tech_lead → architect |

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
