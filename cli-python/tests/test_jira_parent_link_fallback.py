# Unit tests for jira.py's _warn_parent_link_failed() -- the fallback
# path when set_parent() fails. Most commonly this happens because the
# child and parent issues live in different Jira projects (via
# project_keys overrides in integrations.yml), which the parent/Epic-Link
# field rejects outright -- a Jira platform limitation. A plain "Relates"
# issue link works across projects, so this is attempted as a fallback
# instead of just printing a dead-end warning.
from __future__ import annotations

from unittest.mock import MagicMock

from sdd.commands.jira import _warn_parent_link_failed


class TestWarnParentLinkFailed:
    def test_attempts_relates_link_as_fallback(self):
        client = MagicMock()
        _warn_parent_link_failed(
            client, "TEMPT-2", "TEMP-1", "TEMPT", Exception("400 Bad Request")
        )
        client.link_issues.assert_called_once_with("TEMPT-2", "TEMP-1")

    def test_success_message_mentions_relates_link_when_fallback_works(self, capsys):
        client = MagicMock()
        client.link_issues.return_value = None
        _warn_parent_link_failed(
            client, "TEMPT-2", "TEMP-1", "TEMPT", Exception("400 Bad Request")
        )
        out = capsys.readouterr().out
        assert "Relates" in out
        assert "TEMPT-2" in out and "TEMP-1" in out

    def test_failure_message_keeps_original_troubleshooting_hint_when_fallback_also_fails(
        self, capsys
    ):
        client = MagicMock()
        client.link_issues.side_effect = Exception("link type not found")
        _warn_parent_link_failed(
            client, "TEMPT-2", "TEMP-1", "TEMPT", Exception("400 Bad Request")
        )
        out = capsys.readouterr().out
        assert "was not linked under" in out
        assert "sdd config fields --project TEMPT" in out
        assert "Relates" in out  # notes the fallback was also attempted and failed

    def test_original_error_always_surfaced(self, capsys):
        client = MagicMock()
        client.link_issues.return_value = None
        _warn_parent_link_failed(
            client,
            "TEMPT-2",
            "TEMP-1",
            "TEMPT",
            Exception("cross-project parent rejected"),
        )
        out = " ".join(capsys.readouterr().out.split())  # collapse Rich's line-wrapping
        assert "cross-project parent rejected" in out
