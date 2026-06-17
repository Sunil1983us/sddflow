# Input validation for project/feature names.

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
