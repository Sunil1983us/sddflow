# Unit tests for sdd.utils.confluence_push_log -- the record that lets
# `sdd confluence push`/`verify` tell "this page was edited outside
# sddflow since our last push" apart from a normal re-push.
from __future__ import annotations

import pytest
import yaml

from sdd.utils.confluence_push_log import check_drift, load_push_log, record_push


class TestLoadPushLog:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert load_push_log(tmp_path / "nope.yml") == {}

    def test_corrupt_yaml_returns_empty_dict_not_raise(self, tmp_path):
        path = tmp_path / "push-log.yml"
        path.write_text("not: valid: yaml: [")
        assert load_push_log(path) == {}

    def test_non_dict_yaml_returns_empty_dict(self, tmp_path):
        path = tmp_path / "push-log.yml"
        path.write_text("- just\n- a\n- list\n")
        assert load_push_log(path) == {}

    def test_round_trips_a_real_record(self, tmp_path):
        path = tmp_path / "push-log.yml"
        record_push("123", "hld", "Feature — HLD", 3, path=path)
        data = load_push_log(path)
        assert data == {
            "123": {"doc": "hld", "title": "Feature — HLD", "pushed_version": 3}
        }


class TestRecordPush:
    def test_creates_parent_directories(self, tmp_path):
        path = tmp_path / "docs" / "confluence" / "push-log.yml"
        record_push("1", "brd", "BRD", 1, path=path)
        assert path.exists()

    def test_overwrites_prior_entry_for_same_page_id(self, tmp_path):
        path = tmp_path / "push-log.yml"
        record_push("1", "brd", "BRD", 1, path=path)
        record_push("1", "brd", "BRD", 2, path=path)
        data = load_push_log(path)
        assert data["1"]["pushed_version"] == 2
        assert len(data) == 1

    def test_preserves_other_page_ids(self, tmp_path):
        path = tmp_path / "push-log.yml"
        record_push("1", "brd", "BRD", 1, path=path)
        record_push("2", "hld", "HLD", 1, path=path)
        data = load_push_log(path)
        assert set(data) == {"1", "2"}

    def test_written_file_is_valid_yaml_with_a_header_comment(self, tmp_path):
        path = tmp_path / "push-log.yml"
        record_push("1", "brd", "BRD", 1, path=path)
        text = path.read_text()
        assert text.startswith("#")
        assert yaml.safe_load(text) == {
            "1": {"doc": "brd", "title": "BRD", "pushed_version": 1}
        }


class TestCheckDrift:
    def test_never_pushed_before_is_not_drift(self):
        page = {"id": "1", "version": {"number": 5}}
        assert check_drift(page, {}) is None

    def test_version_unchanged_is_not_drift(self):
        page = {"id": "1", "version": {"number": 2}}
        log = {"1": {"doc": "brd", "pushed_version": 2}}
        assert check_drift(page, log) is None

    def test_version_moved_is_drift(self):
        page = {
            "id": "1",
            "version": {
                "number": 4,
                "by": {"displayName": "Jane Reviewer"},
                "when": "2026-03-01T10:00:00.000Z",
            },
        }
        log = {"1": {"doc": "brd", "pushed_version": 2}}
        drift = check_drift(page, log)
        assert drift == {
            "by": "Jane Reviewer",
            "when": "2026-03-01",
            "pushed_version": 2,
            "live_version": 4,
        }

    def test_missing_version_number_is_not_drift(self):
        """Malformed/unexpected API response shape -- treated as nothing
        to warn about rather than raising, matching this module's
        never-raise contract."""
        page = {"id": "1", "version": {}}
        log = {"1": {"doc": "brd", "pushed_version": 2}}
        assert check_drift(page, log) is None

    def test_missing_by_defaults_to_someone(self):
        page = {"id": "1", "version": {"number": 3, "when": "2026-01-01"}}
        log = {"1": {"doc": "brd", "pushed_version": 2}}
        drift = check_drift(page, log)
        assert drift["by"] == "someone"


@pytest.mark.parametrize("bad_id", ["", None])
def test_check_drift_handles_missing_page_id(bad_id):
    page = {"id": bad_id, "version": {"number": 1}} if bad_id is not None else {}
    assert check_drift(page, {"1": {"pushed_version": 1}}) is None
