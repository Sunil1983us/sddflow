"""sdd-universal project_type semantics: the canonical type list (reused
from detect.py), which type-specific extended docs each type uses, and
what changes when a project migrates from one type to another.

This is sdd-universal-specific -- the other 4 packs (backend-service,
frontend-spa, mobile, fullstack) each ship one fixed tech stack and have
no project_type field in their manifest.yml at all. Only sdd-universal's
manifest carries project_type, and only it needs to migrate between types.
"""

from __future__ import annotations

from dataclasses import dataclass

from sdd.utils.detect import PROJECT_TYPES

# Which of the type-specific extended docs (component-spec / ux-flow /
# screen-spec) each project_type generates -- mirrors the Action 2 doc-set
# table in sdd-universal's specify.prompt.md. Types absent from this map
# (backend-service, cli, data-ml, serverless, library, iac) use none of
# these three -- they're non-UI project types.
#
# This is the single source of truth for this mapping -- sdd/utils/status.py
# (the dashboard's "Living Documents"/pipeline builder) imports it from here
# rather than keeping its own copy, so the two can never drift apart.
EXTENDED_DOCS_BY_TYPE: dict[str, frozenset[str]] = {
    "frontend-spa": frozenset({"component-spec", "ux-flow"}),
    "desktop": frozenset({"component-spec", "ux-flow"}),
    "mobile": frozenset({"screen-spec", "ux-flow"}),
    "fullstack": frozenset({"component-spec", "ux-flow"}),
}


def applicable_extended_docs(project_type: str | None) -> frozenset[str]:
    """Which of component-spec/ux-flow/screen-spec this project_type uses.
    None or an unrecognized type -> empty set, not an error -- callers
    treat "no extended docs" as the safe default."""
    if project_type is None:
        return frozenset()
    return EXTENDED_DOCS_BY_TYPE.get(project_type, frozenset())


@dataclass(frozen=True)
class MigrationReport:
    from_type: str
    to_type: str
    added_docs: frozenset[str]  # extended docs the target type adds
    dropped_docs: frozenset[str]  # extended docs the target type drops
    is_lossy: bool  # True if dropped_docs is non-empty

    def render(self) -> str:
        lines = [f"project_type: {self.from_type} -> {self.to_type}"]
        if self.added_docs:
            lines.append("  + newly applicable: " + ", ".join(sorted(self.added_docs)))
        if self.dropped_docs:
            lines.append(
                "  - no longer applicable: " + ", ".join(sorted(self.dropped_docs))
            )
            lines.append(
                "    (any of these already generated under "
                f"{self.from_type} stay exactly where they are on disk -- "
                "nothing is deleted. They just stop being listed as "
                "expected/upcoming pipeline steps for future features "
                "under the new type.)"
            )
        if not self.added_docs and not self.dropped_docs:
            lines.append("  no change to which extended docs apply")
        lines.append(
            "  constitution.md Tech Stack table is NOT touched by this "
            "command -- extend it separately (e.g. via /change, change "
            "type Technical) to cover the new type's stack."
        )
        return "\n".join(lines)


def classify_migration(from_type: str | None, to_type: str) -> MigrationReport:
    """Compares the extended-doc applicability of two project_types. Does
    NOT inspect constitution.md content -- Tech Stack row compatibility
    can't be determined mechanically, so that part is always left as a
    manual/agent-guided step regardless of classification here."""
    from_docs = applicable_extended_docs(from_type)
    to_docs = applicable_extended_docs(to_type)
    return MigrationReport(
        from_type=from_type or "(unset)",
        to_type=to_type,
        added_docs=to_docs - from_docs,
        dropped_docs=from_docs - to_docs,
        is_lossy=bool(from_docs - to_docs),
    )


def is_valid_project_type(value: str) -> bool:
    return value in PROJECT_TYPES
