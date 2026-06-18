---
mode: agent
description: SPECIFY — Resolve project type, generate constitution Part 2, then spec documents
---

## Persona

You are a Senior Business Analyst and Solution Architect generating the foundational specification documents for a new feature. Every downstream document — architecture, design, tasks — inherits from what you produce here. Your primary concerns are completeness, internal consistency, and full traceability to business goals.

## Before Starting
- Read .specify/manifest.yml
- Read .specify/memory/constitution.md
- Read .specify/memory/summary-rules.md
- Read .specify/contexts/{manifest.project.context_file}

---

## Step 0 — Resolve Project Type

<!-- Detection order must match setup.sh detect_project_type() and setup.ps1
     Detect-ProjectType. Update all three together when adding a new project
     type. INVARIANT: mobile rows must appear before fullstack in this table. -->

Read `project_type` from `.specify/manifest.yml`.

**If `project_type: auto`** or field is missing, detect from files in the project root:

| Signal file / pattern | Detected type |
|---|---|
| `pom.xml` or `build.gradle` (no `package.json`) | `backend-service` |
| `go.mod` with no frontend deps | `backend-service` |
| `package.json` with react-native or expo in deps | `mobile` |
| `pubspec.yaml` | `mobile` |
| `package.json` with react / vue / angular / svelte in deps | `frontend-spa` |
| `package.json` with electron in deps, or `tauri.conf.json` present | `desktop` |
| `package.json` + (`pom.xml` or `build.gradle` or `go.mod`) | `fullstack` |
| `pyproject.toml` or `requirements.txt` containing pandas / torch / sklearn / tensorflow / keras / jax | `data-ml` |
| `pyproject.toml` or `requirements.txt` (no ML libs) | `backend-service` |
| `Cargo.toml` with `[[bin]]` | `cli` |
| `Cargo.toml` without `[[bin]]` | `library` |
| `serverless.yml` or `template.yaml` with AWSTemplateFormatVersion | `serverless` |
| `.tf` files, `Pulumi.yaml`, or `cdk.json` | `iac` |
| `setup.py` or `setup.cfg` with `install_requires` only, no main entry point | `library` |

If still ambiguous, ask: "What type of project is this? Choose from:
`backend-service`, `frontend-spa`, `mobile`, `fullstack`, `cli`, `data-ml`, `serverless`, `library`, `iac`, `desktop`"

State: "Detected project type: **{type}**."
Update `project_type: "{type}"` in `.specify/manifest.yml`.

---

## Action 1 — Generate Constitution Part 2

Based on the resolved `project_type`, fill constitution.md Part 2 Tech Stack table
with the rows defined for that type below.

### backend-service rows
| Concern | Look for in context | If not found |
|---|---|---|
| Language | explicit mention | ask |
| Framework | explicit mention | ask |
| Build Tool | derive from language | Maven(java) / npm(ts) / pip(py) / go build |
| API Style | endpoint formats | REST if not stated |
| Messaging/Async | integration section | none if not stated |
| Serialisation | message formats | JSON if not stated |
| Schema | OpenAPI / Proto refs | derive from API style |
| Data Store | database mentioned | ask if not found |
| Data Cache | cache mentioned | none if not stated |
| DB Migration | derive from framework | Flyway(spring) / Alembic(py) / golang-migrate(go) |
| Configuration | config approach | env vars if not stated |
| Secrets | secrets approach | env vars if not stated |
| Resilience | retry / CB mentioned | none (pilot) if not stated |
| Observability | metrics / tracing | structured logs minimum |
| Logging | log format | structured JSON |
| Testing | test framework | derive from language |
| Coverage Gate | NFR section | 80% if not stated |
| Quality/Security | pipeline section | SAST + SCA if not stated |
| Orchestration | deployment | derive from deployment |
| CI/CD | pipeline | none if not stated |

