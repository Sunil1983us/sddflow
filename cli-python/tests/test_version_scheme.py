"""Regression tests for the capped X.Y.Z version scheme documented in
.claude/skills/version-bump/SKILL.md.

Background: from 2.8.0 (the scheme's introduction) through 2.8.40, 41
consecutive version bumps each did a flat `Z += 1` without ever applying
the documented carry rule (Z caps at 24 -- the 26th patch in a minor
should roll into Y += 1, Z = 0). Nothing caught it, so Z silently climbed
to 40 -- 16 past the cap -- and the 2.9.x minor was never used at all
until the drift was noticed and corrected in one jump, straight to
2.9.16. These tests exist so the next time Z or Y drifts past its cap,
the test suite fails immediately at that commit instead of the drift
accumulating unnoticed for 41 more bumps.
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


class TestCappedVersionScheme:
    """Y (minor) and Z (patch) are capped counters, not open-ended semver
    -- see the version-bump skill's "The versioning rule". Z ranges
    0-24; a 25th patch within a minor must instead be expressed as
    Y += 1, Z = 0. Y ranges 0-9 the same way against X."""

    def test_current_version_respects_the_cap(self):
        _major, minor, patch = _parse_version(SDD_VERSION)
        assert 0 <= patch <= 24, (
            f"sdd_version {SDD_VERSION!r} has patch={patch}, which exceeds "
            "the documented cap of 24 -- this is exactly the drift class "
            "that let Z climb to 40 across 2.8.0-2.8.40 unnoticed. The next "
            "bump should have carried into the next minor (Y += 1, Z = 0) "
            "instead of incrementing Z past 24."
        )
        assert 0 <= minor <= 9, (
            f"sdd_version {SDD_VERSION!r} has minor={minor}, which exceeds "
            "the documented cap of 9 -- the next bump should have carried "
            "into the next major (X += 1, Y = 0) instead."
        )

    def test_next_version_helper_never_exceeds_the_cap(self):
        """Sanity-checks the divmod formula itself (see the version-bump
        skill's `next_version`) across a wide sweep of inputs, including
        already-over-cap ones like the historical (2, 8, 40) -- the exact
        shape of the drift this test suite guards against. The formula
        must always reduce back into range regardless of how far a stale
        input has drifted past the cap."""

        def next_version(x: int, y: int, z: int) -> tuple[int, int, int]:
            n = x * 250 + y * 25 + z + 1
            x, rem = divmod(n, 250)
            y, z = divmod(rem, 25)
            return x, y, z

        # A representative sweep: in-range inputs, right at the cap
        # boundary, and inputs already past it (the historical drift
        # shape) -- every output must land back in range.
        cases = [
            (2, 8, 0),
            (2, 8, 23),
            (2, 8, 24),  # right at the cap -- next bump must carry
            (2, 8, 40),  # the actual historical drift input
            (2, 9, 24),
            (0, 0, 0),
            (5, 0, 24),
        ]
        for x, y, z in cases:
            _nx, ny, nz = next_version(x, y, z)
            assert 0 <= nz <= 24, f"next_version({x},{y},{z}) -> patch={nz}"
            assert 0 <= ny <= 9, f"next_version({x},{y},{z}) -> minor={ny}"

    def test_cap_boundary_actually_carries(self):
        """The one specific transition that silently failed to fire for
        41 consecutive bumps: incrementing past patch=24 must produce
        minor+1, patch=0 -- not patch=25."""

        def next_version(x: int, y: int, z: int) -> tuple[int, int, int]:
            n = x * 250 + y * 25 + z + 1
            x, rem = divmod(n, 250)
            y, z = divmod(rem, 25)
            return x, y, z

        assert next_version(2, 8, 24) == (2, 9, 0)


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
