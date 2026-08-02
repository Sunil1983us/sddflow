# Unit tests for `sdd pr` (sdd/commands/pr.py). detect_host/get_provider
# and git subprocess calls are mocked -- these tests exercise the command
# layer (task lookup, branch/PR-body construction, error handling), not
# the individual git-host providers (already covered by test_git_host.py).
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd.commands.pr import pr_command
from sdd.utils.git_host import (
    PrCreateError,
    RemoteInfo,
    ReviewActionError,
    ReviewComment,
)

TASKS_MD = """
## TASK-001 — Add login endpoint

**Story:** STORY-001
**Satisfies:** FR-001
**Estimate:** M

**Description:**
Implements the login endpoint per FR-001.

**Acceptance Criteria:**
- Returns 200 on valid credentials
- Returns 401 on invalid credentials
"""

INTEGRATIONS_NO_JIRA = """
pr_automation:
  enabled: true
  branch_pattern: "feature/{task_id}-{slug}"
  pr_title_pattern: "feat({task_id}): {title}"
code_review:
  enabled: false
"""


def _scaffold(tmp_path: Path, feature: str = "checkout") -> None:
    (tmp_path / ".specify").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".specify" / "integrations.yml").write_text(INTEGRATIONS_NO_JIRA)
    (tmp_path / ".specify" / "manifest.yml").write_text(
        f"project:\n  name: shop\n  feature: {feature}\n"
    )
    feature_dir = tmp_path / ".specify" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(TASKS_MD)


@pytest.fixture()
def runner():
    return CliRunner()


