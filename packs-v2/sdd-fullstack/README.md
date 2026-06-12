# SDD Full Stack Pack
## Backend + Frontend Together

---

## What This Pack Is For
Full system development — backend API + frontend UI.
Backend: Java/Spring Boot · Node/Express · Python/FastAPI
Frontend: React · Vue · Next.js · Nuxt
Deploy: Docker · Kubernetes

---

## How It Works — 3 Steps

### 1. Write your context (20-40 min)
Include BOTH layers:
- Backend: tech stack, database, API contracts, deployment
- Frontend: UI framework, state, component approach
- Integration: how frontend calls backend

### 2. Fill manifest (2 min)
```yaml
project:
  name: "My App"
  scope: "pilot"
  feature: "my-feature"
  context_file: "my-feature.md"
```

### 3. Run — same 6 verbs as all packs

---

## What SPECIFY Generates for Full Stack

Constitution Part 2 extracts BOTH layers:
- Backend + Frontend tech stack
- OpenAPI contract as source of truth
- Core Principles: API-Contract-First, Test-First, Traceable

All templates included (most comprehensive pack):
- api-spec, data-model, component-spec, ux-flow, screen-spec

---

## Key Full Stack Rules (always enforced)
- OpenAPI contract generated first — both teams align
- Backend class max: 200 lines
- Frontend component max: 150 lines
- Both layers tested independently + E2E together
- API contract is source of truth — never assume backend internals
