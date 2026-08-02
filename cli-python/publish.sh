#!/usr/bin/env bash
# publish.sh — bundle packs, build wheel, upload to PyPI
#
# Usage:
#   bash publish.sh             # upload to PyPI (live)
#   bash publish.sh --test      # upload to TestPyPI first (recommended first time)
#
# Prerequisites:
#   brew install uv            (replaces pip + build + twine)
#   export PYPI_TOKEN="pypi-..."     # from pypi.org → Account Settings → API tokens
#   export TEST_PYPI_TOKEN="pypi-..." # from test.pypi.org (optional, for --test)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKS_SRC="$REPO_ROOT/packs"
PACKS_DEST="$SCRIPT_DIR/sdd/packs"
TEST_MODE=false

for arg in "$@"; do
  [[ "$arg" == "--test" ]] && TEST_MODE=true
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SDD CLI — Publish to $([ "$TEST_MODE" = true ] && echo 'TestPyPI' || echo 'PyPI')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Step 1: Bundle packs ──────────────────────────────────────────────────────
echo "▶ Bundling packs..."
rm -rf "$PACKS_DEST"
mkdir -p "$PACKS_DEST"

for pack in sdd-backend-service sdd-frontend-spa sdd-fullstack sdd-mobile sdd-universal sdd-micro; do
  src="$PACKS_SRC/$pack"
  if [ -d "$src" ]; then
    cp -r "$src" "$PACKS_DEST/$pack"
    echo "  ✓  $pack"
  else
    echo "  ✗  $pack not found at $src — aborting"
    exit 1
  fi
done

# ── Step 2: Clean previous build artefacts ───────────────────────────────────
echo ""
echo "▶ Cleaning dist/..."
rm -rf "$SCRIPT_DIR/dist"

# ── Step 3: Build wheel + sdist ──────────────────────────────────────────────
echo ""
echo "▶ Building package..."
cd "$SCRIPT_DIR"
uv build
echo "  ✓  $(ls dist/*.whl 2>/dev/null | head -1 | xargs basename)"
echo "  ✓  $(ls dist/*.tar.gz 2>/dev/null | head -1 | xargs basename)"

# ── Step 3b: Verify the build actually bundled the packs ────────────────────
# Same assertion CI's package-verify job runs, repeated here so a manual
# publish can't ship a broken package even if someone runs this script
# without CI in the loop (e.g. hand-publishing from a laptop).
echo ""
echo "▶ Verifying wheel and sdist contain the bundled packs..."
python3 - <<'PYEOF'
import glob
import sys
import tarfile
import zipfile

needle = "sdd/packs/sdd-universal/setup.sh"

wheel = glob.glob("dist/*.whl")[0]
with zipfile.ZipFile(wheel) as zf:
    names = zf.namelist()
if not any(n.endswith(needle) for n in names):
    sys.exit(f"✗  {wheel} is missing {needle} -- aborting, do not upload")
print(f"  ✓  {wheel} contains {needle}")

sdist = glob.glob("dist/*.tar.gz")[0]
with tarfile.open(sdist) as tf:
    names = tf.getnames()
if not any(n.endswith(needle) for n in names):
    sys.exit(f"✗  {sdist} is missing {needle} -- aborting, do not upload")
print(f"  ✓  {sdist} contains {needle}")
PYEOF

# ── Step 4: Upload ────────────────────────────────────────────────────────────
echo ""
if [ "$TEST_MODE" = true ]; then
  echo "▶ Uploading to TestPyPI..."
  if [ -z "${TEST_PYPI_TOKEN:-}" ]; then
    echo "  ✗  TEST_PYPI_TOKEN is not set"
    echo "     export TEST_PYPI_TOKEN=\"pypi-...\""
    exit 1
  fi
  uv publish --publish-url https://test.pypi.org/legacy/ --token "$TEST_PYPI_TOKEN"
  echo ""
  echo "  Install from TestPyPI to verify:"
  echo "    uv pip install --index-url https://test.pypi.org/simple/ sddflow"
else
  echo "▶ Uploading to PyPI..."
  if [ -z "${PYPI_TOKEN:-}" ]; then
    echo "  ✗  PYPI_TOKEN is not set"
    echo "     export PYPI_TOKEN=\"pypi-...\""
    exit 1
  fi
  uv publish --token "$PYPI_TOKEN"
  echo ""
  echo "  Install with:"
  echo "    uv pip install sddflow"
  echo "  or (once pip is fixed):"
  echo "    pip install sddflow"
fi

# ── Step 5: Cleanup bundled packs (keep repo clean) ──────────────────────────
echo ""
echo "▶ Cleaning up bundled packs from source tree..."
rm -rf "$PACKS_DEST"
echo "  ✓  Cleaned"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Publish complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
