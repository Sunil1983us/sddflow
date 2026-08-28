# Regression guard for a real user-reported bug: Path.read_text()/
# write_text() and open()/os.fdopen() in text mode all default to
# locale.getpreferredencoding(False) when `encoding=` is omitted -- on
# Windows (and any non-UTF-8 locale) that's typically cp1252, not UTF-8.
# A markdown file containing an em-dash ("—", UTF-8 bytes E2 80 94)
# read that way comes back mis-decoded as "â€”" (each byte
# reinterpreted as a separate cp1252 character) -- exactly the mojibake a
# user saw in a Confluence page pushed from a /create-context-generated
# context.md.
#
# The fix touched ~20 files across the whole read/write surface (see the
# version-bump migration entry for the full list). This test is a static
# AST scan, not a runtime locale simulation, because monkeypatching
# locale.getpreferredencoding does not reliably intercept the C-level
# encoding resolution inside io.TextIOWrapper across Python versions --
# an AST check that every relevant call site passes encoding= explicitly
# is deterministic and catches a regression the moment a new call site is
# added without it, rather than only when someone happens to run on a
# non-UTF-8-locale machine with non-ASCII content.
from __future__ import annotations

import ast
from pathlib import Path

SDD_ROOT = Path(__file__).parent.parent / "sdd"

# Method names on any object (Path, a file-like, etc.) that read/write
# text and take an `encoding` keyword.
_TEXT_METHODS = {"read_text", "write_text"}
# Bare function calls (not methods) that open a file in text mode.
_TEXT_OPEN_FUNCS = {"open", "fdopen"}


def _has_encoding_kwarg(call: ast.Call) -> bool:
    return any(kw.arg == "encoding" for kw in call.keywords)


def _is_binary_mode(call: ast.Call) -> bool:
    """True if a positional/keyword mode argument contains 'b' -- binary
    opens (rb/wb/ab) correctly have no `encoding=` and aren't a bug."""
    args = list(call.args)
    mode_arg = None
    if len(args) >= 2:
        mode_arg = args[1]
    for kw in call.keywords:
        if kw.arg == "mode":
            mode_arg = kw.value
    if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
        return "b" in mode_arg.value
    return False


def _find_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Attribute) and func.attr in _TEXT_METHODS:
            name = func.attr
        elif isinstance(func, ast.Name) and func.id in _TEXT_OPEN_FUNCS:
            name = func.id
        elif (
            isinstance(func, ast.Attribute)
            and func.attr == "fdopen"
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
        ):
            name = "os.fdopen"
        if name is None:
            continue
        is_open_call = name in _TEXT_OPEN_FUNCS or name == "os.fdopen"
        if is_open_call and _is_binary_mode(node):
            continue
        if not _has_encoding_kwarg(node):
            violations.append(f"{path}:{node.lineno}: {name}() missing encoding=")
    return violations


def test_every_text_file_io_call_specifies_utf8_encoding():
    violations: list[str] = []
    for py_file in sorted(SDD_ROOT.rglob("*.py")):
        violations.extend(_find_violations(py_file))
    assert not violations, (
        "Found file I/O call(s) with no explicit encoding= -- these fall "
        "back to the OS locale's default encoding (cp1252 on many Windows "
        "setups), which mangles any non-ASCII character on read/write:\n"
        + "\n".join(violations)
    )
