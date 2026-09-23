#!/usr/bin/env python3
"""Validate every .specify/manifest.yml in this repo against the canonical schema.

Why this exists
---------------
`yaml-validate` in CI only proves each file *parses*. It cannot catch a
manifest that is valid YAML but structurally wrong -- and that is exactly
how the `examples/todo-api` bug shipped: `project_type` was nested under
`project:` instead of sitting at the top level, so the CLI and dashboard
read it as absent and rendered `Type: -`. Nothing failed; it just quietly
showed the wrong thing.

The same example also declared no `plan_mode`, so it defaulted to
`unified` while shipping `arch.md` + `hld.md` (the `separate`-mode
artifacts). The dashboard struck Architecture and HLD through as
"skipped" in the pipeline while listing them as Approved in the document
table directly below -- two contradictory claims on one screen.

This checker closes both classes:
  1. key placement + enum values (schema shape)
  2. plan_mode agreeing with the documents actually on disk (semantics)

Usage:
    python3 packs/_shared/tests/check-manifest-schema.py [--verbose]

Exit code 0 = all manifests conform, 1 = at least one failure.
Notes (version drift) are reported but never fail the build.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - CI installs pyyaml
    print("ERROR: PyYAML is required. pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)


REPO_ROOT = Path(__file__).resolve().parents[3]

# Canonical enums. Sourced from packs/sdd-universal/.specify/manifest.yml,
# which is the reference manifest every other pack is a subset of.
ENUMS: dict[str, set[str]] = {
    "scope": {"pilot", "mvp", "full"},
    "project_type": {
        "auto",
        "backend-service",
        "frontend-spa",
        "mobile",
        "fullstack",
        "cli",
        "data-ml",
        "serverless",
        "library",
        "iac",
        "desktop",
    },
    "plan_mode": {"unified", "separate"},
    "reading_mode": {"auto", "summary", "full"},
    "testing_style": {"paired", "tdd", "bdd"},
    "workflow_mode": {"github", "local"},
}

# Keys that belong at the TOP level of the manifest, never inside `project:`.
# `project_type` is listed first because nesting it is the bug this file was
# written for.
TOP_LEVEL_ONLY = (
    "project_type",
    "plan_mode",
    "reading_mode",
    "testing_style",
    "workflow_mode",
    "sdd_version",
    "pack",
    "ai_tool",
    "pr_rules",
)

# Keys that belong INSIDE `project:`, never at the top level.
PROJECT_SCOPED_ONLY = ("name", "feature", "context_file", "feature_display_name")

# Artifacts each plan_mode is expected to produce, checked only against a
# real feature directory (a pack template has none).
PLAN_MODE_ARTIFACTS = {
    "separate": ("arch.md", "hld.md"),
    "unified": ("design.md",),
}


class Result:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []
        self.checked = 0

    def fail(self, path: Path, msg: str) -> None:
        self.failures.append(f"{path.relative_to(REPO_ROOT)}: {msg}")


def feature_dirs_with_docs(manifest_path: Path) -> list[Path]:
    """Feature directories that actually contain generated documents.

    A pack template ships an empty (or absent) features/ directory, so this
    returning [] is how we tell "unfilled scaffold" from "real project".
    """
    features = manifest_path.parent / "features"
    if not features.is_dir():
        return []
    return [d for d in sorted(features.iterdir()) if d.is_dir() and any(d.glob("*.md"))]


def check_manifest(path: Path, result: Result) -> None:
    result.checked += 1
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        result.fail(path, f"invalid YAML: {exc}")
        return

    if not isinstance(data, dict):
        result.fail(path, "top level is not a mapping")
        return

    project = data.get("project")
    if not isinstance(project, dict):
        result.fail(path, "missing required `project:` mapping")
        return

    # --- key placement -------------------------------------------------
    for key in TOP_LEVEL_ONLY:
        if key in project:
            result.fail(
                path,
                f"`{key}` is nested under `project:` but belongs at the top "
                f"level -- the CLI and dashboard read it from the top level "
                f"and will treat it as absent here",
            )
    for key in PROJECT_SCOPED_ONLY:
        if key in data:
            result.fail(
                path,
                f"`{key}` is at the top level but belongs inside `project:`",
            )

    # --- required keys -------------------------------------------------
    for key in ("name", "feature"):
        if key not in project:
            result.fail(path, f"`project.{key}` is missing")
    for key in ("sdd_version", "pack"):
        if key not in data:
            result.fail(path, f"`{key}` is missing")

    pr_rules = data.get("pr_rules")
    if not isinstance(pr_rules, dict):
        result.fail(path, "missing required `pr_rules:` mapping")
    else:
        for key in ("max_lines_per_pr", "max_files_per_pr"):
            if not isinstance(pr_rules.get(key), int):
                result.fail(path, f"`pr_rules.{key}` must be an integer")

    # --- enum values ---------------------------------------------------
    # `scope` lives inside project:, everything else at the top level.
    if "scope" in project and project["scope"] not in ENUMS["scope"]:
        result.fail(
            path,
            f"`project.scope` is {project['scope']!r}; expected one of "
            f"{sorted(ENUMS['scope'])}",
        )
    for key, allowed in ENUMS.items():
        if key == "scope":
            continue
        if key in data and data[key] not in allowed:
            result.fail(
                path,
                f"`{key}` is {data[key]!r}; expected one of {sorted(allowed)}",
            )

    # --- plan_mode agrees with the documents on disk --------------------
    # Only meaningful for a real project. A pack template has no features.
    plan_mode = data.get("plan_mode")
    for feature_dir in feature_dirs_with_docs(path):
        present = {p.name for p in feature_dir.glob("*.md")}
        has_separate = {"arch.md", "hld.md"} & present
        has_unified = "design.md" in present

        if plan_mode is None and (has_separate or has_unified):
            actual = "separate" if has_separate else "unified"
            result.fail(
                path,
                f"no `plan_mode` declared, so it defaults to 'unified', but "
                f"{feature_dir.name}/ ships {sorted(has_separate) or ['design.md']} "
                f'-- declare `plan_mode: "{actual}"`',
            )
            continue

        expected = PLAN_MODE_ARTIFACTS.get(plan_mode or "unified", ())
        missing = [name for name in expected if name not in present]
        if missing:
            result.fail(
                path,
                f"`plan_mode: {plan_mode or 'unified'}` expects "
                f"{list(expected)} in {feature_dir.name}/ but {missing} "
                f"{'is' if len(missing) == 1 else 'are'} absent",
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose", action="store_true", help="list every file checked"
    )
    args = parser.parse_args()

    manifests = sorted(
        p for p in REPO_ROOT.glob("*/**/.specify/manifest.yml") if ".git" not in p.parts
    )
    if not manifests:
        print("ERROR: no manifest.yml files found", file=sys.stderr)
        return 1

    result = Result()
    for path in manifests:
        if args.verbose:
            print(f"  checking {path.relative_to(REPO_ROOT)}")
        check_manifest(path, result)

    # Cross-manifest: flag packs whose sdd_version trails the newest one.
    versions: dict[str, str] = {}
    for path in manifests:
        if "packs" not in path.parts:
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        version = data.get("sdd_version")
        if isinstance(version, str):
            versions[str(path.relative_to(REPO_ROOT))] = version
    if versions:
        newest = max(versions.values())
        for rel, version in sorted(versions.items()):
            if version != newest:
                result.notes.append(
                    f"{rel}: sdd_version {version!r} trails the newest pack "
                    f"version {newest!r} (note only -- use the version-bump "
                    f"skill to change it)"
                )

    print()
    print(f"  Manifests checked: {result.checked}")
    for note in result.notes:
        print(f"  NOTE  {note}")
    if result.failures:
        print()
        for failure in result.failures:
            print(f"  FAIL  {failure}")
        print()
        print(f"  {len(result.failures)} failure(s)")
        return 1
    print("  All manifests conform to the canonical schema.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
