#!/usr/bin/env bash
# SDD Micro — Project Initializer
# Usage: bash setup.sh [--project <name>] [--feature <name>]
# Run this once after copying the pack into your project directory.

set -euo pipefail

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SDD Micro — Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --- Parse optional CLI args ---
PROJECT_NAME=""
FEATURE_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)    PROJECT_NAME="$2"; shift 2;;
    --feature)    FEATURE_NAME="$2"; shift 2;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done

# When stdin is not a terminal (CI, piped input, automation), `read` hits EOF
# and set -e aborts the script — so prompt only when interactive: unsupplied
# values fall back to a generic default rather than failing, since sdd-micro
# is meant to be usable with zero ceremony.
if [ -t 0 ]; then INTERACTIVE=1; else INTERACTIVE=0; fi

if [[ -z "$PROJECT_NAME" ]]; then
  if [[ $INTERACTIVE -eq 1 ]]; then
    read -r -p "Project name (e.g. hello-world): " PROJECT_NAME
  fi
  PROJECT_NAME="${PROJECT_NAME:-untitled-project}"
fi

if [[ -z "$FEATURE_NAME" ]]; then
  if [[ $INTERACTIVE -eq 1 ]]; then
    read -r -p "Feature name (e.g. greeter): " FEATURE_NAME
  fi
  FEATURE_NAME="${FEATURE_NAME:-main}"
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
echo "  Project : $PROJECT_NAME"
echo "  Feature : $FEATURE_NAME"
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
  SDD_FEATURE_NAME="$FEATURE_NAME" \
  python3 - <<'PYEOF'
import re, os
manifest     = os.environ['SDD_MANIFEST']
project_name = os.environ['SDD_PROJECT_NAME']
feature_name = os.environ['SDD_FEATURE_NAME']
with open(manifest) as f:
    content = f.read()
content = re.sub(r'name:\s*""',         lambda _: f'name: "{project_name}"',            content, count=1)
content = re.sub(r'feature:\s*""',      lambda _: f'feature: "{feature_name}"',         content, count=1)
content = re.sub(r'context_file:\s*""', lambda _: f'context_file: "{feature_name}.md"', content, count=1)
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
# Optional — you can also just describe the task to the agent in chat
# at /specify. Fill this file only if you'd rather have it written down.

## What This Does
{1-3 sentences}

## Tech Stack

| Concern | Choice |
|---|---|
| Language | {e.g. Python 3.12} |
| Framework/Library | {e.g. none} |
| Run Command | {e.g. python greet.py} |
| Test/Verify Command | {e.g. pytest, or "manual run"} |
| Storage | {e.g. none — stateless} |

## Ground Rules
{anything you want followed — optional}

## Out of Scope
{optional}
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
echo "  1. (Optional) Edit .specify/contexts/${FEATURE_NAME}.md"
echo "     — or just describe the task in chat, see below"
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
