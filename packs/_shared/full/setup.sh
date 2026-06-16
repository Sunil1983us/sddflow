#!/usr/bin/env bash
# SDD Framework — Project Initializer
# Usage: bash setup.sh [--project <name>] [--scope pilot|mvp|full] [--feature <name>]
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_NAME="$2"; shift 2;;
    --scope)   SCOPE="$2";        shift 2;;
    --feature) FEATURE_NAME="$2"; shift 2;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done

# --- Interactive prompts for anything not supplied ---
if [[ -z "$PROJECT_NAME" ]]; then
  read -r -p "Project name (e.g. my-payments-api): " PROJECT_NAME
fi

if [[ -z "$FEATURE_NAME" ]]; then
  read -r -p "First feature name (e.g. user-authentication): " FEATURE_NAME
fi

if [[ -z "$SCOPE" ]]; then
  echo ""
  echo "Scope:"
  echo "  pilot  — quick prototype, minimal docs (brd, srd, security-design §1)"
  echo "  mvp    — production-ready (+ api-spec, data-model, security-design §1-2)"
  echo "  full   — enterprise (+ resilience, investigation, security-design §1-4)"
  read -r -p "Scope [pilot]: " SCOPE
  SCOPE="${SCOPE:-pilot}"
fi

echo ""
echo "Setting up:"
echo "  Project : $PROJECT_NAME"
echo "  Feature : $FEATURE_NAME"
echo "  Scope   : $SCOPE"
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
