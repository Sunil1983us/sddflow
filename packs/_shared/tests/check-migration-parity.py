#!/usr/bin/env python3
"""Migration-chain parity check between the two CLIs' `sdd upgrade`
implementations.

Background: `cli-python/sdd/commands/upgrade.py` and
`cli/src/commands/upgrade.js` each hand-maintain their own `MIGRATIONS`
list (a Python list of dicts / a JS array of objects) recording every
`sdd_version` hop this framework has ever shipped. Every version bump
requires appending a matching entry to both by hand.

A full audit (see this repo's CHANGELOG/PR history around the v3.4.0
"single migration catalogue" investigation) found the two lists' prose
content -- `description`/`notes` -- has genuinely, *intentionally*
diverged for the majority of historical entries: each CLI's notes
sometimes call out CLI-specific implementation detail (e.g. the Node
CLI's initial-release note mentions "uses js-yaml"; the Python CLI's
mentions "Python CLI added alongside Node.js CLI"). Retroactively forcing
159 historical entries into one byte-identical text was judged not worth
the risk of silently discarding real historical context for what is,
after all, just prose shown to a user running `sdd upgrade` -- so this
repo keeps two lists, not one.

What actually matters for correctness -- and what this script checks --
is narrower and load-bearing: the **version chain** itself. Both CLIs'
`_pending_migrations()`/`pendingMigrations()` walk their own list as a
linked list of `from -> to` hops to decide what a project needs applied.
If the two chains ever silently diverged (a missing hop, a version typo,
hops in a different order), one CLI could migrate a project through a
different sequence than the other -- exactly the kind of bug that's easy
to introduce by hand-editing two files and easy to miss in review, since
nothing else would look wrong.

This script parses both files' MIGRATIONS list far enough to extract just
the ordered (from, to) pairs -- not the prose, which is expected to
differ -- and asserts the two chains are identical.

Usage:
    python3 packs/_shared/tests/check-migration-parity.py [--verbose]

Exit code 0 if the chains match; 1 otherwise (message on stderr says
exactly where they diverge).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # packs/_shared/tests/ -> repo root
PY_UPGRADE = ROOT / "cli-python" / "sdd" / "commands" / "upgrade.py"
JS_UPGRADE = ROOT / "cli" / "src" / "commands" / "upgrade.js"


def _extract_python_chain(path: Path) -> list[tuple[str | None, str]]:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "MIGRATIONS"
        ):
            data = ast.literal_eval(node.value)
            return [(m["from"], m["to"]) for m in data]
    raise RuntimeError(f"No `MIGRATIONS: list[...] = [...]` assignment found in {path}")


# Matches each `{ from: 'x', ... to: 'y', ... }` object's from/to pair in
# source order, without needing a JS engine. Deliberately doesn't parse
# description/notes -- those are expected to differ (see module
# docstring) and JS string concatenation (`'a' + 'b'`) isn't valid JSON,
# so a full-fidelity parse isn't worth it for two fields.
_JS_ENTRY_RE = re.compile(
    r"from:\s*(?:null|'([^']*)')\s*,[^\n]*\n\s*to:\s*'([^']*)'",
)


def _extract_js_chain(path: Path) -> list[tuple[str | None, str]]:
    text = path.read_text()
    start = text.index("const MIGRATIONS")
    end = text.index("\n];\n", start)
    body = text[start:end]
    pairs = _JS_ENTRY_RE.findall(body)
    if not pairs:
        raise RuntimeError(f"No MIGRATIONS entries matched in {path}")
    return [(f or None, t) for f, t in pairs]


def main() -> int:
    verbose = "--verbose" in sys.argv

    py_chain = _extract_python_chain(PY_UPGRADE)
    js_chain = _extract_js_chain(JS_UPGRADE)

    ok = True

    if len(py_chain) != len(js_chain):
        print(
            f"✗  Entry count differs: {PY_UPGRADE} has {len(py_chain)}, "
            f"{JS_UPGRADE} has {len(js_chain)}",
            file=sys.stderr,
        )
        ok = False

    for i, (py_hop, js_hop) in enumerate(zip(py_chain, js_chain)):
        if py_hop != js_hop:
            print(
                f"✗  Chain diverges at entry {i}: "
                f"upgrade.py has {py_hop!r}, upgrade.js has {js_hop!r}",
                file=sys.stderr,
            )
            ok = False
        elif verbose:
            print(f"  ok   {py_hop[0]!r} -> {py_hop[1]!r}")

    # Extra entries on the longer side, past where zip() stopped.
    longer, shorter, label = (
        (py_chain, js_chain, "upgrade.py")
        if len(py_chain) > len(js_chain)
        else (js_chain, py_chain, "upgrade.js")
    )
    if len(longer) > len(shorter):
        for hop in longer[len(shorter) :]:
            print(f"✗  {label} has an extra entry not present in the other: {hop!r}", file=sys.stderr)
            ok = False

    if ok:
        print(f"✓ Migration chains match: {len(py_chain)} entries, upgrade.py == upgrade.js.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
