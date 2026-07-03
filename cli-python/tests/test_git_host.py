# Unit tests for the git-host provider abstraction behind `sdd pr create`.
from unittest.mock import patch, MagicMock

import pytest

from sdd.utils.git_host import (
    parse_remote, detect_host, get_provider, get_origin_url,
    GitHubProvider, GitLabProvider, BitbucketProvider, AzureDevOpsProvider,
    UnknownHostProvider, PrCreateError, RemoteInfo,
)


# ── URL parsing (pure — no mocking) ─────────────────────────────────────────

@pytest.mark.parametrize("url,host,owner,repo", [
    ("git@github.com:acme/widgets.git",             "github",    "acme",         "widgets"),
    ("https://github.com/acme/widgets.git",          "github",    "acme",         "widgets"),
    ("https://github.com/acme/widgets",              "github",    "acme",         "widgets"),
    ("git@bitbucket.org:acme-team/widgets.git",      "bitbucket", "acme-team",    "widgets"),
    ("https://bitbucket.org/acme-team/widgets.git",  "bitbucket", "acme-team",    "widgets"),
    ("git@gitlab.com:acme/widgets.git",               "gitlab",    "acme",         "widgets"),
    ("https://gitlab.com/acme/platform/widgets.git", "gitlab",    "acme/platform", "widgets"),
])
def test_parse_remote_known_hosts(url, host, owner, repo):
    info = parse_remote(url)
    assert info.host == host
    assert info.owner == owner
    assert info.repo == repo


@pytest.mark.parametrize("url", [
    "https://dev.azure.com/acmeorg/AcmeProject/_git/widgets",
    "git@ssh.dev.azure.com:v3/acmeorg/AcmeProject/widgets",
    "https://acmeorg.visualstudio.com/AcmeProject/_git/widgets",
])
def test_parse_remote_azure_forms(url):
    info = parse_remote(url)
    assert info.host == "azure"
    assert info.owner == "acmeorg"
    assert info.repo == "widgets"
    assert info.project == "AcmeProject"


@pytest.mark.parametrize("url", [
    "https://git.internal.corp/team/widgets.git",
    "git@git.internal.corp:team/widgets.git",
])
def test_parse_remote_self_hosted_is_unknown(url):
    info = parse_remote(url)
    assert info.host == "unknown"
    # still best-effort extracts something useful for the fallback message
    assert info.repo == "widgets"


def test_parse_remote_garbage_input_does_not_raise():
    info = parse_remote("not a url at all")
    assert info.host == "unknown"


def test_detect_host_no_remote_configured():
    with patch("sdd.utils.git_host.get_origin_url", return_value=None):
        info = detect_host()
        assert info.host == "unknown"


def test_get_origin_url_uses_git_remote(monkeypatch):
    def fake_run(cmd):
        assert cmd == ["git", "remote", "get-url", "origin"]
        return 0, "https://github.com/acme/widgets.git", ""
    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    assert get_origin_url() == "https://github.com/acme/widgets.git"


def test_run_missing_binary_returns_127_not_an_exception():
    """A genuinely absent CLI (glab/az on most machines) must not raise —
    _*_available() and create_pr() both depend on _run() failing gracefully."""
    from sdd.utils.git_host import _run
    code, out, err = _run(["definitely-not-a-real-binary-xyz"])
    assert code == 127
    assert "not found" in err


# ── Provider dispatch ────────────────────────────────────────────────────────

def test_get_provider_dispatches_by_host():
    assert isinstance(get_provider(RemoteInfo("github", "a", "b")), GitHubProvider)
    assert isinstance(get_provider(RemoteInfo("gitlab", "a", "b")), GitLabProvider)
    assert isinstance(get_provider(RemoteInfo("bitbucket", "a", "b")), BitbucketProvider)
    assert isinstance(get_provider(RemoteInfo("azure", "a", "b")), AzureDevOpsProvider)
    assert isinstance(get_provider(RemoteInfo("unknown", "", "")), UnknownHostProvider)
    assert isinstance(get_provider(RemoteInfo("some-future-host", "a", "b")), UnknownHostProvider)


def test_unknown_host_provider_always_raises():
    provider = UnknownHostProvider(RemoteInfo("unknown", "", ""))
    with pytest.raises(PrCreateError):
        provider.create_pr("t", "b", "main", "feature/x")


# ── GitHubProvider ───────────────────────────────────────────────────────────

def test_github_provider_success(monkeypatch):
    def fake_run(cmd):
        assert cmd[:3] == ["gh", "pr", "create"]
        return 0, "https://github.com/acme/widgets/pull/1", ""
    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = GitHubProvider(RemoteInfo("github", "acme", "widgets"))
    assert p.create_pr("t", "b", "main", "feature/x") == "https://github.com/acme/widgets/pull/1"


def test_github_provider_failure_raises(monkeypatch):
    monkeypatch.setattr("sdd.utils.git_host._run", lambda cmd: (1, "", "not authenticated"))
    p = GitHubProvider(RemoteInfo("github", "acme", "widgets"))
    with pytest.raises(PrCreateError, match="not authenticated"):
        p.create_pr("t", "b", "main", "feature/x")


