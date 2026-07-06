# Unit tests for sdd.utils.validate — name validation and feature-path containment.
from pathlib import Path

import pytest

from sdd.utils.validate import validate_name, assert_valid_name, safe_feature_path


def test_validate_name_rejects_empty():
    assert validate_name("", "Feature") is not None
    assert validate_name("   ", "Feature") is not None


def test_validate_name_rejects_double_quote():
    assert validate_name('foo"bar', "Feature") is not None


def test_validate_name_accepts_normal_name():
    assert validate_name("payments", "Feature") is None


def test_assert_valid_name_raises_on_invalid():
    with pytest.raises(ValueError):
        assert_valid_name("", "Feature")


def test_safe_feature_path_rejects_empty():
    with pytest.raises(ValueError):
        safe_feature_path(Path(".specify") / "features", "")


def test_safe_feature_path_accepts_normal_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = safe_feature_path(Path(".specify") / "features", "payments")
    assert result == Path(".specify") / "features" / "payments"


def test_safe_feature_path_rejects_parent_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        safe_feature_path(Path(".specify") / "features", "../../../../tmp/pwned")


def test_safe_feature_path_rejects_sibling_prefix_bypass(tmp_path, monkeypatch):
    """A feature name that resolves to a sibling directory whose name merely
    starts with the same string as the base directory (e.g. base 'features',
    sibling 'features-legacy') must be rejected — a naive string-prefix
    check without a separator boundary would incorrectly allow this."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        safe_feature_path(Path(".specify") / "features", "../features-legacy")


def test_safe_feature_path_rejects_sibling_prefix_bypass_variant(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        safe_feature_path(Path(".specify") / "features", "../features_backup")
