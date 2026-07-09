# Runbook
# Service: {Service Name}
> Version: 1.0 | Date: {date}
> Scope: MVP+ only — skip for pilot
>
> **Living artifact** — `docs/runbook/local-setup.md` describes the whole
> service, not one feature. If it already exists, only add what this
> feature introduces (new Troubleshooting entries, new Environment
> Variables, new On-Call mappings) — Local Setup/Profiles/Common
> Operations/Rollback almost never change and should be left as-is.

---

## References

| Source | Sections / IDs Used |
|---|---|
| plan.summary.md | {sections/IDs referenced} |
| arch.summary.md | {sections/IDs referenced} |

## 1. Local Setup

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

## 2. Profiles

| Profile | Purpose | Dependencies |
|---|---|---|
| mock | Local dev / unit-test | All integrations mocked, H2/Testcontainers |
| test | CI pipeline | Testcontainers — real DB, mocked external systems |
| prod | Production | Real DB, real integrations |

---

## 3. Common Operations

| Task | Command |
|---|---|
| Run unit tests | `{test command}` |
| Run integration tests | `{integration test command}` |
| Check coverage | `{coverage command}` |
| Run DB migration | `{migration command}` |
| View logs | `docker-compose logs -f app` |
| Rebuild after change | `docker-compose up -d --build app` |

---

## 4. Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| {symptom} | {cause} | {fix} |
| Health check failing | DB not ready | `docker-compose ps` — wait for healthy, check logs |
| {integration} timeout in mock | Wrong profile active | Confirm `SPRING_PROFILES_ACTIVE=mock` |

---

## 5. Key Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| {VAR_NAME} | {purpose} | {example — no real secrets} |

---

## 6. Rollback

```bash
# Application rollback (previous image tag)
{rollback command, e.g. kubectl rollout undo deployment/{service}}

# DB migration rollback (if down-script exists)
{down-migration command}
```

If no down-migration exists for the latest version: {documented manual recovery steps}.

---

## 7. On-Call Quick Reference

| Alert | First Action | Escalation |
|---|---|---|
| {alert name} | {first responder action} | {who/when to escalate} |

---

## Approvals

| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
