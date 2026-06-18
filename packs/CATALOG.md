# SDD Pack Catalog

> Official and community-submitted packs for the SDD Framework.
> See [PACK-SPEC.md](../PACK-SPEC.md) to build and submit your own.

---

## Official Packs

| Pack | Project class | Auto-detect | Scope support |
|---|---|---|---|
| [sdd-universal](sdd-universal/) | Any type — auto-detected | ✅ (10 types) | pilot / mvp / full |
| [sdd-backend-service](sdd-backend-service/) | REST APIs, microservices, data pipelines | — | pilot / mvp / full |
| [sdd-frontend-spa](sdd-frontend-spa/) | React / Vue / Angular / Svelte SPAs | — | pilot / mvp / full |
| [sdd-mobile](sdd-mobile/) | React Native / Flutter (iOS + Android) | — | pilot / mvp / full |
| [sdd-fullstack](sdd-fullstack/) | Backend + Frontend in one repo | — | pilot / mvp / full |

**Not sure which to use?** → Start with `sdd-universal`.

---

## Which Pack Is Right for Me?

```
I don't know my project type yet, or it's not listed below
  → sdd-universal

I'm building a REST API / GraphQL API / microservice / worker
  → sdd-backend-service

I'm building a single-page web application (React, Vue, Angular, Svelte, Next.js)
  → sdd-frontend-spa

I'm building a mobile app (React Native, Flutter, Expo)
  → sdd-mobile

I'm building a monorepo with a backend API and frontend client
  → sdd-fullstack
```

---

## Community Packs

_No community packs yet — be the first!_

See [PACK-SPEC.md](../PACK-SPEC.md) for the submission guide.

---

## Supported Project Types (sdd-universal)

| Type | Language / stack | Detected from |
|---|---|---|
| `backend-service` | Java, Go, Python, Node.js (server) | `pom.xml`, `go.mod`, `requirements.txt`, `package.json` (no frontend deps) |
| `frontend-spa` | React, Vue, Angular, Svelte, Next.js | `package.json` + SPA framework dep |
| `mobile` | React Native, Flutter | `pubspec.yaml`, or `package.json` + react-native/expo |
| `fullstack` | Any backend + JS frontend | `package.json` + `pom.xml`/`build.gradle`/`go.mod` |
| `cli` | Rust (bin), Go (cmd/) | `Cargo.toml` with `[[bin]]`, or `go.mod` + `cmd/` |
| `data-ml` | Python (pandas, PyTorch, sklearn) | `requirements.txt` with ML libraries |
| `serverless` | AWS Lambda, SAM, Serverless Framework | `serverless.yml`, `template.yaml` |
| `library` | Rust (lib), Python (package), any | `Cargo.toml` without `[[bin]]`, Python lib structure |
| `iac` | Terraform, Pulumi, AWS CDK | `*.tf`, `Pulumi.yaml`, `cdk.json` |
| `desktop` | Electron, Tauri | `package.json` + electron, or `tauri.conf.json` |
