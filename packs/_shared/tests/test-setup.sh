#!/usr/bin/env bash
# Smoke tests for sdd-universal/setup.sh
#
# Run from the repo root:  bash packs/_shared/tests/test-setup.sh
#
# Covers every injection class fixed in the code review:
#   - single quote in project/feature name  (was: python3 -c path injection)
#   - slash in feature name                 (was: sed delimiter collision)
#   - backslash/ampersand in names          (was: re.sub via unquoted heredoc)
#   - double quote in name                  (should be rejected — invalid YAML)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PACK_DIR="$REPO_ROOT/packs/sdd-universal"
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
  # Validates that manifest.yml is fully filled and valid.
  local manifest="$1"
  SDD_MANIFEST="$manifest" python3 - <<'PYEOF'
import re, os, sys
txt = open(os.environ['SDD_MANIFEST']).read()
errors = []
if not re.search(r'name:\s*"[^"]+"', txt):         errors.append("name still empty")
if not re.search(r'feature:\s*"[^"]+"', txt):      errors.append("feature still empty")
if re.search(r'context_file:\s*""', txt):          errors.append("context_file still empty")
if re.search(r'project_type:\s*"auto"', txt):      errors.append("project_type still auto")
if errors:
    print("  manifest errors: " + ", ".join(errors)); sys.exit(1)
PYEOF
}

_assert_scope() {
  # Validates manifest.yml's scope: field equals the expected canonical
  # value -- used for the alias-resolution tests, where the CLI is given
  # a friendly name (lean/standard/regulated) and must never persist it
  # as-is (manifest.yml's own schema only ever stores pilot/mvp/full).
  local manifest="$1" expected="$2"
  if ! grep -q "scope: \"$expected\"" "$manifest"; then
    echo "  scope mismatch: expected \"$expected\" not found in $manifest"
    return 1
  fi
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

# Runs setup, expects SUCCESS, and that --scope resolved to $2 (canonical).
ok_scope() {
  local label="$1" expected_scope="$2"; shift 2
  printf "  %-48s" "$label"
  local tmpdir exit_code=0
  tmpdir=$(_run_setup "$@") || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    echo "FAIL (setup exited $exit_code)"; FAIL=$((FAIL+1)); rm -rf "$tmpdir"; return
  fi
  if ! _assert_manifest "$tmpdir/.specify/manifest.yml" 2>&1; then
    FAIL=$((FAIL+1)); rm -rf "$tmpdir"; return
  fi
  if ! _assert_scope "$tmpdir/.specify/manifest.yml" "$expected_scope" 2>&1; then
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
echo "  SDD Framework — setup.sh smoke tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Happy paths — setup must complete + produce valid manifest:"

ok "simple names"                 --project "my-payments-api"    --feature "user-authentication"  --scope pilot --type backend-service
ok "hyphenated names"             --project "order-service"       --feature "checkout-flow"         --scope mvp   --type backend-service
ok "slash in feature name"        --project "my-api"              --feature "auth/oauth"            --scope pilot --type backend-service
ok "single quote in project"      --project "O'Brien's API"       --feature "login"                 --scope pilot --type backend-service
ok "backslash in project"         --project 'path\to\service'     --feature "init"                  --scope pilot --type cli
ok "ampersand in project"         --project "Payments & Billing"  --feature "invoice"               --scope pilot --type fullstack
ok "spaces in names"              --project "my payments api"     --feature "user auth"             --scope pilot --type frontend-spa
ok "unicode in names"             --project "café-service"        --feature "résumé-upload"         --scope pilot --type backend-service
ok "mobile type"                  --project "my-app"              --feature "onboarding"            --scope pilot --type mobile
ok "fullstack mvp scope"          --project "my-platform"         --feature "dashboard"             --scope mvp   --type fullstack
ok "data-ml type"                 --project "ml-pipeline"         --feature "model-training"        --scope pilot --type data-ml
ok "serverless type"              --project "lambda-api"          --feature "event-processor"       --scope pilot --type serverless
ok "iac type"                     --project "infra-prod"          --feature "vpc-setup"             --scope pilot --type iac

echo ""
echo "Scope aliases — --scope <alias> must resolve to the canonical name:"

ok_scope "lean resolves to pilot"      "pilot" --project "alias-lean"      --feature "checkout" --scope lean      --type backend-service
ok_scope "standard resolves to mvp"    "mvp"   --project "alias-standard"  --feature "checkout" --scope standard  --type backend-service
ok_scope "regulated resolves to full"  "full"  --project "alias-regulated" --feature "checkout" --scope regulated --type backend-service

echo ""
echo "Rejection paths — setup must exit non-zero (invalid YAML input):"

nok "double quote in project"     --project 'my"project'          --feature "feature"              --scope pilot --type backend-service
nok "double quote in feature"     --project "my-project"          --feature 'auth"oauth'           --scope pilot --type backend-service
nok "unrecognized scope value"    --project "my-project"          --feature "feature"              --scope not-a-real-scope --type backend-service

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
