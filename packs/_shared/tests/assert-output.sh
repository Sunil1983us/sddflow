#!/usr/bin/env bash
# Prompt regression harness — structural assertions on SDD output documents.
#
# Usage:
#   bash packs/_shared/tests/assert-output.sh <feature-dir> [scope]
#
# Arguments:
#   feature-dir   Path to .specify/features/{feature}/ directory
#   scope         pilot | mvp | full  (default: pilot)
#
# Examples:
#   bash packs/_shared/tests/assert-output.sh \
#        examples/todo-api/.specify/features/task-management pilot
#
# What this catches:
#   - AI-generated documents that are missing required structural markers
#     (BO-NNN, FR-NNN, UC-NNN, Satisfies:, MoSCoW headings, Mermaid blocks)
#   - Broken traceability: tasks that do not reference FR-NNN
#   - Incomplete spec: use cases without Given/When/Then acceptance scenarios
#   - Sign-off documents missing approval markers
#
# Run this after each /specify or /task to detect prompt drift (model updates
# changing output structure) before users encounter it.

set -euo pipefail

FEATURE_DIR="${1:?Usage: assert-output.sh <feature-dir> [pilot|mvp|full]}"
SCOPE="${2:-pilot}"
PASS=0
FAIL=0

# ── helpers ──────────────────────────────────────────────────────────────────

_file="$FEATURE_DIR"

check() {
  # check <label> <file> <pattern> [<description>]
  local label="$1" file="$_file/$2" pattern="$3" desc="${4:-}"
  printf "  %-52s" "$label"
  if [[ ! -f "$file" ]]; then
    echo "SKIP (file absent)"; return
  fi
  if grep -qE "$pattern" "$file" 2>/dev/null; then
    echo "PASS"; PASS=$((PASS+1))
  else
    echo "FAIL — pattern not found: $pattern${desc:+ ($desc)}"; FAIL=$((FAIL+1))
  fi
}

check_file() {
  # check_file <label> <file>  — just check existence
  local label="$1" file="$_file/$2"
  printf "  %-52s" "$label"
  if [[ -f "$file" ]]; then
    echo "PASS"; PASS=$((PASS+1))
  else
    echo "FAIL — file missing"; FAIL=$((FAIL+1))
  fi
}

check_tasks_traceability() {
  # Every TASK-NNN block must have a "Satisfies: FR-" line.
  local file="$_file/tasks.md"
  printf "  %-52s" "tasks.md — every TASK has Satisfies: FR-"
  if [[ ! -f "$file" ]]; then echo "SKIP (file absent)"; return; fi

  local task_count satisfies_count
  task_count=$(grep -cE '^## TASK-[0-9]+' "$file" || true)
  satisfies_count=$(grep -cE '\*\*Satisfies:\*\*.*FR-[0-9]+|\bSatisfies:.*FR-[0-9]+' "$file" || true)

  if [[ "$task_count" -eq 0 ]]; then
    echo "FAIL — no TASK-NNN blocks found"; FAIL=$((FAIL+1))
  elif [[ "$satisfies_count" -ge "$task_count" ]]; then
    echo "PASS ($task_count tasks, $satisfies_count Satisfies lines)"; PASS=$((PASS+1))
  else
    echo "FAIL — $task_count tasks but only $satisfies_count Satisfies: FR- lines"; FAIL=$((FAIL+1))
  fi
}

check_gwt() {
  # srd.md must have Given/When/Then acceptance scenarios inside each UC.
  local file="$_file/srd.md"
  printf "  %-52s" "srd.md — Given/When/Then in use cases"
  if [[ ! -f "$file" ]]; then echo "SKIP (file absent)"; return; fi

  local uc_count gwt_count
  uc_count=$(grep -cE '^### UC-[0-9]+' "$file" || true)
  # Count lines that contain a Given/When/Then cell in a table row
  gwt_count=$(grep -cE 'Given|When|Then' "$file" || true)

  if [[ "$uc_count" -eq 0 ]]; then
    echo "FAIL — no UC-NNN use cases found"; FAIL=$((FAIL+1))
  elif [[ "$gwt_count" -gt 0 ]]; then
    echo "PASS ($uc_count UCs, $gwt_count Given/When/Then lines)"; PASS=$((PASS+1))
  else
    echo "FAIL — $uc_count use cases but no Given/When/Then content"; FAIL=$((FAIL+1))
  fi
}

