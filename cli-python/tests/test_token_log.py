# Unit tests for `sdd token-log` -- writes REAL Claude Code token usage
# into token-usage.md, exiting with a distinct code for every reason a
# calling prompt should fall back to the char/4 estimate instead.
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd.commands.token_log import token_log_command
from sdd.utils.claude_code_transcript import ModelUsage


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specify" / "features" / "auth").mkdir(parents=True)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "templates").mkdir(parents=True)
    (tmp_path / ".specify" / "manifest.yml").write_text(
        yaml.dump({"project": {"name": "Demo", "feature": "auth"}})
    )
    template_src = (
        Path(__file__).resolve().parents[2]
        / "packs/_shared/full/.specify/templates/token-usage-template.md"
    )
    (tmp_path / ".specify" / "templates" / "token-usage-template.md").write_text(
        template_src.read_text()
    )
    return tmp_path


def _write_pricing(project, **overrides):
    models = {
        "claude-sonnet-5": {
            "input_per_million": 3.0,
            "output_per_million": 15.0,
            "last_verified": "2026-07-01",
        },
    }
    models.update(overrides)
    (project / ".specify" / "memory" / "token-pricing.yml").write_text(
        yaml.dump(
            {
                "models": models,
                "unknown_model_fallback": "n/a — add/fill in this model's rates",
            }
        )
    )


class TestGatesAndFallbackExitCodes:
    def test_exits_2_when_pricing_file_missing(self, project, runner):
        result = runner.invoke(token_log_command, ["--command", "specify-brd"])
        assert result.exit_code == 2

    def test_exits_3_when_no_transcript_found(self, project, runner):
        _write_pricing(project)
        with patch(
            "sdd.commands.token_log.find_session_transcripts", return_value=(None, [])
        ):
            result = runner.invoke(token_log_command, ["--command", "specify-brd"])
        assert result.exit_code == 3

    def test_exits_1_when_no_feature_resolvable(self, tmp_path, monkeypatch, runner):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify" / "memory").mkdir(parents=True)
        (tmp_path / ".specify" / "manifest.yml").write_text(yaml.dump({"project": {}}))
        _write_pricing(tmp_path)
        result = runner.invoke(token_log_command, ["--command", "specify-brd"])
        assert result.exit_code == 1

    def test_exits_0_when_no_new_usage_since_last_log(self, project, runner):
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value={}),
        ):
            result = runner.invoke(token_log_command, ["--command", "specify-brd"])
        assert result.exit_code == 0
        assert not (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).exists()


class TestSuccessPath:
    def test_creates_file_from_template_and_logs_real_row(self, project, runner):
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage = {
            "claude-sonnet-5": ModelUsage(input_tokens=1000, output_tokens=200, turns=3)
        }
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage),
        ):
            result = runner.invoke(token_log_command, ["--command", "specify-brd"])

        assert result.exit_code == 0, result.output
        text = (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).read_text()
        assert "Feature: auth" in text
        assert "| 1 | specify-brd | claude-sonnet-5 | 1000 | 200 |" in text
        assert "Real (Claude Code)" in text
        assert "Total Input Tokens" in text

    def test_cost_computed_from_pricing_file(self, project, runner):
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage = {
            "claude-sonnet-5": ModelUsage(
                input_tokens=1_000_000, output_tokens=1_000_000
            )
        }
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage),
        ):
            runner.invoke(token_log_command, ["--command", "specify-brd"])
        text = (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).read_text()
        # 1M input @ $3/M + 1M output @ $15/M = $18.0000
        assert "$18.0000" in text

    def test_unpriced_model_uses_fallback_string(self, project, runner):
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage = {"claude-opus-4-8": ModelUsage(input_tokens=100, output_tokens=50)}
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage),
        ):
            runner.invoke(token_log_command, ["--command", "specify-brd"])
        text = (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).read_text()
        assert "n/a — add/fill in this model's rates" in text

    def test_billed_input_includes_cache_tokens(self, project, runner):
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage = {
            "claude-sonnet-5": ModelUsage(
                input_tokens=100,
                output_tokens=50,
                cache_creation_input_tokens=900,
                cache_read_input_tokens=0,
            )
        }
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage),
        ):
            runner.invoke(token_log_command, ["--command", "specify-brd"])
        text = (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).read_text()
        assert "| 1 | specify-brd | claude-sonnet-5 | 1000 | 50 |" in text

    def test_zero_usage_synthetic_model_bucket_is_skipped(self, project, runner):
        """Some transcript entries carry a placeholder model (observed:
        '<synthetic>') with an all-zero usage object -- an internal
        Claude Code implementation detail, not real command work. Must
        not produce a noisy zero-token row."""
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage = {
            "<synthetic>": ModelUsage(input_tokens=0, output_tokens=0),
            "claude-sonnet-5": ModelUsage(input_tokens=100, output_tokens=50),
        }
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage),
        ):
            result = runner.invoke(token_log_command, ["--command", "specify-brd"])
        assert result.exit_code == 0, result.output
        text = (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).read_text()
        assert "<synthetic>" not in text
        assert "claude-sonnet-5" in text

    def test_dry_run_does_not_write_file(self, project, runner):
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage = {"claude-sonnet-5": ModelUsage(input_tokens=100, output_tokens=50)}
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage),
        ):
            result = runner.invoke(
                token_log_command, ["--command", "specify-brd", "--dry-run"]
            )
        assert result.exit_code == 0
        assert not (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).exists()


