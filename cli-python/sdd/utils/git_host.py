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


class ReviewActionError(Exception):
    """Raised when a provider cannot perform a review-comment action (list,
    reply, resolve, request-review) — used by `sdd pr comments/reply/
    resolve/request-review`, the CLI backing /address-review."""


@dataclass
class RemoteInfo:
    host: str  # github | bitbucket | gitlab | azure | unknown
    owner: str  # org/workspace/group (best-effort — empty for azure/unknown)
    repo: str  # repo name (best-effort)
    project: str = ""  # azure-only: the Azure DevOps "project" segment


@dataclass
class ReviewComment:
    """One unresolved review comment, normalized across hosts.

    comment_id: the id used to reply to this specific comment.
    thread_id: the id used to resolve the whole thread/discussion this
      comment belongs to. Equal to comment_id on hosts with no separate
      thread concept.
    """

    comment_id: str
    thread_id: str
    path: str
    line: int | None
    author: str
    body: str


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a subprocess, treating a missing binary as a normal failure
    (returncode 127, shell convention) rather than an uncaught exception —
    gh/glab/az are all optional and commonly absent."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: command not found"
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def get_origin_url() -> str | None:
    code, out, _ = _run(["git", "remote", "get-url", "origin"])
    return out if code == 0 and out else None


# ── Pure URL parsing ─────────────────────────────────────────────────────────
# Handles both SSH (git@host:path.git) and HTTPS (https://host/path.git) forms.

_SSH_RE = re.compile(r"^[\w.-]+@(?P<host>[\w.-]+):(?P<path>.+?)(?:\.git)?/?$")
_HTTPS_RE = re.compile(
    r"^https?://(?:[^@/]+@)?(?P<host>[\w.-]+)(?::\d+)?/(?P<path>.+?)(?:\.git)?/?$"
)


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
                return RemoteInfo(
                    host="azure", owner=org, repo=clean[-1], project=clean[-2]
                )
            return RemoteInfo(host="azure", owner=org, repo=clean[-1] if clean else "")
        if len(clean) >= 3:
            return RemoteInfo(
                host="azure", owner=clean[0], repo=clean[-1], project=clean[-2]
            )
        return RemoteInfo(
            host="azure",
            owner=clean[0] if clean else "",
            repo=clean[-1] if clean else "",
        )

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
        code, out, err = _run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--base",
                base,
            ]
        )
        if code != 0:
            raise PrCreateError(f"gh pr create failed: {err}")
        return out

    # ── Review comments (backs /address-review) ───────────────────────────

    def get_pr_number(self, branch: str) -> str:
        code, out, err = _run(
            ["gh", "pr", "view", "--json", "number", "--jq", ".number"]
        )
        if code != 0 or not out:
            raise ReviewActionError(
                f"gh pr view failed: {err or 'no PR found for this branch'}"
            )
        return out

    def list_unresolved_comments(self, pr_id: str) -> list[ReviewComment]:
        # REST only returns comments, not thread resolution state or thread
        # node IDs — GraphQL is required to know which threads are still
        # open and to get a threadId that resolve_thread() can act on.
        query = """
        query($owner:String!,$repo:String!,$number:Int!){
          repository(owner:$owner,name:$repo){
            pullRequest(number:$number){
              reviewThreads(first:100){
                nodes{
                  id isResolved
                  comments(first:1){ nodes{ databaseId body path line author{login} } }
                }
              }
            }
          }
        }"""
        code, out, err = _run(
            [
                "gh",
                "api",
                "graphql",
                "-f",
                f"query={query}",
                "-f",
                f"owner={self.info.owner}",
                "-f",
                f"repo={self.info.repo}",
                "-F",
                f"number={pr_id}",
            ]
        )
        if code != 0:
            raise ReviewActionError(f"gh api graphql (list threads) failed: {err}")
        import json

        data = json.loads(out)
        threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
        result = []
        for t in threads:
            if t["isResolved"]:
                continue
            c = t["comments"]["nodes"][0]
            result.append(
                ReviewComment(
                    comment_id=str(c["databaseId"]),
                    thread_id=t["id"],
                    path=c.get("path", ""),
                    line=c.get("line"),
                    author=c.get("author", {}).get("login", "unknown"),
                    body=c["body"],
                )
            )
        return result

    def reply_to_comment(self, pr_id: str, comment: ReviewComment, body: str) -> None:
        code, _, err = _run(
            [
                "gh",
                "api",
                f"repos/{self.info.owner}/{self.info.repo}/pulls/comments/{comment.comment_id}/replies",
                "-f",
                f"body={body}",
            ]
        )
        if code != 0:
            raise ReviewActionError(f"gh api reply failed: {err}")

    def resolve_thread(self, pr_id: str, comment: ReviewComment) -> None:
        mutation = "mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}"
        code, _, err = _run(
            [
                "gh",
                "api",
                "graphql",
                "-f",
                f"query={mutation}",
                "-f",
                f"id={comment.thread_id}",
            ]
        )
        if code != 0:
            raise ReviewActionError(f"gh api graphql (resolve) failed: {err}")

    def request_review(self, pr_id: str, reviewer: str) -> None:
        code, _, err = _run(["gh", "pr", "edit", pr_id, "--add-reviewer", reviewer])
        if code != 0:
            raise ReviewActionError(f"gh pr edit --add-reviewer failed: {err}")


