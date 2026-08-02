# Unit tests for the review-comment provider methods behind /address-review
# (sdd pr comments / reply / resolve / request-review).
import json
from unittest.mock import MagicMock, patch

import pytest

from sdd.utils.git_host import (
    AzureDevOpsProvider,
    BitbucketProvider,
    GitHubProvider,
    GitLabProvider,
    RemoteInfo,
    ReviewActionError,
    ReviewComment,
    UnknownHostProvider,
)

# ── GitHubProvider ───────────────────────────────────────────────────────────


def test_github_get_pr_number(monkeypatch):
    monkeypatch.setattr("sdd.utils.git_host._run", lambda cmd: (0, "42", ""))
    p = GitHubProvider(RemoteInfo("github", "acme", "widgets"))
    assert p.get_pr_number("feature/x") == "42"


def test_github_get_pr_number_failure_raises(monkeypatch):
    monkeypatch.setattr("sdd.utils.git_host._run", lambda cmd: (1, "", "no PR"))
    p = GitHubProvider(RemoteInfo("github", "acme", "widgets"))
    with pytest.raises(ReviewActionError):
        p.get_pr_number("feature/x")


GITHUB_GRAPHQL_RESPONSE = json.dumps(
    {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": [
                            {
                                "id": "THREAD_1",
                                "isResolved": False,
                                "comments": {
                                    "nodes": [
                                        {
                                            "databaseId": 111,
                                            "body": "fix this",
                                            "path": "a.py",
                                            "line": 10,
                                            "author": {"login": "jane"},
                                        }
                                    ]
                                },
                            },
                            {
                                "id": "THREAD_2",
                                "isResolved": True,
                                "comments": {
                                    "nodes": [
                                        {
                                            "databaseId": 112,
                                            "body": "already resolved",
                                            "path": "b.py",
                                            "line": 5,
                                            "author": {"login": "jane"},
                                        }
                                    ]
                                },
                            },
                        ]
                    }
                }
            }
        }
    }
)


def test_github_list_unresolved_comments_filters_resolved(monkeypatch):
    monkeypatch.setattr(
        "sdd.utils.git_host._run", lambda cmd: (0, GITHUB_GRAPHQL_RESPONSE, "")
    )
    p = GitHubProvider(RemoteInfo("github", "acme", "widgets"))
    comments = p.list_unresolved_comments("42")
    assert len(comments) == 1
    assert comments[0].comment_id == "111"
    assert comments[0].thread_id == "THREAD_1"
    assert comments[0].path == "a.py"
    assert comments[0].author == "jane"


def test_github_reply_to_comment(monkeypatch):
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return 0, "", ""

    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = GitHubProvider(RemoteInfo("github", "acme", "widgets"))
    comment = ReviewComment("111", "THREAD_1", "a.py", 10, "jane", "fix this")
    p.reply_to_comment("42", comment, "Fixed in abc123")
    assert "pulls/comments/111/replies" in calls[0][2]


def test_github_resolve_thread(monkeypatch):
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return 0, "", ""

    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = GitHubProvider(RemoteInfo("github", "acme", "widgets"))
    comment = ReviewComment("111", "THREAD_1", "a.py", 10, "jane", "fix this")
    p.resolve_thread("42", comment)
    assert "resolveReviewThread" in calls[0][4]
    assert "THREAD_1" in calls[0][6]


def test_github_request_review(monkeypatch):
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return 0, "", ""

    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = GitHubProvider(RemoteInfo("github", "acme", "widgets"))
    p.request_review("42", "jane")
    assert calls[0] == ["gh", "pr", "edit", "42", "--add-reviewer", "jane"]


# ── GitLabProvider ───────────────────────────────────────────────────────────


def test_gitlab_requires_token_for_review_ops(monkeypatch):
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
    with pytest.raises(ReviewActionError, match="GITLAB_TOKEN"):
        p.get_pr_number("feature/x")


def test_gitlab_get_pr_number(monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "tok")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = [{"iid": 7}]
    with patch("requests.get", return_value=mock_resp):
        p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
        assert p.get_pr_number("feature/x") == "7"