class TestSecondCommandAppends:
    def test_second_call_uses_last_timestamp_as_since_and_appends(
        self, project, runner
    ):
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage1 = {"claude-sonnet-5": ModelUsage(input_tokens=100, output_tokens=50)}
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage1),
        ):
            runner.invoke(token_log_command, ["--command", "specify-brd"])

        usage2 = {"claude-sonnet-5": ModelUsage(input_tokens=200, output_tokens=60)}
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch(
                "sdd.commands.token_log.sum_usage_since", return_value=usage2
            ) as mock_sum2,
        ):
            result = runner.invoke(token_log_command, ["--command", "specify-uc"])

        assert result.exit_code == 0, result.output
        # Second call must have passed a non-None `since` -- the timestamp
        # of the first row -- not re-summed from session start.
        assert mock_sum2.call_args.args[1] is not None

        text = (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).read_text()
        assert "| 1 | specify-brd |" in text
        assert "| 2 | specify-uc |" in text
        assert "Commands logged | 2" in text

    def test_legacy_seven_column_row_is_preserved_not_dropped(self, project, runner):
        """A file created before this version added the Source column has
        a 7-column header/separator, not the current 8-column one -- both
        the separator-matching (to find where to insert) and the row
        parsing (to preserve old data) must handle this real shape, not
        just a synthetic one that happens to already use the new
        separator."""
        _write_pricing(project)
        path = project / ".specify" / "features" / "auth" / "token-usage.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Token Usage Log\n# Feature: auth\n\n"
            "## Running Totals\n\n| Metric | Value |\n|---|---|\n"
            "| Total Est. Input Tokens | 500 |\n"
            "| Total Est. Output Tokens | 100 |\n"
            "| Total Est. Cost (USD) | n/a — see notes |\n"
            "| Commands logged | 1 |\n"
            "| Last updated | 2026-07-10 |\n\n---\n\n"
            "## Per-Command Log\n\n"
            "| # | Command | Model | Est. Input Tokens | Est. Output Tokens | Est. Cost (USD) | Timestamp |\n"
            "|---|---|---|---|---|---|---|\n"
            "| 1 | specify-brd | claude-sonnet-5 | 500 | 100 | n/a | 2026-07-10 |\n"
        )

        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage = {"claude-sonnet-5": ModelUsage(input_tokens=1000, output_tokens=200)}
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage),
        ):
            result = runner.invoke(token_log_command, ["--command", "specify-uc"])

        assert result.exit_code == 0, result.output
        new_text = path.read_text()
        # Original legacy row must still be present, byte-for-byte.
        assert (
            "| 1 | specify-brd | claude-sonnet-5 | 500 | 100 | n/a | 2026-07-10 |"
            in new_text
        )
        # New row appended after it, numbered 2, in the new 8-col shape.
        assert "| 2 | specify-uc | claude-sonnet-5 | 1000 | 200 |" in new_text
        # Totals now include both legacy and new rows.
        assert "Commands logged | 2" in new_text

    def test_inserts_into_per_command_log_not_running_totals_table(
        self, project, runner
    ):
        """Running Totals' own |---|---| separator appears earlier in the
        file than Per-Command Log's -- a naive "find any separator row"
        search would insert the new row into the wrong table."""
        _write_pricing(project)
        fake_transcript = project / "fake.jsonl"
        fake_transcript.write_text("")
        usage = {"claude-sonnet-5": ModelUsage(input_tokens=100, output_tokens=50)}
        with (
            patch(
                "sdd.commands.token_log.find_session_transcripts",
                return_value=(fake_transcript, []),
            ),
            patch("sdd.commands.token_log.sum_usage_since", return_value=usage),
        ):
            result = runner.invoke(token_log_command, ["--command", "specify-brd"])

        assert result.exit_code == 0, result.output
        text = (
            project / ".specify" / "features" / "auth" / "token-usage.md"
        ).read_text()
        totals_idx = text.index("## Running Totals")
        log_heading_idx = text.index("## Per-Command Log")
        row_idx = text.index("| 1 | specify-brd |")
        assert totals_idx < log_heading_idx < row_idx
