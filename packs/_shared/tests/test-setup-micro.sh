#!/usr/bin/env bash
# Smoke tests for sdd-micro/setup.sh
#
# Run from the repo root:  bash packs/_shared/tests/test-setup-micro.sh
#
# sdd-micro/setup.sh has a materially different arg surface from
# sdd-universal's (--project/--feature only, no --type/--scope, its own
# defaulting-to-"untitled-project"/"main" fallback for non-interactive runs
# with no args) — test-setup.sh never exercises it (it's hardcoded to
# packs/sdd-universal), so this file exists to cover the same injection
# classes and the non-interactive-default path specific to this script.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PACK_DIR="$REPO_ROOT/packs/sdd-micro"
PASS=0
FAIL=0

# ── helpers ──────────────────────────────────────────────────────────────────

_run_setup() {
  # Run setup.sh with supplied args inside a temp copy of the pack.
  # Stdout/stderr suppressed. Prints tmpdir path on stdout. Returns setup exit code.
  local tmpdir
  tmpdir=$(mktemp -d)
  cp -r "$PACK_DIR/." "$tmpdir/"
  pushd "$tmpdir" > /dev/null
  # stdin from /dev/null: tests always exercise the non-interactive path,
  # even when the suite itself is run from a terminal.
  bash setup.sh "$@" < /dev/null > /dev/null 2>&1
  local rc=$?
  popd > /dev/null
  echo "$tmpdir"
  return $rc
}

_assert_manifest() {
  # Validates that manifest.yml's 3 required fields are filled.
  local manifest="$1"
  SDD_MANIFEST="$manifest" python3 - <<'PYEOF'
import re, os, sys
txt = open(os.environ['SDD_MANIFEST']).read()
errors = []
if not re.search(r'name:\s*"[^"]+"', txt):         errors.append("name still empty")
if not re.search(r'feature:\s*"[^"]+"', txt):      errors.append("feature still empty")
if re.search(r'context_file:\s*""', txt):          errors.append("context_file still empty")
if errors:
    print("  manifest errors: " + ", ".join(errors)); sys.exit(1)
PYEOF
}

_assert_context() {
  # Validates that the context file exists and has no unsubstituted PLACEHOLDERs.
  local contexts_dir="$1"
  local ctx
  ctx=$(find "$contexts_dir" -name "*.md" 2>/dev/null | head -1)
  if [[ -z "$ctx" ]]; then
    echo "  context file not created"; return 1
  fi
  if grep -q 'PLACEHOLDER' "$ctx"; then
    echo "  PLACEHOLDER text remains in: $ctx"; return 1
  fi
}

# Runs setup, expects SUCCESS, validates outputs.
ok() {
  local label="$1"; shift
  printf "  %-48s" "$label"
  local tmpdir exit_code=0
  tmpdir=$(_run_setup "$@") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    echo "FAIL (setup exited $exit_code)"; FAIL=$((FAIL+1)); rm -rf "$tmpdir"; return
  fi
  if ! _assert_manifest "$tmpdir/.specify/manifest.yml" 2>&1; then
    FAIL=$((FAIL+1)); rm -rf "$tmpdir"; return
  fi
  if ! _assert_context "$tmpdir/.specify/contexts" 2>&1; then
    FAIL=$((FAIL+1)); rm -rf "$tmpdir"; return
  fi
  echo "PASS"; PASS=$((PASS+1))
  rm -rf "$tmpdir"
}

# Runs setup, expects FAILURE (non-zero exit = input rejected).
nok() {
  local label="$1"; shift
  printf "  %-48s" "$label (expect reject)"
  local tmpdir exit_code=0
  tmpdir=$(_run_setup "$@") || exit_code=$?
  rm -rf "$tmpdir"
  if [[ $exit_code -eq 0 ]]; then
    echo "FAIL (should have been rejected)"; FAIL=$((FAIL+1))
  else
    echo "PASS"; PASS=$((PASS+1))
  fi
}

# ── test cases ────────────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SDD Micro — setup.sh smoke tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Happy paths — setup must complete + produce valid manifest:"

ok "simple names"                 --project "hello-world"         --feature "greeter"
ok "hyphenated names"             --project "my-cli-tool"         --feature "arg-parser"
ok "slash in feature name"        --project "my-script"           --feature "utils/formatter"
ok "single quote in project"      --project "O'Brien's Script"    --feature "main"
ok "backslash in project"         --project 'path\to\script'      --feature "init"
ok "ampersand in project"         --project "Fetch & Parse"       --feature "loader"
ok "spaces in names"              --project "my little script"    --feature "the runner"
ok "unicode in names"             --project "café-script"         --feature "résumé-cleaner"
ok "no args (non-interactive default)"

echo ""
echo "Rejection paths — setup must exit non-zero (invalid YAML input):"

nok "double quote in project"     --project 'my"script'           --feature "feature"
nok "double quote in feature"     --project "my-script"           --feature 'main"loop'
nok "unknown option"              --type "backend-service"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  Results: %d passed" "$PASS"
if [[ $FAIL -gt 0 ]]; then
  printf ", %d FAILED" "$FAIL"
fi
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

[[ $FAIL -eq 0 ]]