def test_gitlab_list_unresolved_comments(monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "tok")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = [
        {
            "id": "disc1",
            "notes": [
                {
                    "id": 1,
                    "resolvable": True,
                    "resolved": False,
                    "body": "fix",
                    "author": {"username": "jane"},
                    "position": {"new_path": "a.py", "new_line": 10},
                }
            ],
        },
        {
            "id": "disc2",
            "notes": [
                {
                    "id": 2,
                    "resolvable": True,
                    "resolved": True,
                    "body": "done",
                    "author": {"username": "jane"},
                    "position": {},
                }
            ],
        },
        {
            "id": "disc3",
            "notes": [
                {
                    "id": 3,
                    "resolvable": False,
                    "body": "fyi not a review comment",
                    "author": {"username": "bob"},
                }
            ],
        },
    ]
    with patch("requests.get", return_value=mock_resp):
        p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
        comments = p.list_unresolved_comments("7")
    assert len(comments) == 1
    assert comments[0].thread_id == "disc1"
    assert comments[0].path == "a.py"


def test_gitlab_reply_to_comment(monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "tok")
    mock_resp = MagicMock(status_code=201)
    with patch("requests.post", return_value=mock_resp) as post:
        p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
        comment = ReviewComment("1", "disc1", "a.py", 10, "jane", "fix")
        p.reply_to_comment("7", comment, "Fixed")
    assert "discussions/disc1/notes" in post.call_args[0][0]


def test_gitlab_resolve_thread(monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "tok")
    mock_resp = MagicMock(status_code=200)
    with patch("requests.put", return_value=mock_resp) as put:
        p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
        comment = ReviewComment("1", "disc1", "a.py", 10, "jane", "fix")
        p.resolve_thread("7", comment)
    assert "discussions/disc1" in put.call_args[0][0]
    assert put.call_args.kwargs["params"] == {"resolved": "true"}


def test_gitlab_request_review_looks_up_user_then_assigns(monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "tok")
    user_resp = MagicMock(status_code=200)
    user_resp.json.return_value = [{"id": 99}]
    put_resp = MagicMock(status_code=200)
    with (
        patch("requests.get", return_value=user_resp),
        patch("requests.put", return_value=put_resp) as put,
    ):
        p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
        p.request_review("7", "jane")
    assert put.call_args.kwargs["json"] == {"reviewer_ids": [99]}


def test_gitlab_request_review_user_not_found(monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "tok")
    user_resp = MagicMock(status_code=200)
    user_resp.json.return_value = []
    with patch("requests.get", return_value=user_resp):
        p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
        with pytest.raises(ReviewActionError, match="not found"):
            p.request_review("7", "ghost")


# ── BitbucketProvider ────────────────────────────────────────────────────────


def test_bitbucket_review_ops_require_credentials(monkeypatch):
    monkeypatch.delenv("BITBUCKET_USERNAME", raising=False)
    monkeypatch.delenv("BITBUCKET_APP_PASSWORD", raising=False)
    p = BitbucketProvider(RemoteInfo("bitbucket", "acme-team", "widgets"))
    with pytest.raises(ReviewActionError):
        p.get_pr_number("feature/x")


def test_bitbucket_get_pr_number(monkeypatch):
    monkeypatch.setenv("BITBUCKET_USERNAME", "bob")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "secret")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"values": [{"id": 5}]}
    with patch("requests.get", return_value=mock_resp):
        p = BitbucketProvider(RemoteInfo("bitbucket", "acme-team", "widgets"))
        assert p.get_pr_number("feature/x") == "5"


def test_bitbucket_list_unresolved_comments(monkeypatch):
    monkeypatch.setenv("BITBUCKET_USERNAME", "bob")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "secret")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "values": [
            {
                "id": 1,
                "deleted": False,
                "resolved": False,
                "inline": {"path": "a.py", "to": 10},
                "user": {"display_name": "Jane"},
                "content": {"raw": "fix"},
            },
            {
                "id": 2,
                "deleted": False,
                "resolved": True,
                "user": {"display_name": "Jane"},
                "content": {"raw": "done"},
            },
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        p = BitbucketProvider(RemoteInfo("bitbucket", "acme-team", "widgets"))
        comments = p.list_unresolved_comments("5")
    assert len(comments) == 1
    assert comments[0].comment_id == "1"
    assert comments[0].path == "a.py"


def test_bitbucket_reply_to_comment(monkeypatch):
    monkeypatch.setenv("BITBUCKET_USERNAME", "bob")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "secret")
    mock_resp = MagicMock(status_code=201)
    with patch("requests.post", return_value=mock_resp) as post:
        p = BitbucketProvider(RemoteInfo("bitbucket", "acme-team", "widgets"))
        comment = ReviewComment("1", "1", "a.py", 10, "jane", "fix")
        p.reply_to_comment("5", comment, "Fixed")
    assert post.call_args.kwargs["json"]["parent"] == {"id": 1}


