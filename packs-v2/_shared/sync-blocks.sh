#!/usr/bin/env bash
# Sync canonical _shared/blocks/*.md content into marked sections of
# every sdd-* pack. See README.md for the marker format and rules.
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
