# Unit tests for dashboard_comments.py -- the pure-local-mode fallback that
# lets `sdd review check`/`sdd review apply` discover and acknowledge
# dashboard-left review comments when there's no Jira ticket to poll.
# Run from repo root: pytest cli-python/tests -q
import json
from pathlib import Path

from sdd.utils.dashboard_comments import all_comments, unacknowledged, acknowledge


def _write_comments(root: Path, feature: str, doc: str, entries: list[dict]) -> None:
    (root / ".specify").mkdir(parents=True, exist_ok=True)
    path = root / ".specify" / ".dashboard-comments.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data[f"{feature}/{doc}"] = entries
    path.write_text(json.dumps(data))


class TestAllComments:
    def test_no_file_returns_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert all_comments("auth", "brd") == []

    def test_returns_entries_for_the_given_feature_doc_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_comments(tmp_path, "auth", "brd", [
            {"by": "PO", "text": "please clarify §2", "at": "2026-07-01T10:00:00+00:00"},
        ])
        assert len(all_comments("auth", "brd")) == 1
        assert all_comments("auth", "srd") == []
        assert all_comments("billing", "brd") == []

    def test_malformed_file_does_not_crash(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify").mkdir(parents=True)
        (tmp_path / ".specify" / ".dashboard-comments.json").write_text("{not json")
        assert all_comments("auth", "brd") == []


class TestUnacknowledged:
    def test_never_acked_returns_everything(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_comments(tmp_path, "auth", "brd", [
            {"by": "PO", "text": "fix this", "at": "2026-07-01T10:00:00+00:00"},
            {"by": "PO", "text": "and this", "at": "2026-07-01T11:00:00+00:00"},
        ])
        assert len(unacknowledged("auth", "brd")) == 2

    def test_acked_comments_are_excluded(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_comments(tmp_path, "auth", "brd", [
            {"by": "PO", "text": "fix this", "at": "2026-07-01T10:00:00+00:00"},
        ])
        acknowledge("auth", "brd")
        assert unacknowledged("auth", "brd") == []

    def test_comments_left_after_acknowledge_still_show_up(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_comments(tmp_path, "auth", "brd", [
            {"by": "PO", "text": "first round", "at": "2000-01-01T10:00:00+00:00"},
        ])
        acknowledge("auth", "brd")  # ack timestamp is real "now" -- after the fixture's fake past date
        _write_comments(tmp_path, "auth", "brd", [
            {"by": "PO", "text": "first round", "at": "2000-01-01T10:00:00+00:00"},
            {"by": "PO", "text": "second round", "at": "2999-01-01T10:00:00+00:00"},
        ])
        remaining = unacknowledged("auth", "brd")
        assert len(remaining) == 1
        assert remaining[0]["text"] == "second round"

    def test_acknowledgement_is_scoped_per_feature_and_doc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_comments(tmp_path, "auth", "brd", [{"by": "PO", "text": "x", "at": "2026-07-01T10:00:00+00:00"}])
        _write_comments(tmp_path, "auth", "srd", [{"by": "PO", "text": "y", "at": "2026-07-01T10:00:00+00:00"}])
        acknowledge("auth", "brd")
        assert unacknowledged("auth", "brd") == []
        assert len(unacknowledged("auth", "srd")) == 1


class TestAcknowledge:
    def test_writes_the_ack_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        acknowledge("auth", "brd")
        ack_path = tmp_path / ".specify" / ".dashboard-comments-ack.json"
        assert ack_path.exists()
        data = json.loads(ack_path.read_text())
        assert "auth/brd" in data