def test_bitbucket_resolve_thread_always_raises(monkeypatch):
    monkeypatch.setenv("BITBUCKET_USERNAME", "bob")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "secret")
    p = BitbucketProvider(RemoteInfo("bitbucket", "acme-team", "widgets"))
    comment = ReviewComment("1", "1", "a.py", 10, "jane", "fix")
    with pytest.raises(ReviewActionError, match="no API-level thread resolution"):
        p.resolve_thread("5", comment)


# ── AzureDevOpsProvider ──────────────────────────────────────────────────────


def test_azure_review_ops_require_az_cli(monkeypatch):
    monkeypatch.setattr("sdd.utils.git_host._run", lambda cmd: (1, "", "not found"))
    p = AzureDevOpsProvider(
        RemoteInfo("azure", "acmeorg", "widgets", project="AcmeProject")
    )
    with pytest.raises(ReviewActionError, match="az CLI not found"):
        p.get_pr_number("feature/x")


def test_azure_get_pr_number(monkeypatch):
    def fake_run(cmd):
        if cmd[:2] == ["az", "--version"]:
            return 0, "azure-cli", ""
        return 0, "17", ""

    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = AzureDevOpsProvider(
        RemoteInfo("azure", "acmeorg", "widgets", project="AcmeProject")
    )
    assert p.get_pr_number("feature/x") == "17"


AZURE_THREADS_RESPONSE = json.dumps(
    {
        "value": [
            {
                "id": 501,
                "status": "active",
                "comments": [
                    {"id": 1, "content": "fix this", "author": {"displayName": "jane"}}
                ],
                "threadContext": {"filePath": "/a.py", "rightFileStart": {"line": 10}},
            },
            {
                "id": 502,
                "status": "fixed",
                "comments": [
                    {"id": 2, "content": "done", "author": {"displayName": "jane"}}
                ],
            },
        ]
    }
)


def test_azure_list_unresolved_comments(monkeypatch):
    def fake_run(cmd):
        if cmd[:2] == ["az", "--version"]:
            return 0, "azure-cli", ""
        return 0, AZURE_THREADS_RESPONSE, ""

    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = AzureDevOpsProvider(
        RemoteInfo("azure", "acmeorg", "widgets", project="AcmeProject")
    )
    comments = p.list_unresolved_comments("17")
    assert len(comments) == 1
    assert comments[0].thread_id == "501"
    assert comments[0].path == "/a.py"
    assert comments[0].line == 10


def test_azure_reply_and_resolve(monkeypatch):
    calls = []

    def fake_run(cmd):
        if cmd[:2] == ["az", "--version"]:
            return 0, "azure-cli", ""
        calls.append(cmd)
        return 0, "", ""

    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = AzureDevOpsProvider(
        RemoteInfo("azure", "acmeorg", "widgets", project="AcmeProject")
    )
    comment = ReviewComment("1", "501", "/a.py", 10, "jane", "fix")
    p.reply_to_comment("17", comment, "Fixed")
    p.resolve_thread("17", comment)
    assert "threads/501/comments" in calls[0][5]
    assert calls[1][5].endswith("threads/501?api-version=7.1")


def test_azure_request_review(monkeypatch):
    calls = []

    def fake_run(cmd):
        if cmd[:2] == ["az", "--version"]:
            return 0, "azure-cli", ""
        calls.append(cmd)
        return 0, "", ""

    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = AzureDevOpsProvider(
        RemoteInfo("azure", "acmeorg", "widgets", project="AcmeProject")
    )
    p.request_review("17", "jane")
    assert calls[0] == [
        "az",
        "repos",
        "pr",
        "reviewer",
        "add",
        "--id",
        "17",
        "--reviewers",
        "jane",
    ]


# ── UnknownHostProvider ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "method,args",
    [
        ("get_pr_number", ("feature/x",)),
        ("list_unresolved_comments", ("1",)),
        (
            "reply_to_comment",
            ("1", ReviewComment("1", "1", "a.py", 1, "x", "y"), "body"),
        ),
        ("resolve_thread", ("1", ReviewComment("1", "1", "a.py", 1, "x", "y"))),
        ("request_review", ("1", "jane")),
    ],
)
def test_unknown_host_all_review_methods_raise(method, args):
    p = UnknownHostProvider(RemoteInfo("unknown", "", ""))
    with pytest.raises(ReviewActionError):
        getattr(p, method)(*args)