check_mermaid() {
  local file="$_file/design.md"
  printf "  %-52s" "design.md — contains Mermaid diagram"
  if [[ ! -f "$file" ]]; then echo "SKIP (file absent)"; return; fi
  if grep -q '```mermaid' "$file"; then
    echo "PASS"; PASS=$((PASS+1))
  else
    echo "FAIL — no \`\`\`mermaid block found"; FAIL=$((FAIL+1))
  fi
}

check_moscow() {
  local file="$_file/stories.md"
  printf "  %-52s" "stories.md — MoSCoW headings present"
  if [[ ! -f "$file" ]]; then echo "SKIP (file absent)"; return; fi
  if grep -qE '## Must Have|## Should Have|## Could Have|## Won.t Have' "$file"; then
    echo "PASS"; PASS=$((PASS+1))
  else
    echo "FAIL — no MoSCoW section headings found"; FAIL=$((FAIL+1))
  fi
}

check_sign_off() {
  local file="$_file/$1" label="$2"
  printf "  %-52s" "$label"
  if [[ ! -f "$file" ]]; then echo "SKIP (file absent)"; return; fi
  if grep -qiE 'APPROVED|SIGN-OFF|PASSED|GO\b' "$file"; then
    echo "PASS"; PASS=$((PASS+1))
  else
    echo "FAIL — no APPROVED/PASSED/GO marker found"; FAIL=$((FAIL+1))
  fi
}

# ── pilot-scope checks ────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SDD output assertions — scope: $SCOPE"
echo "  Directory: $FEATURE_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "File presence (pilot scope):"
check_file "brd.md exists"           "brd.md"
check_file "srd.md exists"           "srd.md"
check_file "validate.md exists"      "validate.md"
check_file "analyze.md exists"       "analyze.md"
check_file "clarify.md exists"       "clarify.md"
check_file "design.md exists"          "design.md"
check_file "lld.md exists (mvp+)"        "lld.md"
check_file "stories.md exists"       "stories.md"
check_file "tasks.md exists"         "tasks.md"
check_file "release.md exists"       "release.md"

echo ""
echo "brd.md — structural markers:"
check "brd.md has BO-NNN objective"  "brd.md" "BO-[0-9]+"
check "brd.md has BR-NNN requirement" "brd.md" "BR-[0-9]+"
check "brd.md has MUST priority"     "brd.md" "MUST|Must Have|must"

echo ""
echo "srd.md — structural markers:"
check "srd.md has FR-NNN requirement" "srd.md" "FR-[0-9]+"
check "srd.md has NFR-NNN requirement" "srd.md" "NFR-[0-9]+"
check "srd.md has UC-NNN use case"   "srd.md" "UC-[0-9]+"
check_gwt

echo ""
echo "validate.md — sign-off:"
check_sign_off "validate.md" "validate.md — APPROVED/PASSED gate"
check "validate.md has Product Owner" "validate.md" "Product Owner"

echo ""
echo "analyze.md — structural markers:"
check "analyze.md has risk register"  "analyze.md" "R-[0-9]+"
check "analyze.md has severity"       "analyze.md" "HIGH|MEDIUM|LOW|CRITICAL"
check "analyze.md has CF-NNN finding" "analyze.md" "CF-[0-9]+"

echo ""
echo "stories.md — structural markers:"
check "stories.md has STORY-NNN"      "stories.md" "STORY-[0-9]+"
check "stories.md has Satisfies: FR-" "stories.md" "Satisfies:.*FR-[0-9]+"
check_moscow

echo ""
echo "tasks.md — traceability:"
check "tasks.md has TASK-NNN"         "tasks.md" "TASK-[0-9]+"
check_tasks_traceability

echo ""
echo "design.md — diagrams:"
check_mermaid

echo ""
echo "release.md — go/no-go:"
check_sign_off "release.md" "release.md — GO decision"
check "release.md has UAT scenarios"  "release.md" "UAT-[0-9]+"
check "release.md closes BO-NNN"      "release.md" "BO-[0-9]+"

# ── mvp+ checks ──────────────────────────────────────────────────────────────

if [[ "$SCOPE" == "mvp" || "$SCOPE" == "full" ]]; then
  echo ""
  echo "MVP+ scope additional checks:"
  check_file "use-cases.md exists"          "use-cases.md"
  check_file "data-model.md exists"  "data-model.md"
  check_file "lld.md exists"         "lld.md"
  check_file "adr.md exists"         "adr.md"
fi

if [[ "$SCOPE" == "full" ]]; then
  echo ""
  echo "Full scope additional checks:"
  check_file "resilience.md exists"        "resilience.md"
  check_file "security-design.md exists"   "security-design.md"
fi

# ── results ──────────────────────────────────────────────────────────────────

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
