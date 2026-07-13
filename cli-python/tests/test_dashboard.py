# Unit tests for sdd/commands/dashboard.py's write actions (approve,
# comment) and the input-validation that protects them once --host makes
# the server reachable beyond 127.0.0.1. No live server — these call the
# helper functions directly, same as the HTTP handler does.
from pathlib import Path

from sdd.commands.dashboard import (
    _PAGE, _SAFE_TOKEN, _clip_text, _do_approve, _do_comment, _load_comments,
)


def _scaffold_feature(tmp_path: Path, feature: str = "payments", doc: str = "brd") -> Path:
    feature_dir = tmp_path / ".specify" / "features" / feature
    feature_dir.mkdir(parents=True)
    (feature_dir / f"{doc}.md").write_text(f"# {doc.upper()}\n> Status: Draft | Date: 2026-07-09\n")
    return feature_dir


def test_safe_token_rejects_path_traversal():
    assert _SAFE_TOKEN.match("payments")
    assert _SAFE_TOKEN.match("my-feature_1")
    assert not _SAFE_TOKEN.match("../../etc/passwd")
    assert not _SAFE_TOKEN.match("payments/brd")
    assert not _SAFE_TOKEN.match("")
    assert not _SAFE_TOKEN.match("a b")


def test_clip_text_trims_and_bounds_length():
    assert _clip_text("  hello  ") == "hello"
    assert _clip_text(None) == ""
    assert len(_clip_text("x" * 5000)) <= 2000


def test_approve_flips_status_header_and_records_local_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _scaffold_feature(tmp_path)
    result = _do_approve("payments", "brd", "Jane", "lgtm")

    assert result["local_approval"] is True
    assert result["md_updated"] is True

    md_text = (tmp_path / ".specify" / "features" / "payments" / "brd.md").read_text()
    assert "Status: Approved" in md_text

    approvals_text = (tmp_path / ".specify" / ".local-approvals.yml").read_text()
    assert "Jane" in approvals_text
    assert "lgtm" in approvals_text


def test_approve_without_confluence_or_jira_configured_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _scaffold_feature(tmp_path)
    result = _do_approve("payments", "brd", "Jane", "")
    assert result["confluence"] == {"updated": False, "title": None}
    assert result["jira_comment"]["posted"] is False


def test_approve_missing_doc_reports_error_but_still_records_local_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    result = _do_approve("payments", "brd", "Jane", "")
    assert result["local_approval"] is True
    assert "error" in result
    assert result["md_updated"] is False


def test_approve_blank_by_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _scaffold_feature(tmp_path)
    _do_approve("payments", "brd", "   ", "")
    approvals_text = (tmp_path / ".specify" / ".local-approvals.yml").read_text()
    assert "dashboard user" in approvals_text


def test_comment_saved_feature_scoped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _scaffold_feature(tmp_path)
    result = _do_comment("payments", "brd", "Jane", "please clarify NFR-002")

    assert result["saved"] is True
    assert result["comment"]["by"] == "Jane"
    assert result["comment"]["text"] == "please clarify NFR-002"

    comments = _load_comments()
    assert comments["payments/brd"][0]["text"] == "please clarify NFR-002"


def test_comment_empty_text_returns_error_without_writing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _scaffold_feature(tmp_path)
    result = _do_comment("payments", "brd", "Jane", "   ")
    assert "error" in result
    assert not (tmp_path / ".specify" / ".dashboard-comments.json").exists()


def test_multiple_comments_append_in_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _scaffold_feature(tmp_path)
    _do_comment("payments", "brd", "Jane", "first")
    _do_comment("payments", "brd", "Bob", "second")
    comments = _load_comments()["payments/brd"]
    assert [c["text"] for c in comments] == ["first", "second"]


