# Unit tests for the Claude Code session-transcript reader that powers
# `sdd token-log` -- real, measured token usage instead of the char/4
# estimate, but only discoverable when running under Claude Code itself.
import json
from datetime import datetime, timezone
from pathlib import Path

from sdd.utils.claude_code_transcript import (
    ModelUsage,
    _sanitize_cwd,
    claude_projects_dir,
    find_session_transcripts,
    sum_usage_since,
)


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")


def _assistant_entry(
    model: str,
    timestamp: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation: int = 0,
    cache_read: int = 0,
) -> dict:
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
            },
        },
    }


class TestModelUsage:
    def test_billed_input_tokens_sums_all_three_input_buckets(self):
        u = ModelUsage(
            input_tokens=100, cache_creation_input_tokens=50, cache_read_input_tokens=25
        )
        assert u.billed_input_tokens == 175


class TestSanitizeCwd:
    def test_replaces_every_slash_with_dash(self):
        assert (
            _sanitize_cwd(Path("/home/user/Universalguide"))
            == "-home-user-Universalguide"
        )


class TestFindSessionTranscripts:
    def test_returns_none_when_project_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "sdd.utils.claude_code_transcript.claude_projects_dir",
            lambda: tmp_path / "nonexistent",
        )
        main, subagents = find_session_transcripts(cwd=tmp_path / "myproject")
        assert main is None
        assert subagents == []

    def test_picks_most_recently_modified_top_level_jsonl(self, tmp_path, monkeypatch):
        projects_root = tmp_path / "claude-projects"
        monkeypatch.setattr(
            "sdd.utils.claude_code_transcript.claude_projects_dir",
            lambda: projects_root,
        )
        cwd = tmp_path / "myproject"
        project_dir = projects_root / _sanitize_cwd(cwd)
        older = project_dir / "session-old.jsonl"
        newer = project_dir / "session-new.jsonl"
        _write_jsonl(older, [])
        _write_jsonl(newer, [])
        # Force distinguishable mtimes regardless of filesystem timestamp resolution
        import os, time

        os.utime(older, (1000, 1000))
        os.utime(newer, (2000, 2000))

        main, _ = find_session_transcripts(cwd=cwd)
        assert main == newer

    def test_finds_subagent_transcripts_for_the_chosen_session(
        self, tmp_path, monkeypatch
    ):
        projects_root = tmp_path / "claude-projects"
        monkeypatch.setattr(
            "sdd.utils.claude_code_transcript.claude_projects_dir",
            lambda: projects_root,
        )
        cwd = tmp_path / "myproject"
        project_dir = projects_root / _sanitize_cwd(cwd)
        session = project_dir / "session-abc.jsonl"
        _write_jsonl(session, [])
        sub1 = project_dir / "session-abc" / "subagents" / "agent-1.jsonl"
        sub2 = project_dir / "session-abc" / "subagents" / "agent-2.jsonl"
        _write_jsonl(sub1, [])
        _write_jsonl(sub2, [])

        main, subagents = find_session_transcripts(cwd=cwd)
        assert main == session
        assert set(subagents) == {sub1, sub2}

    def test_no_subagents_dir_returns_empty_list(self, tmp_path, monkeypatch):
        projects_root = tmp_path / "claude-projects"
        monkeypatch.setattr(
            "sdd.utils.claude_code_transcript.claude_projects_dir",
            lambda: projects_root,
        )
        cwd = tmp_path / "myproject"
        project_dir = projects_root / _sanitize_cwd(cwd)
        session = project_dir / "session-abc.jsonl"
        _write_jsonl(session, [])

        main, subagents = find_session_transcripts(cwd=cwd)
        assert main == session
        assert subagents == []


