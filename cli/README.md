# sdd-init — SDD Framework CLI

Cross-platform replacement for `setup.sh` / `setup.ps1`.  
No bash required. Works on Mac, Linux, and Windows.

## Install

```bash
# Run once without installing (recommended for first use)
npx sdd-init init

# Or install globally
npm install -g sdd-init
sdd init
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
applies the migration to `manifest.yml`, and updates `sdd_version`.

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
