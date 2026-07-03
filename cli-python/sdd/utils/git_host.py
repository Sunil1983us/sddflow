# Git-host abstraction for `sdd pr create`.
#
# The SDD document workflow never touches a git host (approval happens via
# the Status: header — see review.py). Only code-phase PR creation needs to
# know which host the repo lives on. This module isolates that one concern:
# detect the host from `git remote get-url origin`, then dispatch to a small
# provider that knows how to open a PR there.
#
# Parsing (detect_host, parse_remote) is pure — no subprocess, no network —
# so it is fully unit-testable. Providers do the actual CLI/API calls and are
# exercised in tests by mocking subprocess.run / requests.

from __future__ import annotations
import os
import re
import subprocess
from dataclasses import dataclass


class PrCreateError(Exception):
    """Raised when a provider cannot create a PR — caller falls back to the
    manual title/body printout, same as the historical gh-not-found path."""


@dataclass
class RemoteInfo:
    host: str          # github | bitbucket | gitlab | azure | unknown
    owner: str          # org/workspace/group (best-effort — empty for azure/unknown)
    repo: str           # repo name (best-effort)
    project: str = ""   # azure-only: the Azure DevOps "project" segment


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a subprocess, treating a missing binary as a normal failure
    (returncode 127, shell convention) rather than an uncaught exception —
    gh/glab/az are all optional and commonly absent."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: command not found"
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def get_origin_url() -> str | None:
    code, out, _ = _run(["git", "remote", "get-url", "origin"])
    return out if code == 0 and out else None


# ── Pure URL parsing ─────────────────────────────────────────────────────────
# Handles both SSH (git@host:path.git) and HTTPS (https://host/path.git) forms.

_SSH_RE   = re.compile(r"^[\w.-]+@(?P<host>[\w.-]+):(?P<path>.+?)(?:\.git)?/?$")
_HTTPS_RE = re.compile(r"^https?://(?:[^@/]+@)?(?P<host>[\w.-]+)(?::\d+)?/(?P<path>.+?)(?:\.git)?/?$")


def _split_host_path(url: str) -> tuple[str, str] | None:
    m = _SSH_RE.match(url) or _HTTPS_RE.match(url)
    if not m:
        return None
    return m.group("host").lower(), m.group("path").strip("/")


def parse_remote(url: str) -> RemoteInfo:
    """Parse a git remote URL into (host, owner, repo[, project]).

    Best-effort: an unrecognized host still returns owner/repo split on the
    last path segment where possible, host='unknown'.
    """
    split = _split_host_path(url)
    if not split:
        return RemoteInfo(host="unknown", owner="", repo="")
    host, path = split
    parts = [p for p in path.split("/") if p]

    if "github.com" in host:
        if len(parts) >= 2:
            return RemoteInfo(host="github", owner=parts[0], repo=parts[1])
        return RemoteInfo(host="github", owner="", repo=parts[-1] if parts else "")

    if "bitbucket.org" in host:
        if len(parts) >= 2:
            return RemoteInfo(host="bitbucket", owner=parts[0], repo=parts[1])
        return RemoteInfo(host="bitbucket", owner="", repo=parts[-1] if parts else "")

    if "gitlab" in host:
        # GitLab supports nested subgroups: group/subgroup/.../repo — owner is
        # everything before the last segment (still enough to build the URL-
        # encoded project path GitLab's API expects: "group%2Fsubgroup%2Frepo").
        if len(parts) >= 2:
            return RemoteInfo(host="gitlab", owner="/".join(parts[:-1]), repo=parts[-1])
        return RemoteInfo(host="gitlab", owner="", repo=parts[-1] if parts else "")

    if "dev.azure.com" in host or "visualstudio.com" in host:
        # https forms:  dev.azure.com/{org}/{project}/_git/{repo}
        #               {org}.visualstudio.com/{project}/_git/{repo}
        # ssh form:     ssh.dev.azure.com:v3/{org}/{project}/{repo}
        clean = [p for p in parts if p != "_git" and p != "v3"]
        if "visualstudio.com" in host:
            org = host.split(".visualstudio.com")[0]
            if len(clean) >= 2:
                return RemoteInfo(host="azure", owner=org, repo=clean[-1], project=clean[-2])
            return RemoteInfo(host="azure", owner=org, repo=clean[-1] if clean else "")
        if len(clean) >= 3:
            return RemoteInfo(host="azure", owner=clean[0], repo=clean[-1], project=clean[-2])
        return RemoteInfo(host="azure", owner=clean[0] if clean else "", repo=clean[-1] if clean else "")

    # Self-hosted / unrecognized — still return best-effort owner/repo so the
    # manual-fallback message can show something useful.
    if len(parts) >= 2:
        return RemoteInfo(host="unknown", owner=parts[-2], repo=parts[-1])
    return RemoteInfo(host="unknown", owner="", repo=parts[-1] if parts else "")


def detect_host() -> RemoteInfo:
    url = get_origin_url()
    if not url:
        return RemoteInfo(host="unknown", owner="", repo="")
    return parse_remote(url)