class GitLabProvider:
    name = "GitLab"

    def __init__(self, info: RemoteInfo):
        self.info = info

    def _glab_available(self) -> bool:
        code, _, _ = _run(["glab", "--version"])
        return code == 0

    def create_pr(self, title: str, body: str, base: str, branch: str) -> str:
        if self._glab_available():
            code, out, err = _run(
                [
                    "glab",
                    "mr",
                    "create",
                    "--title",
                    title,
                    "--description",
                    body,
                    "--target-branch",
                    base,
                    "--source-branch",
                    branch,
                    "--yes",
                ]
            )
            if code != 0:
                raise PrCreateError(f"glab mr create failed: {err}")
            # glab prints progress lines then the MR URL last
            lines = [line for line in out.splitlines() if line.strip()]
            return lines[-1] if lines else out

        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise PrCreateError(
                "glab CLI not found and GITLAB_TOKEN not set — "
                "install glab (https://gitlab.com/gitlab-org/cli) or export GITLAB_TOKEN"
            )
        import requests

        resp = requests.post(
            f"https://gitlab.com/api/v4/projects/{self._encoded_project()}/merge_requests",
            headers={"PRIVATE-TOKEN": token},
            json={
                "source_branch": branch,
                "target_branch": base,
                "title": title,
                "description": body,
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise PrCreateError(
                f"GitLab API error {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json().get("web_url", "")

    def _encoded_project(self) -> str:
        project_path = (
            f"{self.info.owner}/{self.info.repo}" if self.info.owner else self.info.repo
        )
        return project_path.replace("/", "%2F")

    def _token(self) -> str:
        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise ReviewActionError(
                "GITLAB_TOKEN not set — export a personal/project access "
                "token with api scope"
            )
        return token

    # ── Review comments (backs /address-review) ───────────────────────────

    def get_pr_number(self, branch: str) -> str:
        import requests

        resp = requests.get(
            f"https://gitlab.com/api/v4/projects/{self._encoded_project()}/merge_requests",
            headers={"PRIVATE-TOKEN": self._token()},
            params={"source_branch": branch, "state": "opened"},
            timeout=30,
        )
        if resp.status_code >= 300 or not resp.json():
            raise ReviewActionError(f"No open merge request found for branch {branch}")
        return str(resp.json()[0]["iid"])

    def list_unresolved_comments(self, pr_id: str) -> list[ReviewComment]:
        import requests

        resp = requests.get(
            f"https://gitlab.com/api/v4/projects/{self._encoded_project()}"
            f"/merge_requests/{pr_id}/discussions",
            headers={"PRIVATE-TOKEN": self._token()},
            params={"per_page": 100},
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ReviewActionError(
                f"GitLab API error {resp.status_code}: {resp.text[:200]}"
            )
        result = []
        for disc in resp.json():
            notes = disc.get("notes", [])
            if not notes:
                continue
            first = notes[0]
            if not first.get("resolvable") or first.get("resolved"):
                continue
            pos = first.get("position") or {}
            result.append(
                ReviewComment(
                    comment_id=str(first["id"]),
                    thread_id=disc["id"],
                    path=pos.get("new_path", ""),
                    line=pos.get("new_line"),
                    author=first.get("author", {}).get("username", "unknown"),
                    body=first["body"],
                )
            )
        return result

    def reply_to_comment(self, pr_id: str, comment: ReviewComment, body: str) -> None:
        import requests

        resp = requests.post(
            f"https://gitlab.com/api/v4/projects/{self._encoded_project()}"
            f"/merge_requests/{pr_id}/discussions/{comment.thread_id}/notes",
            headers={"PRIVATE-TOKEN": self._token()},
            json={"body": body},
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ReviewActionError(
                f"GitLab API error {resp.status_code}: {resp.text[:200]}"
            )

    def resolve_thread(self, pr_id: str, comment: ReviewComment) -> None:
        import requests

        resp = requests.put(
            f"https://gitlab.com/api/v4/projects/{self._encoded_project()}"
            f"/merge_requests/{pr_id}/discussions/{comment.thread_id}",
            headers={"PRIVATE-TOKEN": self._token()},
            params={"resolved": "true"},
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ReviewActionError(
                f"GitLab API error {resp.status_code}: {resp.text[:200]}"
            )

    def request_review(self, pr_id: str, reviewer: str) -> None:
        import requests

        token = self._token()
        headers = {"PRIVATE-TOKEN": token}
        user_resp = requests.get(
            "https://gitlab.com/api/v4/users",
            headers=headers,
            params={"username": reviewer},
            timeout=30,
        )
        if user_resp.status_code >= 300 or not user_resp.json():
            raise ReviewActionError(f"GitLab user '{reviewer}' not found")
        user_id = user_resp.json()[0]["id"]
        resp = requests.put(
            f"https://gitlab.com/api/v4/projects/{self._encoded_project()}/merge_requests/{pr_id}",
            headers=headers,
            json={"reviewer_ids": [user_id]},
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ReviewActionError(
                f"GitLab API error {resp.status_code}: {resp.text[:200]}"
            )


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
            raise PrCreateError(
                "Could not determine Bitbucket workspace/repo from git remote"
            )

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
            raise PrCreateError(
                f"Bitbucket API error {resp.status_code}: {resp.text[:200]}"
            )
        data = resp.json()
        return data.get("links", {}).get("html", {}).get("href", "")

    def _auth(self) -> tuple[str, str]:
        username = os.environ.get("BITBUCKET_USERNAME")
        app_password = os.environ.get("BITBUCKET_APP_PASSWORD")
        if not username or not app_password:
            raise ReviewActionError(
                "BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD env vars are required"
            )
        return username, app_password

    # ── Review comments (backs /address-review) ───────────────────────────
    # Bitbucket Cloud's comment model is simpler than GitHub/GitLab's: there
    # is no separate "resolve thread" endpoint distinct from the comment
    # itself, and no dedicated re-request-review call. resolve_thread() and
    # request_review() below are best-effort — they use the closest
    # documented Bitbucket operation, but are less certain than the
    # GitHub/GitLab implementations and worth a manual check the first time.

    def get_pr_number(self, branch: str) -> str:
        import requests

        resp = requests.get(
            f"https://api.bitbucket.org/2.0/repositories/{self.info.owner}/{self.info.repo}/pullrequests",
            auth=self._auth(),
            params={"q": f'source.branch.name="{branch}"'},
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ReviewActionError(
                f"Bitbucket API error {resp.status_code}: {resp.text[:200]}"
            )
        values = resp.json().get("values", [])
        if not values:
            raise ReviewActionError(f"No open pull request found for branch {branch}")
        return str(values[0]["id"])

    def list_unresolved_comments(self, pr_id: str) -> list[ReviewComment]:
        import requests

        resp = requests.get(
            f"https://api.bitbucket.org/2.0/repositories/{self.info.owner}/{self.info.repo}"
            f"/pullrequests/{pr_id}/comments",
            auth=self._auth(),
            params={"pagelen": 100},
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ReviewActionError(
                f"Bitbucket API error {resp.status_code}: {resp.text[:200]}"
            )
        result = []
        for c in resp.json().get("values", []):
            if c.get("deleted") or c.get("resolved"):
                continue
            inline = c.get("inline") or {}
            result.append(
                ReviewComment(
                    comment_id=str(c["id"]),
                    thread_id=str(c["id"]),
                    path=inline.get("path", ""),
                    line=inline.get("to") or inline.get("from"),
                    author=c.get("user", {}).get("display_name", "unknown"),
                    body=c.get("content", {}).get("raw", ""),
                )
            )
        return result

    def reply_to_comment(self, pr_id: str, comment: ReviewComment, body: str) -> None:
        import requests

        resp = requests.post(
            f"https://api.bitbucket.org/2.0/repositories/{self.info.owner}/{self.info.repo}"
            f"/pullrequests/{pr_id}/comments",
            auth=self._auth(),
            json={"content": {"raw": body}, "parent": {"id": int(comment.comment_id)}},
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ReviewActionError(
                f"Bitbucket API error {resp.status_code}: {resp.text[:200]}"
            )

    def resolve_thread(self, pr_id: str, comment: ReviewComment) -> None:
        # No distinct "resolve" endpoint is reliably documented for Bitbucket
        # Cloud comments — resolution here means "acknowledged via reply".
        # The reviewer marks it resolved manually in the Bitbucket UI.
        raise ReviewActionError(
            "Bitbucket has no API-level thread resolution — the reply is posted "
            "(see reply_to_comment); ask the reviewer to resolve it in the UI"
        )

    def request_review(self, pr_id: str, reviewer: str) -> None:
        # Bitbucket has no single "request re-review" call; adding/re-adding
        # a participant with role=REVIEWER is the closest equivalent.
        import requests

        resp = requests.put(
            f"https://api.bitbucket.org/2.0/repositories/{self.info.owner}/{self.info.repo}"
            f"/pullrequests/{pr_id}/",
            auth=self._auth(),
            json={
                "participants": [{"user": {"nickname": reviewer}, "role": "REVIEWER"}]
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ReviewActionError(
                f"Bitbucket API error {resp.status_code}: {resp.text[:200]}"
            )


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
        code, out, err = _run(
            [
                "az",
                "repos",
                "pr",
                "create",
                "--title",
                title,
                "--description",
                body,
                "--target-branch",
                base,
                "--source-branch",
                branch,
                "--query",
                "url",
                "--output",
                "tsv",
            ]
        )
        if code != 0:
            raise PrCreateError(f"az repos pr create failed: {err}")
        return out

    def _require_az(self):
        if not self._az_available():
            raise ReviewActionError(
                "az CLI not found — install it and run "
                "'az extension add --name azure-devops', then 'az devops login'"
            )

    # ── Review comments (backs /address-review) ───────────────────────────
    # Reply/resolve go through `az rest` (arbitrary Azure DevOps REST calls
    # using the CLI's own auth) rather than `az repos pr thread` subcommands,
    # since comment-on-existing-thread support varies across az CLI versions
    # — az rest is the more stable surface for these two operations.

    def get_pr_number(self, branch: str) -> str:
        self._require_az()
        code, out, err = _run(
            [
                "az",
                "repos",
                "pr",
                "list",
                "--source-branch",
                branch,
                "--status",
                "active",
                "--query",
                "[0].pullRequestId",
                "--output",
                "tsv",
            ]
        )
        if code != 0 or not out:
            raise ReviewActionError(f"No active PR found for branch {branch}: {err}")
        return out

    def _api_base(self) -> str:
        return f"https://dev.azure.com/{self.info.owner}/{self.info.project}/_apis/git/repositories/{self.info.repo}"

    def list_unresolved_comments(self, pr_id: str) -> list[ReviewComment]:
        self._require_az()
        code, out, err = _run(
            [
                "az",
                "rest",
                "--method",
                "get",
                "--uri",
                f"{self._api_base()}/pullRequests/{pr_id}/threads?api-version=7.1",
            ]
        )
        if code != 0:
            raise ReviewActionError(f"az rest (list threads) failed: {err}")
        import json

        data = json.loads(out)
        result = []
        for t in data.get("value", []):
            if t.get("status") != "active":
                continue
            comments = t.get("comments", [])
            if not comments:
                continue
            first = comments[0]
            ctx = t.get("threadContext") or {}
            result.append(
                ReviewComment(
                    comment_id=str(first["id"]),
                    thread_id=str(t["id"]),
                    path=ctx.get("filePath", ""),
                    line=(ctx.get("rightFileStart") or {}).get("line"),
                    author=first.get("author", {}).get("displayName", "unknown"),
                    body=first.get("content", ""),
                )
            )
        return result

    def reply_to_comment(self, pr_id: str, comment: ReviewComment, body: str) -> None:
        self._require_az()
        import json

        code, _, err = _run(
            [
                "az",
                "rest",
                "--method",
                "post",
                "--uri",
                f"{self._api_base()}/pullRequests/{pr_id}/threads/{comment.thread_id}/comments?api-version=7.1",
                "--body",
                json.dumps({"content": body, "commentType": "text"}),
            ]
        )
        if code != 0:
            raise ReviewActionError(f"az rest (reply) failed: {err}")

    def resolve_thread(self, pr_id: str, comment: ReviewComment) -> None:
        import json

        self._require_az()
        code, _, err = _run(
            [
                "az",
                "rest",
                "--method",
                "patch",
                "--uri",
                f"{self._api_base()}/pullRequests/{pr_id}/threads/{comment.thread_id}?api-version=7.1",
                "--body",
                json.dumps({"status": "fixed"}),
            ]
        )
        if code != 0:
            raise ReviewActionError(f"az rest (resolve) failed: {err}")

    def request_review(self, pr_id: str, reviewer: str) -> None:
        self._require_az()
        code, _, err = _run(
            [
                "az",
                "repos",
                "pr",
                "reviewer",
                "add",
                "--id",
                pr_id,
                "--reviewers",
                reviewer,
            ]
        )
        if code != 0:
            raise ReviewActionError(f"az repos pr reviewer add failed: {err}")


class UnknownHostProvider:
    """No known API/CLI for this host — always raises, triggering the
    manual-fallback message. Preserves the pre-multi-host behavior for
    self-hosted git / anything not recognized."""

    name = "this git host"

    def __init__(self, info: RemoteInfo):
        self.info = info

    def create_pr(self, title: str, body: str, base: str, branch: str) -> str:
        raise PrCreateError("no automated PR creation available for this git host")

    def get_pr_number(self, branch: str) -> str:
        raise ReviewActionError("no automated PR lookup available for this git host")

    def list_unresolved_comments(self, pr_id: str) -> list[ReviewComment]:
        raise ReviewActionError(
            "no automated comment listing available for this git host"
        )

    def reply_to_comment(self, pr_id: str, comment: ReviewComment, body: str) -> None:
        raise ReviewActionError(
            "no automated comment reply available for this git host"
        )

    def resolve_thread(self, pr_id: str, comment: ReviewComment) -> None:
        raise ReviewActionError(
            "no automated thread resolution available for this git host"
        )

    def request_review(self, pr_id: str, reviewer: str) -> None:
        raise ReviewActionError(
            "no automated re-review request available for this git host"
        )


_PROVIDERS = {
    "github": GitHubProvider,
    "gitlab": GitLabProvider,
    "bitbucket": BitbucketProvider,
    "azure": AzureDevOpsProvider,
}


def get_provider(info: RemoteInfo):
    return _PROVIDERS.get(info.host, UnknownHostProvider)(info)