class TestPrCreate:
    def test_creates_branch_and_pr_for_matched_task(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        _scaffold(tmp_path)

        provider = MagicMock()
        provider.name = "github"
        provider.create_pr.return_value = "https://github.com/acme/shop/pull/7"

        with (
            patch("sdd.commands.pr._run", return_value=(0, "", "")) as run_mock,
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("github", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(pr_command, ["create", "--task", "TASK-001"])

        assert result.exit_code == 0, result.output
        assert "https://github.com/acme/shop/pull/7" in result.output

        # branch created off the slugged title, then pushed
        checkout_call = run_mock.call_args_list[0][0][0]
        assert checkout_call[:3] == ["git", "checkout", "-b"]
        assert checkout_call[3] == "feature/task-001-add-login-endpoint"

        title, body, base, branch = provider.create_pr.call_args[0]
        assert title == "feat(TASK-001): Add login endpoint"
        assert "Returns 200 on valid credentials" in body
        assert "FR-001" in body
        assert base == "main"
        assert branch == "feature/task-001-add-login-endpoint"

    def test_unknown_task_id_exits_nonzero(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _scaffold(tmp_path)

        result = runner.invoke(pr_command, ["create", "--task", "TASK-999"])

        assert result.exit_code != 0
        assert "not found in tasks.md" in result.output

    def test_missing_integrations_yml_exits_nonzero(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify").mkdir()

        result = runner.invoke(pr_command, ["create", "--task", "TASK-001"])

        assert result.exit_code != 0

    def test_branch_create_failure_exits_nonzero(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _scaffold(tmp_path)

        with patch("sdd.commands.pr._run", return_value=(1, "", "already exists")):
            result = runner.invoke(pr_command, ["create", "--task", "TASK-001"])

        assert result.exit_code != 0
        assert "Could not create branch" in result.output

    def test_pr_create_error_prints_manual_fallback_but_exits_zero(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        _scaffold(tmp_path)

        provider = MagicMock()
        provider.name = "gitlab"
        provider.create_pr.side_effect = PrCreateError("no token configured")

        with (
            patch("sdd.commands.pr._run", return_value=(0, "", "")),
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("gitlab", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(pr_command, ["create", "--task", "TASK-001"])

        assert result.exit_code == 0
        assert "create the PR manually" in result.output
        assert "already pushed to origin" in result.output

    def test_feature_flag_overrides_manifest(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _scaffold(tmp_path, feature="checkout")
        _scaffold(tmp_path, feature="billing")

        provider = MagicMock()
        provider.name = "github"
        provider.create_pr.return_value = "https://github.com/acme/shop/pull/1"

        with (
            patch("sdd.commands.pr._run", return_value=(0, "", "")),
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("github", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(
                pr_command,
                [
                    "create",
                    "--task",
                    "TASK-001",
                    "--feature",
                    "billing",
                ],
            )

        assert result.exit_code == 0, result.output


class TestPrComments:
    def test_lists_unresolved_comments(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        provider = MagicMock()
        provider.name = "github"
        provider.get_pr_number.return_value = "7"
        provider.list_unresolved_comments.return_value = [
            ReviewComment(
                comment_id="1",
                thread_id="1",
                path="src/a.py",
                line=10,
                author="reviewer1",
                body="please rename this",
            ),
        ]

        with (
            patch("sdd.commands.pr._run", return_value=(0, "main", "")),
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("github", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(pr_command, ["comments"])

        assert result.exit_code == 0, result.output
        assert "src/a.py:10" in result.output
        assert "please rename this" in result.output

    def test_no_comments_prints_ready_to_approve(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        provider = MagicMock()
        provider.name = "github"
        provider.get_pr_number.return_value = "7"
        provider.list_unresolved_comments.return_value = []

        with (
            patch("sdd.commands.pr._run", return_value=(0, "main", "")),
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("github", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(pr_command, ["comments"])

        assert result.exit_code == 0
        assert "Ready to approve" in result.output

    def test_pr_id_resolution_failure_exits_nonzero(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        provider = MagicMock()
        provider.name = "github"

        with (
            patch("sdd.commands.pr._run", return_value=(1, "", "not a git repo")),
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("github", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(pr_command, ["comments"])

        assert result.exit_code != 0


class TestPrReply:
    def test_replies_to_matched_comment(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        comment = ReviewComment(
            comment_id="1",
            thread_id="1",
            path="src/a.py",
            line=10,
            author="reviewer1",
            body="please rename this",
        )
        provider = MagicMock()
        provider.name = "github"
        provider.list_unresolved_comments.return_value = [comment]

        with (
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("github", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(
                pr_command,
                [
                    "reply",
                    "--comment-id",
                    "1",
                    "--body",
                    "done",
                    "--pr-id",
                    "7",
                ],
            )

        assert result.exit_code == 0, result.output
        provider.reply_to_comment.assert_called_once_with("7", comment, "done")

    def test_unknown_comment_id_exits_nonzero(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        provider = MagicMock()
        provider.name = "github"
        provider.list_unresolved_comments.return_value = []

        with (
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("github", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(
                pr_command,
                [
                    "reply",
                    "--comment-id",
                    "99",
                    "--body",
                    "done",
                    "--pr-id",
                    "7",
                ],
            )

        assert result.exit_code != 0
        assert "not found among unresolved comments" in result.output


class TestPrResolve:
    def test_resolve_action_error_degrades_gracefully(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        comment = ReviewComment(
            comment_id="1",
            thread_id="1",
            path="src/a.py",
            line=10,
            author="reviewer1",
            body="please rename this",
        )
        provider = MagicMock()
        provider.name = "bitbucket"
        provider.list_unresolved_comments.return_value = [comment]
        provider.resolve_thread.side_effect = ReviewActionError(
            "no thread-resolution API"
        )

        with (
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("bitbucket", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(
                pr_command,
                [
                    "resolve",
                    "--comment-id",
                    "1",
                    "--pr-id",
                    "7",
                ],
            )

        # Not a hard failure -- reply was already posted, resolution is best-effort.
        assert result.exit_code == 0
        assert "resolve manually" in result.output


class TestPrRequestReview:
    def test_requests_review_from_reviewer(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        provider = MagicMock()
        provider.name = "github"

        with (
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("github", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(
                pr_command,
                [
                    "request-review",
                    "--reviewer",
                    "octocat",
                    "--pr-id",
                    "7",
                ],
            )

        assert result.exit_code == 0, result.output
        provider.request_review.assert_called_once_with("7", "octocat")

    def test_request_review_error_degrades_gracefully(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        provider = MagicMock()
        provider.name = "azure"
        provider.request_review.side_effect = ReviewActionError(
            "az cli not authenticated"
        )

        with (
            patch(
                "sdd.commands.pr.detect_host",
                return_value=RemoteInfo("azure", "acme", "shop"),
            ),
            patch("sdd.commands.pr.get_provider", return_value=provider),
        ):
            result = runner.invoke(
                pr_command,
                [
                    "request-review",
                    "--reviewer",
                    "octocat",
                    "--pr-id",
                    "7",
                ],
            )

        assert result.exit_code == 0
        assert "Ask @octocat to re-review manually" in result.output
