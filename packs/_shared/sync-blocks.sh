#!/usr/bin/env bash
# Sync canonical _shared/ content into every sdd-* pack:
#  1. blocks/*.md   -> marked sections within otherwise pack-specific files
#  2. full/**       -> whole files with zero pack-specific content
# See README.md for the marker format and rules.
set -euo pipefail
cd "$(dirname "$0")"

for block in blocks/*.md; do
  id=$(basename "$block" .md)
  start="<!-- shared:${id}:start -->"
  end="<!-- shared:${id}:end -->"

  grep -rl --include="*.md" -F "$start" ../sdd-*/ 2>/dev/null | while read -r file; do
    awk -v start="$start" -v end="$end" -v blockfile="$block" '
      $0 == start { print; while ((getline line < blockfile) > 0) print line; close(blockfile); skip=1; next }
      $0 == end { print; skip=0; next }
      skip { next }
      { print }
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    echo "synced $id -> $file"
  done
done

find full -type f | while read -r src; do
  rel="${src#full/}"
  for pack in ../sdd-*; do
    dest="$pack/$rel"
    # sdd-micro intentionally does not follow PACK-SPEC.md and is hand-
    # maintained, not generated from _shared/ — see PACK-SPEC.md's
    # exception note and packs/sdd-micro/CLAUDE.md. It has none of the
    # shared:{id} markers either, so the blocks loop above already skips
    # it; this exclusion covers the full-file loop the same way.
    if [[ "$pack" == *"sdd-micro"* ]]; then
      continue
    fi
    # sdd-universal has pack-specific setup.sh/setup.ps1 (with auto-detection)
    # that must not be overwritten by the shared base versions.
    if [[ "$pack" == *"sdd-universal"* && ( "$rel" == "setup.sh" || "$rel" == "setup.ps1" ) ]]; then
      continue
    fi
    if [ -f "$dest" ]; then
      if ! cmp -s "$src" "$dest"; then
        cp "$src" "$dest"
        echo "synced (full) $rel -> $dest"
      fi
    else
      echo "SKIP (full) $rel -> $dest  [dest missing — run: cp packs/_shared/full/$rel $dest]" >&2
    fi
  done
done
