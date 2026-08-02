#!/usr/bin/env bash
# Fixture tests for sdd-universal/setup.sh's detect_project_type().
#
# Run from the repo root:  bash packs/_shared/tests/test-detect-fixtures.sh
#
# The same ~20 fixtures are mirrored in cli-python/tests/test_detect.py and
# cli/tests/detect.test.js, so all three implementations are asserted
# against identical inputs. detect_project_type() is extracted from
# setup.sh via sed (function body only) rather than sourcing the whole
# script, since the rest of setup.sh has side effects (arg parsing,
# prompts) this suite doesn't want to trigger.
#
# setup.ps1 has the equivalent fix (see Detect-ProjectType) but isn't
# exercised here -- there's no pwsh available in every environment this
# suite runs in. Windows CI (windows-setup-smoke-test in ci.yml) at least
# validates setup.ps1 parses and runs; it does not currently run these
# same fixtures.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SETUP_SH="$REPO_ROOT/packs/sdd-universal/setup.sh"
PASS=0
FAIL=0

# Extract just the detect_project_type() function body -- sourcing the
# whole script would run its arg-parsing/prompt logic too.
eval "$(sed -n '/^detect_project_type()/,/^}/p' "$SETUP_SH")"

# fixture "name" "expected_type" "relpath1=content1" "relpath2=content2" ...
fixture() {
  local name="$1" expected="$2"; shift 2
  local tmpdir
  tmpdir=$(mktemp -d)
  local spec
  for spec in "$@"; do
    local relpath="${spec%%=*}"
    local content="${spec#*=}"
    mkdir -p "$(dirname "$tmpdir/$relpath")"
    printf '%s' "$content" > "$tmpdir/$relpath"
  done

  local actual
  actual=$(detect_project_type "$tmpdir")
  rm -rf "$tmpdir"

  printf "  %-42s" "$name"
  if [[ "$actual" == "$expected" ]]; then
    echo "PASS"; PASS=$((PASS+1))
  else
    echo "FAIL (expected '$expected', got '$actual')"; FAIL=$((FAIL+1))
  fi
}

pkg() {
  # pkg 'dep1' 'dep2' ... -> {"dependencies": {"dep1": "x", "dep2": "x", ...}}
  local body="" first=1
  for d in "$@"; do
    [[ $first -eq 0 ]] && body+=","
    body+="\"$d\": \"x\""
    first=0
  done
  echo "{\"dependencies\": {$body}}"
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SDD Framework — detect_project_type() fixture tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

fixture "flutter" "mobile" \
  "pubspec.yaml=name: demo"

fixture "react-native" "mobile" \
  "package.json=$(pkg react-native)"

fixture "expo" "mobile" \
  "package.json=$(pkg expo)"

fixture "react-native-web-is-not-mobile" "frontend-spa" \
  "package.json=$(pkg react-native-web react)"

fixture "react-native-plus-backend-monorepo" "mobile" \
  "package.json=$(pkg react-native)" \
  "pom.xml=<project></project>"

fixture "js-frontend-plus-backend" "fullstack" \
  "package.json=$(pkg react)" \
  "pom.xml=<project></project>"

fixture "electron" "desktop" \
  "package.json=$(pkg electron)"

fixture "react" "frontend-spa" \
  "package.json=$(pkg react)"

fixture "vue" "frontend-spa" \
  "package.json=$(pkg vue)"

fixture "angular-scoped-packages" "frontend-spa" \
  "package.json=$(pkg @angular/core @angular/common)"

fixture "sveltekit" "frontend-spa" \
  "package.json=$(pkg svelte @sveltejs/kit)"

fixture "tauri" "desktop" \
  "tauri.conf.json={}"

fixture "serverless" "serverless" \
  "serverless.yml=service: demo"

fixture "terraform" "iac" \
  "main.tf=resource \"null_resource\" \"x\" {}"

fixture "rust-cli" "cli" \
  "Cargo.toml=[package]
name = \"demo\"

[[bin]]
name = \"demo\""

fixture "rust-library" "library" \
  "Cargo.toml=[package]
name = \"demo\""

fixture "go-cli" "cli" \
  "go.mod=module demo" \
  "cmd/main.go=package main"

fixture "go-backend" "backend-service" \
  "go.mod=module demo"

fixture "python-ml" "data-ml" \
  "requirements.txt=pandas>=2.0.0
numpy>=1.24.0"

fixture "python-library" "library" \
  "pyproject.toml=[project]
name = 'demo'
build-backend = 'hatchling'"

fixture "python-backend" "backend-service" \
  "requirements.txt=click>=8.0.0"

fixture "java-backend" "backend-service" \
  "pom.xml=<project></project>"

fixture "empty" ""

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
