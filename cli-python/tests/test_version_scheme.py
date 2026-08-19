"""Regression tests for the version scheme documented in
.claude/skills/version-bump/SKILL.md.

Current rule (since 3.0.2): standard, uncapped SemVer X.Y.Z. Which field
bumps is a deliberate classification made per-release (PATCH/MINOR/MAJOR)
by whoever runs the version-bump skill -- there's no formula to sanity-
check anymore, just well-formedness of whatever the classification
produced.

Historical note: from 2.8.0 through 3.0.2 this repo used a *capped*
counter scheme instead (Z capped at 24, Y capped at 9, with a divmod-
based carry rule) -- introduced after Z had earlier drifted to 40, 16
past its intended cap, because 41 consecutive bumps each did a flat
`Z += 1` with nothing checking the cap. That capped scheme is what this
file's tests used to enforce (`TestCappedVersionScheme`, removed here).
It was itself replaced by the uncapped SemVer rule above once it became
clear the capped scheme had the same underlying flaw as the plain-
increment scheme before it: every bump treated as equivalent regardless
of what actually shipped, carrying no signal about fix vs. feature vs.
breaking change. See CHANGELOG.md and the skill file's own "Historical
note" for the full chain. `TestVersionLockstep` below is unaffected by
any of this -- keeping 8 files in sync on one version string is orthogonal
to how that string's next value gets chosen.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from sdd import __version__ as SDD_VERSION

_REPO_ROOT = Path(__file__).resolve().parents[2]

# sdd-micro is deliberately excluded from the sdd_version lockstep -- see
# repo CLAUDE.md "Repository Layout" and the version-bump skill's own
# file list. It has its own sdd_version field, frozen independently --
# see TestVersionLockstep.test_sdd_micro_is_frozen_outside_the_lockstep.
_MANIFEST_PACKS = [
    "sdd-backend-service",
    "sdd-frontend-spa",
    "sdd-fullstack",
    "sdd-mobile",
    "sdd-universal",
]


def _parse_version(v: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v)
    assert m, f"Not a plain X.Y.Z version string: {v!r}"
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


class TestSemVerScheme:
    """Standard, uncapped SemVer -- see the version-bump skill's "The
    versioning rule". No cap on any field; which field bumps is a
    per-release classification (PATCH/MINOR/MAJOR), not a formula, so
    there's nothing here to sanity-check beyond well-formedness."""

    def test_current_version_is_well_formed_semver(self):
        major, minor, patch = _parse_version(SDD_VERSION)
        assert major >= 0 and minor >= 0 and patch >= 0, (
            f"sdd_version {SDD_VERSION!r} parsed to a negative component: "
            f"({major}, {minor}, {patch})"
        )

    def test_current_version_is_at_or_past_the_semver_rule_introduction(self):
        """The uncapped SemVer rule took effect at 3.0.2 (see this file's
        module docstring and the skill's own "Historical note") -- nothing
        before that point followed it, but nothing after should regress
        to a version below where the rule started."""
        major, minor, patch = _parse_version(SDD_VERSION)
        assert (major, minor, patch) >= (3, 0, 2), (
            f"sdd_version {SDD_VERSION!r} is below 3.0.2, where the "
            "uncapped SemVer rule took effect -- versions should only "
            "move forward."
        )


class TestVersionLockstep:
    """The version-bump skill's step 2 lists 8 files (9 counting
    sdd-micro's deliberate exclusion) that must always carry the same
    sdd_version. This was previously only checked by hand (`grep -rn` per
    the skill's own instructions) -- automating it here so a partial bump
    (one file edited, another missed) fails CI instead of shipping."""

    def test_package_json_matches(self):
        text = (_REPO_ROOT / "cli" / "package.json").read_text()
        m = re.search(r'"version"\s*:\s*"([^"]+)"', text)
        assert m, 'cli/package.json has no "version" field'
        assert m.group(1) == SDD_VERSION

    def test_pyproject_toml_matches(self):
        text = (_REPO_ROOT / "cli-python" / "pyproject.toml").read_text()
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        assert m, "cli-python/pyproject.toml has no version field"
        assert m.group(1) == SDD_VERSION

    @pytest.mark.parametrize("pack", _MANIFEST_PACKS)
    def test_pack_manifest_matches(self, pack):
        path = _REPO_ROOT / "packs" / pack / ".specify" / "manifest.yml"
        data = yaml.safe_load(path.read_text())
        assert data.get("sdd_version") == SDD_VERSION, (
            f"packs/{pack}/.specify/manifest.yml sdd_version is "
            f"{data.get('sdd_version')!r}, expected {SDD_VERSION!r}"
        )

    def test_sdd_micro_is_frozen_outside_the_lockstep(self):
        """sdd-micro has its own sdd_version field, but is deliberately
        excluded from the lockstep (see repo CLAUDE.md "Repository
        Layout" and the version-bump skill's file list) -- it's frozen
        in maintenance mode, not kept in sync with the other 5 packs.
        This just confirms the field is still present and well-formed,
        and documents that it is expected to differ from SDD_VERSION --
        a future session should not "fix" it into the lockstep by hand."""
        path = _REPO_ROOT / "packs" / "sdd-micro" / ".specify" / "manifest.yml"
        data = yaml.safe_load(path.read_text()) or {}
        assert "sdd_version" in data
        _parse_version(data["sdd_version"])  # well-formed X.Y.Z, nothing more