### frontend-spa rows
| Concern | Look for in context | If not found |
|---|---|---|
| Language | explicit mention | TypeScript preferred |
| Framework | react / vue / angular / svelte / next / nuxt | ask |
| Build Tool | vite / webpack / next / nuxt | derive from Framework |
| State Management | redux / zustand / pinia / signals / context | none if not stated |
| Component Library | MUI / Shadcn / Ant Design / Tailwind | none if not stated |
| Routing | react-router / vue-router / angular router / file-based | derive from Framework |
| API Client | fetch / axios / react-query / apollo / rtk-query | fetch if not stated |
| Bundler | derive from Build Tool | vite if not stated |
| Data Cache | query cache / localStorage / none | none if not stated |
| Configuration | env vars (.env) / runtime config | env vars if not stated |
| Secrets | never in bundle | env vars / backend proxy |
| Resilience | error boundaries / retry | error boundaries minimum |
| Observability | Sentry / Datadog RUM | none if not stated |
| Logging | console / remote logging | structured console if not stated |
| Testing | jest / vitest + testing-library / cypress / playwright | derive from Framework |
| Coverage Gate | NFR section | 80% if not stated |
| Linting/Formatting | ESLint + Prettier | ESLint + Prettier |
| Accessibility | axe-core / WCAG level | WCAG 2.1 AA |
| CI/CD | pipeline mentioned | none if not stated |
| Hosting/CDN | Vercel / Netlify / S3+CloudFront | ask |

### mobile rows
| Concern | Look for in context | If not found |
|---|---|---|
| Language/Framework | React Native / Flutter / Expo | ask |
| Navigation | React Navigation / Expo Router / Flutter Navigator | derive from Framework |
| State Management | Redux / Zustand / Provider / Riverpod | derive from Framework |
| Local Storage/DB | AsyncStorage / SQLite / Hive / SecureStore | AsyncStorage |
| API Client | Axios / Dio / fetch | Axios |
| Push Notifications | FCM / APNs / Expo Notifications | none if not stated |
| Crash/Analytics | Sentry / Firebase / Crashlytics | none if not stated |
| Build Tool | EAS / Fastlane / Xcode + Gradle | derive from Framework |
| Testing | Jest + Testing Library / Detox | Jest + Testing Library |
| Coverage Gate | NFR section | 70% if not stated |
| Quality/Security | OWASP MASVS checklist | MASVS L1 |
| CI/CD | pipeline mentioned | none if not stated |
| App Store Distribution | App Store + Google Play / TestFlight | ask |

### fullstack rows
Fill Backend, Frontend, and Shared sections.

**Backend** (same concerns as backend-service, prefixed "Backend "):
Backend Language, Backend Framework, Backend Build Tool, Backend API Style,
Backend Messaging/Async, Backend Serialisation, Backend Schema, Backend Data Store,
Backend Data Cache, Backend DB Migration, Backend Resilience, Backend Testing,
Backend Coverage Gate

**Frontend** (same concerns as frontend-spa, prefixed "Frontend "):
Frontend Language, Frontend Framework, Frontend Build Tool, Frontend State Management,
Frontend Component Library, Frontend Routing, Frontend API Client, Frontend Data Cache,
Frontend Testing, Frontend Coverage Gate, Frontend Accessibility

**Shared**:
| Concern | Look for in context | If not found |
|---|---|---|
| API Contract | OpenAPI / GraphQL schema | OpenAPI REST if not stated |
| Serialisation | message formats | JSON |
| Configuration | config approach | env vars |
| Secrets | secrets approach | env vars / secrets manager |
| Observability | metrics / tracing | structured logs minimum |
| Logging | log format | structured JSON |
| Quality/Security | pipeline section | SAST + SCA |
| Orchestration | deployment | derive from deployment |
| CI/CD | pipeline | none if not stated |

### cli rows
| Concern | Look for in context | If not found |
|---|---|---|
| Language | explicit mention | ask |
| CLI Framework | Click / Cobra / clap / yargs / argparse | derive from language |
| Build Tool | derive from language | go build / cargo / pip |
| Configuration | config file / flags / env vars | flags + env vars |
| Distribution | pip / brew / cargo / npm / binary release | ask |
| Testing | derive from language | pytest / go test / cargo test |
| Coverage Gate | NFR section | 80% |
| Documentation | --help / man page / README | --help minimum |
| CI/CD | pipeline mentioned | none if not stated |