# ── GitLabProvider ───────────────────────────────────────────────────────────

def test_gitlab_provider_uses_glab_when_available(monkeypatch):
    calls = []
    def fake_run(cmd):
        calls.append(cmd)
        if cmd[:2] == ["glab", "--version"]:
            return 0, "glab 1.0", ""
        assert cmd[:3] == ["glab", "mr", "create"]
        return 0, "https://gitlab.com/acme/widgets/-/merge_requests/1", ""
    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
    url = p.create_pr("t", "b", "main", "feature/x")
    assert url == "https://gitlab.com/acme/widgets/-/merge_requests/1"


def test_gitlab_provider_falls_back_to_api_without_glab(monkeypatch):
    monkeypatch.setattr("sdd.utils.git_host._run", lambda cmd: (1, "", "not found"))
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-xxx")
    mock_resp = MagicMock(status_code=201)
    mock_resp.json.return_value = {"web_url": "https://gitlab.com/acme/widgets/-/merge_requests/2"}
    with patch("requests.post", return_value=mock_resp) as post:
        p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
        url = p.create_pr("t", "b", "main", "feature/x")
    assert url == "https://gitlab.com/acme/widgets/-/merge_requests/2"
    called_url = post.call_args[0][0]
    assert "acme%2Fwidgets" in called_url  # URL-encoded project path


def test_gitlab_provider_raises_without_glab_or_token(monkeypatch):
    monkeypatch.setattr("sdd.utils.git_host._run", lambda cmd: (1, "", "not found"))
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    p = GitLabProvider(RemoteInfo("gitlab", "acme", "widgets"))
    with pytest.raises(PrCreateError, match="GITLAB_TOKEN"):
        p.create_pr("t", "b", "main", "feature/x")


# ── BitbucketProvider ────────────────────────────────────────────────────────

def test_bitbucket_provider_requires_credentials(monkeypatch):
    monkeypatch.delenv("BITBUCKET_USERNAME", raising=False)
    monkeypatch.delenv("BITBUCKET_APP_PASSWORD", raising=False)
    p = BitbucketProvider(RemoteInfo("bitbucket", "acme-team", "widgets"))
    with pytest.raises(PrCreateError, match="BITBUCKET_USERNAME"):
        p.create_pr("t", "b", "main", "feature/x")


def test_bitbucket_provider_success(monkeypatch):
    monkeypatch.setenv("BITBUCKET_USERNAME", "bob")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "secret")
    mock_resp = MagicMock(status_code=201)
    mock_resp.json.return_value = {
        "links": {"html": {"href": "https://bitbucket.org/acme-team/widgets/pull-requests/1"}}
    }
    with patch("requests.post", return_value=mock_resp) as post:
        p = BitbucketProvider(RemoteInfo("bitbucket", "acme-team", "widgets"))
        url = p.create_pr("t", "b", "main", "feature/x")
    assert url == "https://bitbucket.org/acme-team/widgets/pull-requests/1"
    assert post.call_args.kwargs["auth"] == ("bob", "secret")
    assert "acme-team/widgets" in post.call_args[0][0]


def test_bitbucket_provider_missing_owner_repo_raises(monkeypatch):
    monkeypatch.setenv("BITBUCKET_USERNAME", "bob")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "secret")
    p = BitbucketProvider(RemoteInfo("bitbucket", "", ""))
    with pytest.raises(PrCreateError, match="workspace/repo"):
        p.create_pr("t", "b", "main", "feature/x")


def test_bitbucket_provider_api_error_raises(monkeypatch):
    monkeypatch.setenv("BITBUCKET_USERNAME", "bob")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "secret")
    mock_resp = MagicMock(status_code=400, text="source branch not found")
    with patch("requests.post", return_value=mock_resp):
        p = BitbucketProvider(RemoteInfo("bitbucket", "acme-team", "widgets"))
        with pytest.raises(PrCreateError, match="400"):
            p.create_pr("t", "b", "main", "feature/x")


# ── AzureDevOpsProvider ──────────────────────────────────────────────────────

def test_azure_provider_requires_az_cli(monkeypatch):
    monkeypatch.setattr("sdd.utils.git_host._run", lambda cmd: (1, "", "not found"))
    p = AzureDevOpsProvider(RemoteInfo("azure", "acmeorg", "widgets", project="AcmeProject"))
    with pytest.raises(PrCreateError, match="az CLI not found"):
        p.create_pr("t", "b", "main", "feature/x")


def test_azure_provider_success(monkeypatch):
    def fake_run(cmd):
        if cmd[:2] == ["az", "--version"]:
            return 0, "azure-cli 2.0", ""
        assert cmd[:4] == ["az", "repos", "pr", "create"]
        return 0, "https://dev.azure.com/acmeorg/AcmeProject/_git/widgets/pullrequest/1", ""
    monkeypatch.setattr("sdd.utils.git_host._run", fake_run)
    p = AzureDevOpsProvider(RemoteInfo("azure", "acmeorg", "widgets", project="AcmeProject"))
    url = p.create_pr("t", "b", "main", "feature/x")
    assert "pullrequest/1" in url
