#!/usr/bin/env bash
# _shared/package.sh — Build distributable zip for each SDD pack
#
# What it does:
#   1. Runs sync-blocks.sh  → ensures all shared content is current in every pack
#   2. Zips each sdd-* pack → dist/{pack-name}.zip (self-contained, no _shared/)
#
# Usage:
#   cd packs/_shared && ./package.sh              # zips → packs/dist/
#   cd packs/_shared && ./package.sh /tmp/out     # zips → /tmp/out/
#   cd anywhere      && bash packs/_shared/package.sh [output-dir]
#
# Output zip contains only the pack directory (e.g. sdd-backend-service/)
# with these paths excluded:
#   CLAUDE.local.md          — gitignored personal preferences, never ship
#   .git/                    — git internals
#
# The zip is fully self-contained: a user unzips and has everything needed
# to run the pack. _shared/ is a maintainer tool and is NOT included.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKS_DIR="$(dirname "$SCRIPT_DIR")"
DIST="${1:-$PACKS_DIR/dist}"

echo "=== SDD Pack Builder ==="
echo ""

# ── Step 1: Sync shared content ──────────────────────────────────────────────
echo "Step 1/2  Syncing shared content..."
"$SCRIPT_DIR/sync-blocks.sh"
echo ""

# ── Step 2: Package each pack ─────────────────────────────────────────────────
echo "Step 2/2  Packaging packs → $DIST/"
mkdir -p "$DIST"
cd "$PACKS_DIR"

PASS=0
FAIL=0

for pack_dir in sdd-*/; do
  name="${pack_dir%/}"
  zipfile="$DIST/$name.zip"

  rm -f "$zipfile"

  if zip -rq "$zipfile" "$name" \
       --exclude "$name/.git/*" \
       --exclude "$name/CLAUDE.local.md" 2>/dev/null; then
    size=$(du -sh "$zipfile" | cut -f1)
    echo "  ✓  $name.zip  ($size)"
    PASS=$((PASS + 1))
  else
    echo "  ✗  $name  — zip failed" >&2
    FAIL=$((FAIL + 1))
  fi
done

echo ""
echo "=== Done: $PASS packed, $FAIL failed ==="
echo ""
ls -lh "$DIST/"*.zip 2>/dev/null || true

# Exit non-zero if any pack failed
[ "$FAIL" -eq 0 ]
