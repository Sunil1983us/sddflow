# Input validation for project/feature names.
from pathlib import Path

_INVALID_CHARS = ['"']


def validate_name(value: str, label: str) -> str | None:
    """Return an error message string, or None if valid."""
    if not value or not value.strip():
        return f"{label} cannot be empty."
    for ch in _INVALID_CHARS:
        if ch in value:
            return (
                f"{label} cannot contain double-quote characters — "
                "they break YAML string serialization. Please use a different name."
            )
    return None


def assert_valid_name(value: str, label: str) -> None:
    error = validate_name(value, label)
    if error:
        raise ValueError(error)


def safe_feature_path(base: Path, feature_name: str) -> Path:
    """Return base / feature_name, raising ValueError if feature_name escapes base."""
    if not feature_name:
        raise ValueError(
            "feature name is empty — pass --feature or set project.feature in manifest.yml"
        )
    resolved = (base / feature_name).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError:
        raise ValueError(
            f"feature name '{feature_name}' is invalid — path escapes the features directory"
        )
    return base / feature_name


# Documents that describe something singular for the whole service, not one
# feature — generated once, then extended/amended by every later feature
# instead of being regenerated per feature. See living-doc-update shared block.
LIVING_SERVICE_DOCS = {"data-model", "security-design", "api-spec"}


def resolve_doc_path(doc: str, feature_name: str) -> Path:
    """Resolve the on-disk path for a doc key.

    - Living/service-level docs (LIVING_SERVICE_DOCS) -> .specify/service/{doc}.md
    - "context" -> .specify/contexts/{feature}.md
    - Everything else -> .specify/features/{feature}/{doc}.md (traversal-checked)
    """
    if doc in LIVING_SERVICE_DOCS:
        return Path(".specify") / "service" / f"{doc}.md"
    if doc == "context":
        return safe_feature_path(Path(".specify") / "contexts", f"{feature_name}.md")
    return safe_feature_path(Path(".specify") / "features", feature_name) / f"{doc}.md"
