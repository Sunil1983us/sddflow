#!/usr/bin/env bash
# SDD Framework — Universal Project Initializer
# Usage: bash setup.sh [--project <name>] [--scope pilot|mvp|full] [--feature <name>] [--type <project-type>] [--plan-mode unified|separate]
# Run this once after copying the pack into your project directory.

set -euo pipefail

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SDD Framework — Universal Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --- Parse optional CLI args ---
PROJECT_NAME=""
SCOPE=""
FEATURE_NAME=""
PROJECT_TYPE_ARG=""
PLAN_MODE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)    PROJECT_NAME="$2"; shift 2;;
    --scope)      SCOPE="$2";        shift 2;;
    --feature)    FEATURE_NAME="$2"; shift 2;;
    --type)       PROJECT_TYPE_ARG="$2"; shift 2;;
    --plan-mode)  PLAN_MODE="$2";    shift 2;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done

# --- Auto-detect project type ---
# Detection order must match specify.prompt.md Step 0 table and setup.ps1
# Detect-ProjectType. Update all three together when adding a new type.
# INVARIANT: mobile checks must appear before fullstack — a React Native +
# pom.xml monorepo must resolve to "mobile", not "fullstack".
detect_project_type() {
  local root="${1:-.}"

  # Mobile (Flutter/Dart) — checked before fullstack to avoid misclassifying a
  # React Native + backend monorepo as fullstack
  if [ -f "$root/pubspec.yaml" ]; then echo "mobile"; return; fi

  # Package.json-based detection — pass $root via env to avoid path injection
  if [ -f "$root/package.json" ]; then
    local deps
    deps=$(root="$root" python3 -c "
import json, os, sys
try:
    d = json.load(open(os.environ['root'] + '/package.json'))
    all_deps = list(d.get('dependencies', {}).keys()) + list(d.get('devDependencies', {}).keys())
    print(' '.join(all_deps))
except Exception:
    print('')
" 2>/dev/null || echo "")

    # Mobile (React Native / Expo) — before fullstack check
    if echo "$deps" | grep -qE 'react-native|expo\b'; then echo "mobile"; return; fi

    # Fullstack: JS frontend + separate backend (only after mobile ruled out)
    if { [ -f "$root/pom.xml" ] || [ -f "$root/build.gradle" ] || [ -f "$root/go.mod" ]; }; then
      echo "fullstack"; return
    fi

    if echo "$deps" | grep -q 'electron'; then echo "desktop"; return; fi
    if echo "$deps" | grep -qE '\breact\b|\bvue\b|angular|svelte|next|nuxt'; then echo "frontend-spa"; return; fi
  fi

  # Desktop (Tauri)
  if [ -f "$root/tauri.conf.json" ] || [ -f "$root/src-tauri/tauri.conf.json" ]; then echo "desktop"; return; fi

  # Serverless
  if [ -f "$root/serverless.yml" ]; then echo "serverless"; return; fi
  if [ -f "$root/template.yaml" ] && grep -q 'AWSTemplateFormatVersion' "$root/template.yaml" 2>/dev/null; then echo "serverless"; return; fi

  # IaC
  if ls "$root"/*.tf > /dev/null 2>&1 || [ -f "$root/Pulumi.yaml" ] || [ -f "$root/cdk.json" ]; then echo "iac"; return; fi

  # Rust
  if [ -f "$root/Cargo.toml" ]; then
    if grep -q '\[\[bin\]\]' "$root/Cargo.toml"; then echo "cli"; else echo "library"; fi
    return
  fi

  # Go
  if [ -f "$root/go.mod" ]; then
    if [ -d "$root/cmd" ]; then echo "cli"; else echo "backend-service"; fi
    return
  fi

  # Python
  if [ -f "$root/pyproject.toml" ] || [ -f "$root/requirements.txt" ]; then
    local py_deps
    py_deps=$(cat "$root/requirements.txt" "$root/pyproject.toml" 2>/dev/null | tr '[:upper:]' '[:lower:]')
    if echo "$py_deps" | grep -qE 'pandas|torch|tensorflow|sklearn|keras|jax|xgboost|lightgbm'; then echo "data-ml"; return; fi
    if ([ -f "$root/setup.py" ] || grep -q 'install_requires\|build-backend' "$root/pyproject.toml" 2>/dev/null) && \
       [ ! -f "$root/main.py" ] && [ ! -d "$root/app" ] && [ ! -d "$root/src/app" ]; then
      echo "library"; return
    fi
    echo "backend-service"; return
  fi

  # Java/Kotlin
  if [ -f "$root/pom.xml" ] || [ -f "$root/build.gradle" ] || [ -f "$root/build.gradle.kts" ]; then
    echo "backend-service"; return
  fi

  echo ""
}

# When stdin is not a terminal (CI, piped input, automation), `read` hits EOF
# and set -e aborts the script — so prompt only when interactive: optional
# values fall back to their defaults, required ones fail fast with a hint.
if [ -t 0 ]; then INTERACTIVE=1; else INTERACTIVE=0; fi

if [[ -n "$PROJECT_TYPE_ARG" ]]; then
  PROJECT_TYPE="$PROJECT_TYPE_ARG"
  echo "  Project type (from --type): $PROJECT_TYPE"
else
  echo "  Detecting project type..."
  DETECTED_TYPE=$(detect_project_type ".")
  if [[ -n "$DETECTED_TYPE" ]]; then
    echo "  Detected: $DETECTED_TYPE"
    if [[ $INTERACTIVE -eq 1 ]]; then
      echo ""
      read -r -p "  Project type [$DETECTED_TYPE]: " PROJECT_TYPE_INPUT
      PROJECT_TYPE="${PROJECT_TYPE_INPUT:-$DETECTED_TYPE}"
    else
      PROJECT_TYPE="$DETECTED_TYPE"
    fi
  else
    echo "  Could not auto-detect. Supported types:"
    echo "    backend-service  frontend-spa  mobile  fullstack"
    echo "    cli  data-ml  serverless  library  iac  desktop"
    if [[ $INTERACTIVE -eq 0 ]]; then
      echo "  ✗  --type is required when running non-interactively and auto-detection finds nothing" >&2
      exit 1
    fi
    echo ""
    while [[ -z "${PROJECT_TYPE:-}" ]]; do
      read -r -p "  Project type: " PROJECT_TYPE
    done
  fi
fi
echo ""

# --- Interactive prompts for anything not supplied ---
if [[ -z "$PROJECT_NAME" ]]; then
  if [[ $INTERACTIVE -eq 1 ]]; then
    read -r -p "Project name (e.g. my-payments-api): " PROJECT_NAME
  else
    echo "  ✗  --project is required when running non-interactively" >&2
    exit 1
  fi
fi

if [[ -z "$FEATURE_NAME" ]]; then
  if [[ $INTERACTIVE -eq 1 ]]; then
    read -r -p "First feature name (e.g. user-authentication): " FEATURE_NAME
  else
    echo "  ✗  --feature is required when running non-interactively" >&2
    exit 1
  fi
fi

if [[ -z "$SCOPE" ]]; then
  if [[ $INTERACTIVE -eq 1 ]]; then
    echo ""
    echo "Scope:"
    echo "  pilot  — quick prototype, minimal docs (brd, srd, security-design §1)"
    echo "  mvp    — production-ready (+ api-spec, data-model, security-design §1-2)"
    echo "  full   — enterprise (+ resilience, investigation, security-design §1-4)"
    read -r -p "Scope [pilot]: " SCOPE
  fi
  SCOPE="${SCOPE:-pilot}"
fi

if [[ -z "$PLAN_MODE" ]]; then
  if [[ $INTERACTIVE -eq 1 ]]; then
    echo ""
    echo "Plan document style:"
    echo "  unified  — One combined design.md covering architecture, diagrams,"
    echo "             API design and decisions in one place."
    echo "             Good for: small teams, fast delivery, single review gate."
    echo ""
    echo "  separate — Three focused documents reviewed one by one:"
    echo "             arch.md → hld.md → adr.md (mvp+ only)"
    echo "             Good for: larger teams, separate approvals, detailed audit trail."
    echo ""
    read -r -p "Plan mode [unified]: " PLAN_MODE
  fi
  PLAN_MODE="${PLAN_MODE:-unified}"
fi

# --- Validate inputs ---
# Double quotes inside a YAML double-quoted scalar produce invalid YAML.
# Reject early with a clear message rather than silently writing a broken file.
_validate_name() {
  local value="$1" label="$2"
  if [[ "$value" == *'"'* ]]; then
    echo "" >&2
    echo "  ✗  $label cannot contain double-quote characters." >&2
    echo "     Names are written inside YAML double quotes — an embedded \" breaks" >&2
    echo "     manifest.yml. Please re-run without \" in the name." >&2
    exit 1
  fi
}
_validate_name "$PROJECT_NAME" "Project name"
_validate_name "$FEATURE_NAME" "Feature name"

echo ""
echo "Setting up:"
echo "  Project   : $PROJECT_NAME"
echo "  Type      : $PROJECT_TYPE"
echo "  Feature   : $FEATURE_NAME"
echo "  Scope     : $SCOPE"
echo "  Plan mode : $PLAN_MODE"
echo ""

# --- Update manifest.yml ---
# Values are passed via environment variables so that special characters in
# project/feature names (quotes, backslashes, re.sub metacharacters) are
# treated as data, never as code. Heredoc is quoted (<<'PYEOF') to prevent
# shell expansion inside the Python script.
MANIFEST=".specify/manifest.yml"
if [[ -f "$MANIFEST" ]]; then
  SDD_MANIFEST="$MANIFEST" \
  SDD_PROJECT_NAME="$PROJECT_NAME" \
  SDD_SCOPE="$SCOPE" \
  SDD_FEATURE_NAME="$FEATURE_NAME" \
  SDD_PROJECT_TYPE="$PROJECT_TYPE" \
  SDD_PLAN_MODE="$PLAN_MODE" \
  python3 - <<'PYEOF'
import re, os
manifest     = os.environ['SDD_MANIFEST']
project_name = os.environ['SDD_PROJECT_NAME']
scope        = os.environ['SDD_SCOPE']
feature_name = os.environ['SDD_FEATURE_NAME']
project_type = os.environ['SDD_PROJECT_TYPE']
plan_mode    = os.environ['SDD_PLAN_MODE']
with open(manifest) as f:
    content = f.read()
content = re.sub(r'name:\s*""',              lambda _: f'name: "{project_name}"',            content, count=1)
content = re.sub(r'scope:\s*"pilot"',        lambda _: f'scope: "{scope}"',                  content, count=1)
content = re.sub(r'feature:\s*""',           lambda _: f'feature: "{feature_name}"',         content, count=1)
content = re.sub(r'context_file:\s*""',      lambda _: f'context_file: "{feature_name}.md"', content, count=1)
content = re.sub(r'project_type:\s*"auto"',  lambda _: f'project_type: "{project_type}"',    content, count=1)
content = re.sub(r'plan_mode:\s*"unified"',  lambda _: f'plan_mode: "{plan_mode}"',          content, count=1)
with open(manifest, 'w') as f:
    f.write(content)
PYEOF
  echo "  ✓  .specify/manifest.yml filled"
else
  echo "  ✗  .specify/manifest.yml not found — are you in the pack root?" >&2
  exit 1
fi

# --- Create contexts directory + placeholder ---
CONTEXT_FILE=".specify/contexts/${FEATURE_NAME}.md"
mkdir -p "$(dirname "$CONTEXT_FILE")"
if [[ ! -f "$CONTEXT_FILE" ]]; then
  cat > "$CONTEXT_FILE" << 'TMPL'
# Context: FEATURE_PLACEHOLDER
# Project: PROJECT_PLACEHOLDER
# Fill this file, then run /specify (or /create-context to build it interactively).

## What This Does
{describe the feature in 2-3 sentences}

## Actors
{who triggers or benefits from this feature?}

## Key Flows
{describe 2-3 main user journeys}

## Integrations
{list any external systems, APIs, or databases}

## Business Rules
{any constraints, validation rules, or compliance requirements}

## Tech Stack
{language, framework, database, cache, CI/CD — fill what you know}

## Non-Functional Requirements
{performance targets, availability, security level}

## Out of Scope
{explicitly list what this feature does NOT cover}

## Open Questions
{anything unclear that needs a decision}
TMPL

  # Replace placeholders using Python str.replace — treats values as literals,
  # safe against feature/project names containing / | & or other metacharacters.
  SDD_CONTEXT_FILE="$CONTEXT_FILE" \
  SDD_FEATURE_NAME="$FEATURE_NAME" \
  SDD_PROJECT_NAME="$PROJECT_NAME" \
  python3 - <<'PYEOF'
import os
path = os.environ['SDD_CONTEXT_FILE']
with open(path) as f:
    content = f.read()
content = content.replace('FEATURE_PLACEHOLDER', os.environ['SDD_FEATURE_NAME'])
content = content.replace('PROJECT_PLACEHOLDER', os.environ['SDD_PROJECT_NAME'])
with open(path, 'w') as f:
    f.write(content)
PYEOF

  echo "  ✓  .specify/contexts/${FEATURE_NAME}.md created"
else
  echo "  ✓  .specify/contexts/${FEATURE_NAME}.md already exists — skipped"
fi

# --- Create feature output directory ---
mkdir -p ".specify/features/${FEATURE_NAME}"
echo "  ✓  .specify/features/${FEATURE_NAME}/ ready"

# --- Done ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo ""
echo "  1. Edit .specify/contexts/${FEATURE_NAME}.md"
echo "     Fill in: What it does, actors, flows, tech stack, NFRs"
echo "     (or run /create-context to build it interactively)"
echo ""
echo "  2. Open this folder in your AI tool and run /specify"
echo ""
echo "     Claude Code  →  type:  /specify"
echo "     Copilot      →  type:  /specify"
echo "     Cursor       →  chat:  Read and follow .github/prompts/specify.prompt.md exactly"
echo "     Windsurf     →  chat:  Run specify"
echo "     Any AI       →  paste the contents of .github/prompts/specify.prompt.md"
echo ""
echo "  See QUICKSTART.md for the complete guide."
echo ""
