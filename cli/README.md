# sddflow — SDD Framework CLI (Node.js)

[![npm version](https://img.shields.io/npm/v/@sunil1983us/sddflow.svg?color=blue)](https://www.npmjs.com/package/@sunil1983us/sddflow)
[![npm downloads](https://img.shields.io/npm/dm/@sunil1983us/sddflow.svg?color=green)](https://www.npmjs.com/package/@sunil1983us/sddflow)
[![License](https://img.shields.io/npm/l/@sunil1983us/sddflow.svg)](../LICENSE)
[![CI](https://github.com/sunil1983us/sddflow/actions/workflows/ci.yml/badge.svg)](https://github.com/sunil1983us/sddflow/actions/workflows/ci.yml)

> **Deprecated.** This Node.js CLI covers scaffolding only
> (`sdd init` / `sdd upgrade`), receives fixes only — no new features are
> planned. **Use the Python CLI instead** (`pip install sddflow`) unless
> you specifically need a Node-only environment with no Python available:
> it has all of this CLI's functionality plus Jira, Confluence, review
> gates, and PR automation. If you install both, they collide on the
> `sdd` binary name: prefer the Python CLI.

Cross-platform replacement for `setup.sh` / `setup.ps1`.  
No bash required. Works on Mac, Linux, and Windows.

## Install

> ⚠️ Two things to avoid confusing this with: the `sdd-init` name on npm
> belongs to an **unrelated third-party package** — do not install that
> one. And npm's own anti-squatting policy blocks the unscoped name
> `sddflow` as "too similar" to an unrelated existing package
> (`sdd-flow`) — so this CLI publishes under the **scoped** name
> `@sunil1983us/sddflow` instead. The `sdd` command it installs is
> unaffected by the scope:

```bash
npm install -g @sunil1983us/sddflow
sdd init
```

**Alternative:** use `bash setup.sh` (Mac/Linux) or `.\setup.ps1` (Windows) instead —
they do exactly the same thing as `sdd init` without needing Node.js or npm.

For development / contributors:

```bash
git clone https://github.com/sunil1983us/sddflow.git
cd sddflow/cli
npm ci
node bin/sdd.js init
```

## Commands

### `sdd init`

Initialize an SDD pack in the current project directory.  
Replaces `bash setup.sh` / `.\setup.ps1`.

```bash
# Interactive (recommended)
sdd init

# Non-interactive
sdd init --project "my-payments-api" \
         --feature "user-authentication" \
         --scope   pilot \
         --type    backend-service
```

**Options:**

| Flag | Description | Default |
|---|---|---|
| `-p, --project <name>` | Project name | prompted |
| `-f, --feature <name>` | First feature name | prompted |
| `-s, --scope <scope>` | `pilot` \| `mvp` \| `full` | `pilot` |
| `-t, --type <type>` | Project type (auto-detected if omitted) | auto |

**What it does:**
1. Auto-detects project type from files in the current directory
2. Updates `.specify/manifest.yml` using `js-yaml` — no injection risk
3. Creates `.specify/contexts/{feature}.md` (template)
4. Creates `.specify/features/{feature}/` output directory

**Why this is safer than `setup.sh`:**  
`manifest.yml` is written by `js-yaml.dump()` — project/feature names with special characters (`'`, `\`, `&`, etc.) are serialized as YAML data, never as code. The only rejected character is `"` (which would produce invalid YAML regardless of approach).

---

### `sdd upgrade`

Migrate an existing project's `manifest.yml` to the current pack version.

```bash
sdd upgrade
```

Shows what changed between your current `sdd_version` and the CLI version,
applies the migration(s) to `manifest.yml`, and updates `sdd_version`.

If several versions are pending, a real terminal is asked whether to jump
straight to the latest version (apply everything now) or step through one
migration at a time; `--to-latest`/`--step`/`-y` skip the prompt, and a
non-interactive invocation (CI, scripts) defaults to jumping straight to
latest so it never needs repeated reruns to converge.

---

## Supported Project Types

| Type | Detected from |
|---|---|
| `backend-service` | `pom.xml`, `build.gradle`, `go.mod`, Python files |
| `frontend-spa` | `package.json` + react/vue/svelte/angular/next/nuxt |
| `mobile` | `pubspec.yaml`, or `package.json` + react-native/expo |
| `fullstack` | `package.json` + `pom.xml`/`build.gradle`/`go.mod` |
| `cli` | `Cargo.toml` with `[[bin]]`, or `go.mod` + `cmd/` dir |
| `data-ml` | `requirements.txt` with pandas/torch/sklearn/keras/jax |
| `serverless` | `serverless.yml`, or `template.yaml` with AWSTemplateFormatVersion |
| `library` | `Cargo.toml` without `[[bin]]`, or Python lib structure |
| `iac` | `*.tf` files, `Pulumi.yaml`, `cdk.json` |
| `desktop` | `package.json` + electron, or `tauri.conf.json` |

Detection order matches `setup.sh` and `specify.prompt.md` Step 0.

---

## Requirements

- Node.js ≥ 18
- An SDD pack already copied into your project directory
