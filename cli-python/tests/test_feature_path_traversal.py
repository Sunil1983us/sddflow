# Regression tests for the path-traversal fix: sdd confluence / sdd cr / sdd jira
# previously built .specify/features/{feature}/... paths without validating
# `feature`, unlike sdd pr / sdd review which already used safe_feature_path().
# These call the actual helper functions each command now routes through.
from pathlib import Path

import pytest

from sdd.commands.confluence import _resolve_doc_path
from sdd.commands.cr import _cr_path


def test_confluence_resolve_doc_path_rejects_traversal_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _resolve_doc_path("context", "../../../../tmp/pwned")


def test_confluence_resolve_doc_path_rejects_traversal_feature_doc(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _resolve_doc_path("hld", "../../../../tmp/pwned")


def test_confluence_resolve_doc_path_accepts_normal_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _resolve_doc_path("hld", "payments") == (
        Path(".specify") / "features" / "payments" / "hld.md"
    )
    assert _resolve_doc_path("context", "payments") == (
        Path(".specify") / "contexts" / "payments.md"
    )


def test_cr_path_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _cr_path("../../../../tmp/pwned", "CR-001")


def test_cr_path_accepts_normal_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _cr_path("payments", "CR-001") == (
        Path(".specify") / "features" / "payments" / "changesets" / "CR-001.md"
    )
