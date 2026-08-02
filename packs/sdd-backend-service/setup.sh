#!/usr/bin/env bash
# SDD Framework — Project Initializer
# Usage: bash setup.sh [--project <name>] [--scope pilot|mvp|full] [--feature <name>] [--plan-mode unified|separate] [--reading-mode auto|summary|full]
# Run this once after copying the pack into your project directory.

set -euo pipefail

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SDD Framework — Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --- Parse optional CLI args ---
PROJECT_NAME=""
SCOPE=""
FEATURE_NAME=""

PLAN_MODE=""
READING_MODE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)      PROJECT_NAME="$2"; shift 2;;
    --scope)        SCOPE="$2";        shift 2;;
    --feature)      FEATURE_NAME="$2"; shift 2;;
    --plan-mode)    PLAN_MODE="$2";    shift 2;;
    --reading-mode) READING_MODE="$2"; shift 2;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done

# --- Interactive prompts for anything not supplied ---
# When stdin is not a terminal (CI, piped input, automation), `read` hits EOF
# and set -e aborts the script — so prompt only when interactive: optional
# values fall back to their defaults, required ones fail fast with a hint.
if [ -t 0 ]; then INTERACTIVE=1; else INTERACTIVE=0; fi

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
    echo "  pilot  (lean)       — quick prototype, minimal docs (brd, srd, security-design §1)"
    echo "  mvp    (standard)   — production-ready (+ api-spec, data-model, security-design §1-2)"
    echo "  full   (regulated)  — enterprise (+ resilience, investigation, security-design §1-4)"
    read -r -p "Scope [pilot]: " SCOPE
  fi
  SCOPE="${SCOPE:-pilot}"
fi

# Friendly aliases -- manifest.yml's own schema only ever stores
# pilot/mvp/full (every gate/command in every pack checks for those three
# exact values), so aliases are normalized here, before anything is
# written, rather than teaching every downstream check about them.
case "$SCOPE" in
  lean)      SCOPE="pilot" ;;
  standard)  SCOPE="mvp" ;;
  regulated) SCOPE="full" ;;
esac
if [[ "$SCOPE" != "pilot" && "$SCOPE" != "mvp" && "$SCOPE" != "full" ]]; then
  echo "  ✗  Invalid --scope '$SCOPE' — must be one of: pilot (lean), mvp (standard), full (regulated)" >&2
  exit 1
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

if [[ -z "$READING_MODE" ]]; then
  if [[ $INTERACTIVE -eq 1 ]]; then
    echo ""
    echo "Document reading mode (token economy — see summary-rules.md):"
    echo "  auto    — use each doc's .summary.md when present, fall back to the"
    echo "            full document (and generate a summary) when it's missing."
    echo "            Good for: almost everyone — self-heals, never stuck."
    echo "  summary — always use .summary.md; warns instead of reading the full"
    echo "            doc if one is missing. Good for: strict token budgets."
    echo "  full    — always read the full document, every command. Good for:"
    echo "            deep debugging, or migrating a project with no summaries."
    read -r -p "Reading mode [auto]: " READING_MODE
  fi
  READING_MODE="${READING_MODE:-auto}"
fi

echo ""
echo "Setting up:"
echo "  Project      : $PROJECT_NAME"
echo "  Feature      : $FEATURE_NAME"
echo "  Scope        : $SCOPE"
echo "  Plan mode    : $PLAN_MODE"
echo "  Reading mode : $READING_MODE"
echo ""

# --- Update manifest.yml ---
MANIFEST=".specify/manifest.yml"
if [[ -f "$MANIFEST" ]]; then
  # Use Python for reliable in-place YAML value substitution (avoids sed cross-platform issues)
  python3 - <<PYEOF
import re, sys
with open("$MANIFEST") as f:
    content = f.read()
content = re.sub(r'name:\s*""', 'name: "$PROJECT_NAME"', content)
content = re.sub(r'scope:\s*"pilot"', 'scope: "$SCOPE"', content)
content = re.sub(r'feature:\s*""', 'feature: "$FEATURE_NAME"', content)
content = re.sub(r'context_file:\s*""', 'context_file: "$FEATURE_NAME.md"', content)
content = re.sub(r'plan_mode:\s*"unified"', 'plan_mode: "$PLAN_MODE"', content)
content = re.sub(r'reading_mode:\s*"auto"', 'reading_mode: "$READING_MODE"', content)
with open("$MANIFEST", "w") as f:
    f.write(content)
PYEOF
  echo "  ✓  .specify/manifest.yml filled"
else
  echo "  ✗  .specify/manifest.yml not found — are you in the pack root?" >&2
  exit 1
fi

# --- Create contexts directory + placeholder ---
mkdir -p ".specify/contexts"
CONTEXT_FILE=".specify/contexts/${FEATURE_NAME}.md"
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
  # Replace placeholders
  sed -i.bak \
    -e "s/FEATURE_PLACEHOLDER/${FEATURE_NAME}/" \
    -e "s/PROJECT_PLACEHOLDER/${PROJECT_NAME}/" \
    "$CONTEXT_FILE"
  rm -f "${CONTEXT_FILE}.bak"
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