class TestSumUsageSince:
    def test_sums_multiple_turns_same_model(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_jsonl(
            f,
            [
                _assistant_entry("claude-sonnet-5", "2026-07-14T10:00:00Z", 100, 50),
                _assistant_entry("claude-sonnet-5", "2026-07-14T10:05:00Z", 200, 75),
            ],
        )
        result = sum_usage_since([f], since=None)
        assert result["claude-sonnet-5"].input_tokens == 300
        assert result["claude-sonnet-5"].output_tokens == 125
        assert result["claude-sonnet-5"].turns == 2

    def test_buckets_by_model_separately(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_jsonl(
            f,
            [
                _assistant_entry("claude-sonnet-5", "2026-07-14T10:00:00Z", 100, 50),
                _assistant_entry("claude-haiku-4-5", "2026-07-14T10:01:00Z", 20, 5),
            ],
        )
        result = sum_usage_since([f], since=None)
        assert set(result) == {"claude-sonnet-5", "claude-haiku-4-5"}
        assert result["claude-haiku-4-5"].input_tokens == 20

    def test_since_filters_out_earlier_turns(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_jsonl(
            f,
            [
                _assistant_entry("claude-sonnet-5", "2026-07-14T09:00:00Z", 999, 999),
                _assistant_entry("claude-sonnet-5", "2026-07-14T11:00:00Z", 100, 50),
            ],
        )
        since = datetime(2026, 7, 14, 10, 0, 0, tzinfo=timezone.utc)
        result = sum_usage_since([f], since=since)
        assert result["claude-sonnet-5"].input_tokens == 100
        assert result["claude-sonnet-5"].turns == 1

    def test_none_since_includes_everything(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_jsonl(
            f, [_assistant_entry("claude-sonnet-5", "2026-01-01T00:00:00Z", 1, 1)]
        )
        result = sum_usage_since([f], since=None)
        assert result["claude-sonnet-5"].turns == 1

    def test_ignores_non_assistant_entries(self, tmp_path):
        f = tmp_path / "t.jsonl"
        f.write_text(
            json.dumps({"type": "user", "timestamp": "2026-07-14T10:00:00Z"}) + "\n"
        )
        result = sum_usage_since([f], since=None)
        assert result == {}

    def test_ignores_assistant_entries_with_no_usage(self, tmp_path):
        f = tmp_path / "t.jsonl"
        f.write_text(
            json.dumps(
                {
                    "type": "assistant",
                    "timestamp": "2026-07-14T10:00:00Z",
                    "message": {"model": "claude-sonnet-5"},
                }
            )
            + "\n"
        )
        result = sum_usage_since([f], since=None)
        assert result == {}

    def test_skips_malformed_lines_without_raising(self, tmp_path):
        f = tmp_path / "t.jsonl"
        f.write_text(
            "not json at all\n"
            + json.dumps(
                _assistant_entry("claude-sonnet-5", "2026-07-14T10:00:00Z", 5, 5)
            )
            + "\n"
            + "{broken\n"
        )
        result = sum_usage_since([f], since=None)
        assert result["claude-sonnet-5"].input_tokens == 5

    def test_missing_file_is_skipped_not_fatal(self, tmp_path):
        result = sum_usage_since([tmp_path / "does-not-exist.jsonl"], since=None)
        assert result == {}

    def test_sums_across_multiple_files_same_model(self, tmp_path):
        f1 = tmp_path / "main.jsonl"
        f2 = tmp_path / "sub.jsonl"
        _write_jsonl(
            f1, [_assistant_entry("claude-sonnet-5", "2026-07-14T10:00:00Z", 100, 50)]
        )
        _write_jsonl(
            f2, [_assistant_entry("claude-sonnet-5", "2026-07-14T10:00:00Z", 30, 10)]
        )
        result = sum_usage_since([f1, f2], since=None)
        assert result["claude-sonnet-5"].input_tokens == 130
        assert result["claude-sonnet-5"].output_tokens == 60

    def test_cache_tokens_are_tracked_separately_from_input_tokens(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_jsonl(
            f,
            [
                _assistant_entry(
                    "claude-sonnet-5",
                    "2026-07-14T10:00:00Z",
                    input_tokens=100,
                    output_tokens=50,
                    cache_creation=2000,
                    cache_read=500,
                )
            ],
        )
        result = sum_usage_since([f], since=None)
        u = result["claude-sonnet-5"]
        assert u.input_tokens == 100
        assert u.cache_creation_input_tokens == 2000
        assert u.cache_read_input_tokens == 500
        assert u.billed_input_tokens == 2600