def test_comment_does_not_leak_across_features(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _scaffold_feature(tmp_path, feature="payments")
    _scaffold_feature(tmp_path, feature="dashboard")
    _do_comment("payments", "brd", "Jane", "payments comment")
    _do_comment("dashboard", "brd", "Bob", "dashboard comment")
    comments = _load_comments()
    assert comments["payments/brd"][0]["text"] == "payments comment"
    assert comments["dashboard/brd"][0]["text"] == "dashboard comment"


# Regression guards for the "typed comment text disappears" bug: the 5s
# auto-poll rebuilds #root wholesale, which used to wipe whatever the user
# was mid-typing into the comment form. Live-browser-verified via Playwright
# during development; these are lightweight source guards so a future edit
# can't silently drop the fix without a test noticing.
def test_page_persists_comment_drafts_across_rerenders():
    assert "commentDrafts" in _PAGE
    # inputs must be re-hydrated from the draft on every render, not left
    # empty, and tagged with data-feature/data-doc so drafts + focus-restore
    # can find the right field after #root is rebuilt
    assert 'class="comment-by"' in _PAGE and "draft.by" in _PAGE
    assert 'class="comment-text"' in _PAGE and "draft.text" in _PAGE
    assert "data-feature=\"${feature}\"" in _PAGE


def test_page_restores_focus_after_periodic_rerender():
    assert "activeElement" in _PAGE
    assert "setSelectionRange" in _PAGE


def test_page_clears_draft_after_successful_comment_submit():
    assert "delete state.commentDrafts" in _PAGE


# Regression guards for the "Full Pipeline" section (shows the complete
# command sequence for this scope/plan mode, current step, and a plain-
# language next-action sentence) — source-level checks, same rationale as
# the comment-draft guards above.
def test_page_renders_full_pipeline_section():
    assert "renderPipelineFlow" in _PAGE
    assert "Full Pipeline" in _PAGE
    assert "pipeline-flow" in _PAGE
    assert "next-action-box" in _PAGE


def test_page_pipeline_shows_scope_and_plan_mode():
    assert "project.scope" in _PAGE
    assert "project.plan_mode" in _PAGE


# Regression guards for the dashboard-side sdd review check equivalent:
# _fetch_review_links must surface the same APPROVED/NEEDS_REVISION/PENDING
# classification and reviewer comments as `sdd review check --doc`, by
# reusing review.py's own _get_review_status rather than re-deriving it.
def test_page_renders_review_status_badge_and_jira_comments():
    assert "reviewStatusBadge" in _PAGE
    assert "Jira review comments" in _PAGE
    assert "kind === 'review'" in _PAGE


def test_fetch_review_links_surfaces_classification_and_comments(tmp_path, monkeypatch):
    import sdd.commands.dashboard as dashboard_mod
    import sdd.utils.integrations as integrations_mod
    import sdd.utils.atlassian_auth as auth_mod
    import sdd.utils.jira_client as jira_client_mod
    from sdd.utils.integrations import IntegrationsConfig, JiraConfig, DocumentReview
    from sdd.utils.atlassian_auth import Profile

    monkeypatch.chdir(tmp_path)

    cfg = IntegrationsConfig(
        profile=None,
        jira=JiraConfig(project_key="PROJ"),
        confluence=None,
        document_reviews={
            "brd": DocumentReview(
                reviewer_jira_user="abc123",
                reviewer_role="Product Owner",
                phase="specify",
                sequence=1,
                confluence_page="{project} — BRD",
            ),
        },
    )
    monkeypatch.setattr(integrations_mod, "load_integrations", lambda: cfg)
    monkeypatch.setattr(auth_mod, "load_profile", lambda name=None: Profile(auth_mode="pat", base_url="https://x.atlassian.net"))
    monkeypatch.setattr(auth_mod, "build_session", lambda profile: object())

    class FakeJiraClient:
        def __init__(self, session, base_url):
            pass

        def find_by_label(self, project_key, label):
            return {"key": "PROJ-9", "fields": {"status": {"name": "In Review"}}}

        def get_comments(self, issue_key):
            return [{
                "author": {"displayName": "Jane Reviewer"},
                "created": "2026-07-10T12:00:00.000+0000",
                "body": "Please fix section 3",
            }]

    monkeypatch.setattr(jira_client_mod, "JiraClient", FakeJiraClient)

    result = dashboard_mod._fetch_review_links("payments")

    brd = result["docs"]["brd"]
    assert brd["jira"]["key"] == "PROJ-9"
    assert brd["jira"]["review_status"] == "NEEDS_REVISION"
    assert brd["jira"]["comments"] == [{
        "author": "Jane Reviewer",
        "created": "2026-07-10",
        "text": "Please fix section 3",
    }]


def test_fetch_review_links_classifies_approved_status(tmp_path, monkeypatch):
    import sdd.commands.dashboard as dashboard_mod
    import sdd.utils.integrations as integrations_mod
    import sdd.utils.atlassian_auth as auth_mod
    import sdd.utils.jira_client as jira_client_mod
    from sdd.utils.integrations import IntegrationsConfig, JiraConfig, DocumentReview
    from sdd.utils.atlassian_auth import Profile

    monkeypatch.chdir(tmp_path)

    cfg = IntegrationsConfig(
        profile=None,
        jira=JiraConfig(project_key="PROJ"),
        confluence=None,
        document_reviews={
            "brd": DocumentReview(
                reviewer_jira_user="abc123",
                reviewer_role="Product Owner",
                phase="specify",
                sequence=1,
                confluence_page="{project} — BRD",
            ),
        },
    )
    monkeypatch.setattr(integrations_mod, "load_integrations", lambda: cfg)
    monkeypatch.setattr(auth_mod, "load_profile", lambda name=None: Profile(auth_mode="pat", base_url="https://x.atlassian.net"))
    monkeypatch.setattr(auth_mod, "build_session", lambda profile: object())

    class FakeJiraClient:
        def __init__(self, session, base_url):
            pass

        def find_by_label(self, project_key, label):
            return {"key": "PROJ-9", "fields": {"status": {"name": "Done"}}}

        def get_comments(self, issue_key):
            return []

    monkeypatch.setattr(jira_client_mod, "JiraClient", FakeJiraClient)

    result = dashboard_mod._fetch_review_links("payments")
    assert result["docs"]["brd"]["jira"]["review_status"] == "APPROVED"
    assert result["docs"]["brd"]["jira"]["comments"] == []


# Regression guard: the dashboard's per-document Jira pill previously had
# no local fallback at all (unlike Confluence's), staying blank until the
# user clicked "Check Jira/Confluence review links" -- local.jira_review
# (status.py's _local_review_links) must be threaded all the way through
# renderFeature -> renderDocs -> renderDocRow and used as a fallback for
# the Jira pill, the same way local.confluence already is.
def test_page_wires_local_jira_review_link_into_doc_row():
    assert "local.jira_review" in _PAGE
    assert "localJiraReview" in _PAGE
    assert "reviewJira || localJira" in _PAGE