# ── Providers ────────────────────────────────────────────────────────────────
# Each provider exposes create_pr(title, body, base, branch) -> pr_url.
# Raises PrCreateError on any failure — callers catch it and print the
# manual-fallback message (title + body), same shape as the historical
# gh-not-found path.

class GitHubProvider:
    name = "GitHub"

    def __init__(self, info: RemoteInfo):
        self.info = info

    def available(self) -> bool:
        code, _, _ = _run(["gh", "--version"])
        return code == 0

    def create_pr(self, title: str, body: str, base: str, branch: str) -> str:
        code, out, err = _run([
            "gh", "pr", "create",
            "--title", title, "--body", body, "--base", base,
        ])
        if code != 0:
            raise PrCreateError(f"gh pr create failed: {err}")
        return out


class GitLabProvider:
    name = "GitLab"

    def __init__(self, info: RemoteInfo):
        self.info = info

    def _glab_available(self) -> bool:
        code, _, _ = _run(["glab", "--version"])
        return code == 0

    def create_pr(self, title: str, body: str, base: str, branch: str) -> str:
        if self._glab_available():
            code, out, err = _run([
                "glab", "mr", "create",
                "--title", title, "--description", body,
                "--target-branch", base, "--source-branch", branch,
                "--yes",
            ])
            if code != 0:
                raise PrCreateError(f"glab mr create failed: {err}")
            # glab prints progress lines then the MR URL last
            lines = [l for l in out.splitlines() if l.strip()]
            return lines[-1] if lines else out

        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise PrCreateError(
                "glab CLI not found and GITLAB_TOKEN not set — "
                "install glab (https://gitlab.com/gitlab-org/cli) or export GITLAB_TOKEN"
            )
        import requests
        project_path = f"{self.info.owner}/{self.info.repo}" if self.info.owner else self.info.repo
        encoded = project_path.replace("/", "%2F")
        resp = requests.post(
            f"https://gitlab.com/api/v4/projects/{encoded}/merge_requests",
            headers={"PRIVATE-TOKEN": token},
            json={"source_branch": branch, "target_branch": base,
                  "title": title, "description": body},
            timeout=30,
        )
        if resp.status_code >= 300:
            raise PrCreateError(f"GitLab API error {resp.status_code}: {resp.text[:200]}")
        return resp.json().get("web_url", "")


class BitbucketProvider:
    name = "Bitbucket"

    def __init__(self, info: RemoteInfo):
        self.info = info

    def create_pr(self, title: str, body: str, base: str, branch: str) -> str:
        username = os.environ.get("BITBUCKET_USERNAME")
        app_password = os.environ.get("BITBUCKET_APP_PASSWORD")
        if not username or not app_password:
            raise PrCreateError(
                "BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD env vars are required — "
                "create an app password at bitbucket.org → Personal settings → App passwords "
                "(Pull requests: Write scope)"
            )
        if not self.info.owner or not self.info.repo:
            raise PrCreateError("Could not determine Bitbucket workspace/repo from git remote")

        import requests
        resp = requests.post(
            f"https://api.bitbucket.org/2.0/repositories/{self.info.owner}/{self.info.repo}/pullrequests",
            auth=(username, app_password),
            json={
                "title": title,
                "description": body,
                "source": {"branch": {"name": branch}},
                "destination": {"branch": {"name": base}},
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise PrCreateError(f"Bitbucket API error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return data.get("links", {}).get("html", {}).get("href", "")


class AzureDevOpsProvider:
    name = "Azure DevOps"

    def __init__(self, info: RemoteInfo):
        self.info = info

    def _az_available(self) -> bool:
        code, _, _ = _run(["az", "--version"])
        return code == 0

    def create_pr(self, title: str, body: str, base: str, branch: str) -> str:
        if not self._az_available():
            raise PrCreateError(
                "az CLI not found — install it and run "
                "'az extension add --name azure-devops', then 'az devops login'"
            )
        code, out, err = _run([
            "az", "repos", "pr", "create",
            "--title", title, "--description", body,
            "--target-branch", base, "--source-branch", branch,
            "--query", "url", "--output", "tsv",
        ])
        if code != 0:
            raise PrCreateError(f"az repos pr create failed: {err}")
        return out


class UnknownHostProvider:
    """No known API/CLI for this host — always raises, triggering the
    manual-fallback message. Preserves the pre-multi-host behavior for
    self-hosted git / anything not recognized."""
    name = "this git host"

    def __init__(self, info: RemoteInfo):
        self.info = info

    def create_pr(self, title: str, body: str, base: str, branch: str) -> str:
        raise PrCreateError("no automated PR creation available for this git host")


_PROVIDERS = {
    "github":    GitHubProvider,
    "gitlab":    GitLabProvider,
    "bitbucket": BitbucketProvider,
    "azure":     AzureDevOpsProvider,
}


def get_provider(info: RemoteInfo):
    return _PROVIDERS.get(info.host, UnknownHostProvider)(info)
