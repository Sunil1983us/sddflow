#!/usr/bin/env python3
"""Cross-reference linter — catches dead structural pointers between prompt
files before a user does.

Two real bugs shipped this way and were only found because a user asked a
pointed question, not because CI caught them:
  - v2.7.88: specify-doc.prompt.md / specify-srd.prompt.md /
    orchestrate.prompt.md all pointed at "the doc-set table in
    specify.prompt.md (Action 2)" -- a heading that didn't exist in any
    pack's specify.prompt.md.
  - v2.7.89: the dashboard's "Extended Specs" step silently conflated
    several independent documents' status into one boolean.

This script targets the first bug class specifically: a prose reference to
"{file} (Action N)" or "{doc}.md §N" where the referenced heading doesn't
actually exist in the target file. It does not (and cannot) verify
*behavioral* correctness -- only that a structural pointer resolves to
something real.

Usage:
    python3 packs/_shared/tests/check-cross-references.py [--verbose]

Exit code 0 if every reference resolves; 1 if any is dead (message on
stderr names the file, line, and what didn't resolve).

Scope, deliberately:
  - Checks "Action N" references against specify.prompt.md's own
    "## Action N" headings, per pack (the only file with Action headings
    today, but the check doesn't hardcode that -- it just looks there).
  - Checks "{doc}.md §N" references against that doc's own *-template.md
    top-level "## N. ..." numbered headings, per pack (so a pack
    whose template diverges from another pack's is checked against its
    own copy, not a shared assumption).
  - Deliberately SKIPS "*.summary.md §N" references -- AI-2 summaries are
    a compressed, non-numbered digest of the source doc; there's no
    guarantee they preserve the same section numbers, so checking them
    would produce false positives, not real findings.
  - A doc key with no matching template file is reported as a note, not a
    failure -- it usually means the reference isn't to a real document at
    all (e.g. a prose example), and asserting a template *must* exist for
    every word ending in ".md" would be too strong a claim to make safely.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # packs/_shared/tests/ -> repo root
PACKS = [
    "sdd-backend-service",
    "sdd-frontend-spa",
    "sdd-mobile",
    "sdd-fullstack",
    "sdd-universal",
    "sdd-micro",
]

# doc key (as it appears in "{doc key}.md") -> template file stem, for the
# handful of docs whose physical filename doesn't match "{doc}-template.md".
TEMPLATE_STEM_OVERRIDES = {
    "local-setup": "runbook",  # docs/runbook/local-setup.md <- runbook-template.md
}

# sdd-universal only: data-model/security-design have project_type-flavored
# template variants in addition to the default -- see specify-doc.prompt.md's
# branching. Check whichever variants exist; a hit in any one counts.
FLAVOR_SUFFIXES = ["", "-frontend", "-mobile"]

ACTION_REF_RE = re.compile(r"specify\.prompt\.md[^\n]{0,60}?\(Action (\d+)\)")
SECTION_REF_RE = re.compile(r"\b([\w.-]+)\.md §(\d+)\b")
HEADING_NUM_RE = re.compile(r"^##\s+(\d+)\.", re.MULTILINE)


def _scannable_files(pack_dir: Path) -> list[Path]:
    files = list((pack_dir / ".github" / "prompts").glob("*.md"))
    claude_md = pack_dir / "CLAUDE.md"
    if claude_md.is_file():
        files.append(claude_md)
    return files


def _heading_numbers(template_path: Path) -> set[int]:
    text = template_path.read_text(errors="replace")
    return {int(m.group(1)) for m in HEADING_NUM_RE.finditer(text)}


def check_pack(pack_name: str, verbose: bool) -> list[str]:
    pack_dir = ROOT / "packs" / pack_name
    templates_dir = pack_dir / ".specify" / "templates"
    problems: list[str] = []

    for src in _scannable_files(pack_dir):
        text = src.read_text(errors="replace")
        rel = src.relative_to(ROOT)

        # -- "specify.prompt.md ... (Action N)" --
        specify_prompt = pack_dir / ".github" / "prompts" / "specify.prompt.md"
        specify_actions: set[int] | None = None
        for m in ACTION_REF_RE.finditer(text):
            n = int(m.group(1))
            if specify_actions is None:
                specify_actions = (
                    _heading_action_numbers(specify_prompt)
                    if specify_prompt.is_file() else set()
                )
            if n not in specify_actions:
                line = text.count("\n", 0, m.start()) + 1
                problems.append(
                    f"{rel}:{line}: references specify.prompt.md (Action {n}), "
                    f"but that pack's specify.prompt.md has no '## Action {n}' "
                    f"heading (found: {sorted(specify_actions) or 'none'})"
                )
            elif verbose:
                print(f"  ok   {rel}:{m.start()} -> Action {n}")

        # -- "{doc}.md §N" --
        for m in SECTION_REF_RE.finditer(text):
            doc_key, n = m.group(1), int(m.group(2))
            if doc_key.endswith("summary"):
                continue  # AI-2 summaries: no guaranteed section numbering
            stem = TEMPLATE_STEM_OVERRIDES.get(doc_key, doc_key)
            found_template = False
            numbers: set[int] = set()
            for suffix in FLAVOR_SUFFIXES:
                candidate = templates_dir / f"{stem}-template{suffix}.md"
                if candidate.is_file():
                    found_template = True
                    numbers |= _heading_numbers(candidate)
            if not found_template:
                if verbose:
                    print(f"  note {rel}: no template found for doc key "
                          f"'{doc_key}' (§{n}) -- skipping")
                continue
            if n not in numbers:
                line = text.count("\n", 0, m.start()) + 1
                problems.append(
                    f"{rel}:{line}: references {doc_key}.md §{n}, but "
                    f"{stem}-template.md has no '## {n}.' heading "
                    f"(found: {sorted(numbers) or 'none'})"
                )
            elif verbose:
                print(f"  ok   {rel}:{m.start()} -> {doc_key}.md §{n}")

    return problems


def _heading_action_numbers(prompt_path: Path) -> set[int]:
    text = prompt_path.read_text(errors="replace")
    return {int(m.group(1)) for m in re.finditer(r"^##\s+Action\s+(\d+)", text, re.MULTILINE)}


def main() -> int:
    verbose = "--verbose" in sys.argv
    all_problems: list[str] = []
    for pack in PACKS:
        all_problems.extend(check_pack(pack, verbose))

    if all_problems:
        print(f"✗ {len(all_problems)} dead cross-reference(s) found:\n", file=sys.stderr)
        for p in all_problems:
            print(f"  {p}", file=sys.stderr)
        print(file=sys.stderr)
        return 1

    print(f"✓ All cross-references resolve across {len(PACKS)} packs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