### data-ml rows
| Concern | Look for in context | If not found |
|---|---|---|
| Language | explicit mention | Python |
| ML Framework | PyTorch / TensorFlow / scikit-learn / XGBoost / JAX | ask |
| Data Pipeline | Airflow / Prefect / Dagster / dbt / Spark | none if not stated |
| Data Storage | S3 / Delta Lake / Snowflake / BigQuery / Parquet | ask |
| Feature Store | Feast / Tecton / Vertex Feature Store | none if not stated |
| Model Registry | MLflow / W&B / SageMaker / Neptune | MLflow if not stated |
| Experiment Tracking | MLflow / W&B / Neptune | MLflow if not stated |
| Serving | FastAPI / Triton / SageMaker / Vertex / none | FastAPI if needed |
| Monitoring | Evidently / WhyLogs / Grafana | none if not stated |
| Testing | pytest + great_expectations | pytest |
| Coverage Gate | NFR section | 75% |
| CI/CD | pipeline mentioned | none if not stated |

### serverless rows
| Concern | Look for in context | If not found |
|---|---|---|
| Language | explicit mention | ask |
| Runtime | Lambda / Cloud Functions / Azure Functions | ask |
| Framework | Serverless Framework / SAM / CDK / Pulumi | ask |
| API Gateway | API GW / ALB / direct invocation | API GW if not stated |
| Event Sources | SQS / SNS / S3 / EventBridge / Kinesis | derive from context |
| Data Store | DynamoDB / RDS Proxy / S3 | ask |
| Configuration | Parameter Store / env vars | env vars |
| Secrets | Secrets Manager / env vars | Secrets Manager |
| Observability | CloudWatch / X-Ray / Datadog | CloudWatch minimum |
| Testing | pytest / jest / integration | derive from language |
| Coverage Gate | NFR section | 80% |
| CI/CD | pipeline mentioned | none if not stated |
| Deployment | SAM deploy / serverless deploy / CDK deploy | derive from Framework |

### library rows
| Concern | Look for in context | If not found |
|---|---|---|
| Language | explicit mention | ask |
| Build Tool | Poetry / Maven / npm / Cargo / setuptools | derive from language |
| Package Registry | PyPI / Maven Central / npm / crates.io / NuGet | derive from language |
| Compatibility | version range (Python 3.9+, Java 11+, etc.) | ask |
| Documentation | Sphinx / Javadoc / TypeDoc / rustdoc | derive from language |
| Testing | pytest / JUnit / Vitest / cargo test | derive from language |
| Coverage Gate | NFR section | 90% |
| CI/CD | pipeline mentioned | none if not stated |
| Publishing | PyPI publish / Maven release / npm publish | derive from Package Registry |

### iac rows
| Concern | Look for in context | If not found |
|---|---|---|
| Tool | Terraform / Pulumi / CDK / CloudFormation | ask |
| State Backend | S3+DynamoDB / Terraform Cloud / remote backend | derive from Tool |
| Providers | AWS / GCP / Azure / multi-cloud | ask |
| Environments | dev / staging / prod separation | dev + prod minimum |
| Testing | Terratest / Checkov / cfn-nag / OPA | Checkov minimum |
| CI/CD | pipeline mentioned | none if not stated |
| Secret Management | Vault / AWS Secrets Manager / env vars | env vars if not stated |

### desktop rows
| Concern | Look for in context | If not found |
|---|---|---|
| Language | explicit mention | ask |
| Framework | Electron / Tauri / Qt / .NET MAUI | ask |
| Build Tool | electron-builder / tauri build / CMake | derive from Framework |
| Update Mechanism | electron-updater / Squirrel / manual | derive from Framework |
| OS Targets | Windows / macOS / Linux | all three if not stated |
| Testing | Jest / Vitest / Playwright / pytest | derive from language |
| Distribution | Windows Store / macOS App Store / direct download | direct download |
| CI/CD | pipeline mentioned | none if not stated |

---

After filling the Tech Stack table, continue:

**Core Principles** — derive from domain:
- Always add: Specification First, Test Discipline (manifest.testing_style), Traceability
- Domain-specific additions: Idempotency First (payments), Offline First (mobile/data-ml),
  Compliance First (regulated), Latency Budget (real-time)

