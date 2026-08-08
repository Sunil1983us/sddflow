#!/usr/bin/env bash
# Sync canonical _shared/ content into every sdd-* pack:
#  1. full/**       -> whole files with zero pack-specific content
#  2. blocks/*.md   -> marked sections within otherwise pack-specific files
# See README.md for the marker format and rules.
#
# Order matters: full-file sync MUST run before the blocks sync, not after.
# Several full/**  files (e.g. specify-brd.prompt.md, plan-design.prompt.md)
# themselves contain shared:{id} block markers -- the canonical source for
# those markers' CONTENT is blocks/{id}.md, never full/**'s own copy between
# the markers (full/** only owns the surrounding pack-agnostic prose). If the
# full-file copy ran after the blocks pass, it would silently overwrite a
# just-refreshed pack file with whatever stale content happens to be baked
# into full/**'s own marker region -- full/** files are never themselves
# touched by the blocks loop (it only globs ../sdd-*/), so any edit to
# blocks/{id}.md would then never actually reach the packs: the blocks pass
# fills the pack file correctly, then the full-file pass immediately clobbers
# it back to the stale copy. Running full-file sync first means the blocks
# pass always has the last word on every marker region, in every file,
# whichever loop last touched it.
set -euo pipefail
cd "$(dirname "$0")"

find full -type f | while read -r src; do
  rel="${src#full/}"
  for pack in ../sdd-*; do
    dest="$pack/$rel"
    # sdd-micro intentionally does not follow PACK-SPEC.md and is hand-
    # maintained, not generated from _shared/ — see PACK-SPEC.md's
    # exception note and packs/sdd-micro/CLAUDE.md. It has none of the
    # shared:{id} markers either, so the blocks loop below already skips
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

for block in blocks/*.md; do
  id=$(basename "$block" .md)
  start="<!-- shared:${id}:start -->"
  end="<!-- shared:${id}:end -->"

  # Process substitution (not a pipe) so a brand-new block with zero
  # current matches -- grep exits 1, no lines matched -- doesn't abort the
  # whole script under `set -e -o pipefail`. A pipe's exit status is the
  # rightmost non-zero stage under pipefail, so `grep | while read` would
  # fail the pipeline (and the script) even though the while loop itself
  # ran zero iterations successfully.
  while read -r file; do
    awk -v start="$start" -v end="$end" -v blockfile="$block" '
      $0 == start { print; while ((getline line < blockfile) > 0) print line; close(blockfile); skip=1; next }
      $0 == end { print; skip=0; next }
      skip { next }
      { print }
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    echo "synced $id -> $file"
  done < <(grep -rl --include="*.md" -F "$start" ../sdd-*/ 2>/dev/null || true)
done
