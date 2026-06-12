# SDD Backend Service Pack
## REST APIs · Microservices · Databases · Messaging

---

## What This Pack Is For
Building backend services: REST APIs, microservices, databases, messaging.
Languages: Java · TypeScript · Python · Go
Frameworks: Spring Boot · Express/NestJS · FastAPI · Django
Deploy: Docker · Kubernetes · Bare-metal

---

## How It Works — 3 Steps

### 1. Write your context (15-30 min)
Create `.specify/contexts/{feature}.md`
Describe: what it does, tech stack, flows, integrations, NFRs, constraints.
Use `CONTEXT-GUIDE.md` as your guide.
**Include your tech stack — agent extracts it for constitution.**

### 2. Fill manifest (2 min)
Edit `.specify/manifest.yml` — just 4 fields:
```yaml
project:
  name: "My Service"
  scope: "pilot"
  feature: "my-feature"
  context_file: "my-feature.md"
```

### 3. Run
```bash
claude    # Claude Code Desktop
# OR open VS Code + Copilot
```
Paste Step 0 from `PROMPT-GUIDE.md`

---

## The 6 Verbs

```
SPECIFY    → Generates constitution Part 2 from context
             THEN generates BRD, SRD, API Spec, Data Model
ANALYZE    → Risks, dependencies, complexity
CLARIFY    → Resolve ambiguities (you answer)
PLAN       → Architecture + HLD + LLD + Plan
TASK       → Feature → Story → Task + Jira CSV
IMPLEMENT  → Code one task at a time, PR rules enforced
```

---

## Constitution — Generated Not Filled

SPECIFY reads your context and automatically fills:
```
Tech Stack table (20 concerns including Language, Framework,
Database, CI/CD, Testing, Coverage Gate, Observability...)
Core Principles (derived from your domain)
Domain Rules (extracted from your business rules)
Never Do (extracted from your constraints)
```

You never manually fill the constitution.

---

## Scope → Documents

| Document | Pilot | MVP | Full |
|---|---|---|---|
| BRD + SRD | ✅ | ✅ | ✅ |
| Analyze | ✅ | ✅ | ✅ |
| HLD (diagrams) | ✅ | ✅ | ✅ |
| Data Model + API Spec | ✅ | ✅ | ✅ |
| LLD + ADRs | ❌ | ✅ | ✅ |
| Resilience + Security | ❌ | ❌ | ✅ |
| Stories + Tasks + Jira | ✅ | ✅ | ✅ |
| QA Cases + Runbook | ❌ | ✅ | ✅ |

---

## For ICS Payment Service
Use `ICS-context-pack.zip` alongside this pack:
```bash
cp ICS-context-pack/manifest-pilot.yml .specify/manifest.yml
cp ICS-context-pack/instant-credit-transfer-pilot.md .specify/contexts/
```