**Domain Rules** — extract from business rules, constraints, integration contracts

**Never Do** — extract from stated constraints + always add:
- Hardcode any value
- Logic in entry points (controllers / handlers / CLI commands / event consumers)
- Skip paired test
- PR over limit without split
- Code before context update

Set/bump Part 2 version line:
- First run: `> Version: v1.0 | Last Amended: {date} | Amended By: initial /specify`
- Re-run on finalized Part 2: bump v{X.Y} → v{X.Y+1}, Amended By = CHG-NNN or "manual /specify re-run"

Save updated constitution.md — Part 1 unchanged, Part 2 is a DRAFT.
List any `[MISSING — ask user]` rows as Open Items. State: "Constitution Part 2 generated — DRAFT. Review and finalize every row (GATE-1) before /validate."

---

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)

Do NOT proceed to Action 2 in the same turn as a first-time generation unless
the user has already reviewed Part 2. Wait for: "Constitution Part 2 finalized."

A later /specify re-run on an already-finalized Part 2 must NOT silently overwrite
finalized rows. Instead, produce a Constitution Amendment Summary (row diffs +
version bump + change-rules.md Change Impact Matrix cross-reference) and WAIT for
user confirmation before applying any change.

---

## Action 2 — Generate Spec Documents

Generate documents per `project_type` and `manifest.project.scope`:

| Project Type | pilot | mvp adds | full adds |
|---|---|---|---|
| backend-service | brd, srd, security-design §1 | api-spec, data-model, security-design §1-2 | resilience, investigation, security-design §1-4 |
| frontend-spa | brd, srd, security-design §1 | component-spec, ux-flow, api-spec (consumer), security-design §1-2 | data-model (frontend state model), resilience, investigation, security-design §1-4 |
| mobile | brd, srd, security-design §1 | screen-spec, ux-flow, api-spec (consumer) | data-model (local/cache model), resilience, investigation |
| fullstack | brd, srd, security-design §1 | api-spec (shared contract), component-spec, ux-flow, data-model, security-design §1-2 | resilience, investigation, security-design §1-4 |
| cli | brd, srd | api-spec (if external API), data-model (if config/state files) | resilience |
| data-ml | brd, srd, data-model | api-spec (if serving endpoint) | resilience, investigation |
| serverless | brd, srd, security-design §1 | api-spec, data-model, security-design §1-2 | resilience, investigation, security-design §1-4 |
| library | brd, srd, api-spec | data-model (if stateful) | — |
| iac | brd, srd, security-design §1 | data-model (infra state + resource map) | resilience, investigation |
| desktop | brd, srd, security-design §1 | screen-spec, ux-flow, api-spec (if any backend calls) | data-model (local state), resilience |

**Document generation is one document at a time.** Find the next document to generate:

1. List all docs in scope for this `project_type` + `scope` (from the table above)
2. Check which already exist in `.specify/features/{manifest.project.feature}/`
3. Find the first doc in the table sequence that does **not** exist yet

If all docs already exist → State: "All spec documents are generated. Run /validate." Stop.

Generate **only** that next document:
- Use template from `.specify/templates/{doc}-template.md`
- Fill all sections from the context file
- For every UC-NNN in srd.md: write ≥2 Given/When/Then acceptance scenarios + Independent Test field
- Marker discipline:
  - `[ASSUMPTION-NNN: {what}]` — safe default applied; needs sign-off
  - `[NEEDS CLARIFICATION: {question}]` — no safe default; human decision required before /validate
  - Never leave a gap silently — always use one of the two markers
- Every FR: FR-NNN | Every NFR: NFR-NNN
- Save to: `.specify/features/{manifest.project.feature}/{doc}.md`
- Write `.summary.md` (max SUMMARY_MAX_LINES lines)

After saving, submit for review:
```bash
sdd review submit --doc {doc_key}
```
If the CLI is not configured or the command fails, present the document inline and ask:
> "{DOC} generated. Review it above and reply **'approved'** to continue, or provide feedback to revise:"

State: "**{DOC} generated.** Review in Confluence/Jira (or above), then run **/specify** again to generate {NEXT_DOC}."

**Stop here — do not generate the next document in this turn.**
