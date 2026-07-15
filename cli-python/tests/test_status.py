# Unit tests for sdd/utils/status.py — the read-only snapshot that
# `sdd dashboard` and `sdd status` render. Pure filesystem reads, no
# network/Jira dependency (unlike `sdd review status`).
from pathlib import Path

import sdd.utils.status as status_mod
from sdd.utils.status import (
    build_project_status, build_feature_status, build_pipeline,
    _current_stage, persona_for,
)


def _write_manifest(root: Path, scope_line: str = "") -> None:
    (root / ".specify").mkdir(parents=True, exist_ok=True)
    (root / ".specify" / "manifest.yml").write_text(
        'project:\n'
        '  name: "Demo"\n'
        '  feature: "payments"\n'
        '  context_file: "payments.md"\n'
        + scope_line +
        'project_type: "backend-service"\n'
        'workflow_mode: "local"\n'
        'sdd_version: "2.7.14"\n'
    )


def test_project_fields_come_from_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path, '  scope: "pilot"\n')
    status = build_project_status(".")
    assert status["project"]["name"] == "Demo"
    assert status["project"]["workflow_mode"] == "local"
    assert status["project"]["sdd_version"] == "2.7.14"


def test_missing_manifest_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    status = build_project_status(".")
    assert status["project"]["name"] is None
    assert status["features"] == []


def test_discovers_multiple_features(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    for f in ["payments", "dashboard"]:
        (tmp_path / ".specify" / "features" / f).mkdir(parents=True)
    status = build_project_status(".")
    names = sorted(f["name"] for f in status["features"])
    assert names == ["dashboard", "payments"]


def test_doc_status_header_parsed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\n> Version: 1.0 | Status: Approved | Date: 2026-01-01\n"
    )
    (feature_dir / "srd.md").write_text(
        "# SRD\n> Version: 1.0 | Status: Draft | Date: 2026-01-02\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    by_key = {d["key"]: d for d in feat["docs"]}
    assert by_key["brd"]["status"] == "Approved"
    assert by_key["srd"]["status"] == "Draft"


def test_current_stage_reports_last_doc_and_next(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Approved\n")
    (feature_dir / "use-cases.md").write_text("> Status: Approved\n")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["current_stage"]["doc"] == "Use Cases"
    assert feat["current_stage"]["next"] == "SRD"


def test_current_stage_awaiting_approval_when_not_approved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Draft\n")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["current_stage"]["next"] == "(awaiting approval)"


def test_summary_docs_are_excluded_from_doc_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Approved\n")
    (feature_dir / "brd.summary.md").write_text("summary text\n")
    feat = build_feature_status(tmp_path, "payments")
    keys = [d["key"] for d in feat["docs"]]
    assert keys == ["brd"]


def test_token_usage_excluded_from_doc_list(tmp_path, monkeypatch):
    """token-usage.md is rendered in its own Token Usage card — it must
    not also show up in the Pipeline docs list."""
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Approved\n")
    (feature_dir / "token-usage.md").write_text("## Running Totals\n")
    feat = build_feature_status(tmp_path, "payments")
    keys = [d["key"] for d in feat["docs"]]
    assert keys == ["brd"]


def test_tasks_full_pack_format_uses_checkboxes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text(
        "## Phase A\n"
        "### TASK-001 — Scaffold\n"
        "Acceptance criteria:\n"
        "  - [x] one\n"
        "  - [x] two\n"
        "### TASK-002 — Domain models\n"
        "Acceptance criteria:\n"
        "  - [x] one\n"
        "  - [ ] two\n"
        "### TASK-003 — Contracts\n"
        "Acceptance criteria:\n"
        "  - [ ] one\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    tasks = feat["tasks"]
    assert tasks["format"] == "full"
    assert tasks["total"] == 3
    assert tasks["done"] == 1
    assert tasks["in_progress"] == 1
    assert tasks["not_started"] == 1


def test_tasks_micro_format_uses_status_field(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text(
        "## TASK-001 — Write script\n"
        "- **Steps:** do the thing\n"
        "- **Verify:** run it\n"
        "- **Status:** Done\n"
        "## TASK-002 — Add tests\n"
        "- **Steps:** write tests\n"
        "- **Verify:** pytest\n"
        "- **Status:** Not Started\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    tasks = feat["tasks"]
    assert tasks["format"] == "micro"
    assert tasks["total"] == 2
    assert tasks["done"] == 1
    assert tasks["not_started"] == 1


def test_no_tasks_file_returns_empty_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    feat = build_feature_status(tmp_path, "payments")
    assert feat["tasks"]["total"] == 0
    assert feat["tasks"]["format"] == "none"


def test_token_usage_parsed_from_running_totals(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "token-usage.md").write_text(
        "## Running Totals\n\n"
        "| Metric | Value |\n"
        "|---|---|\n"
        "| Total Input Tokens | 12345 |\n"
        "| Total Output Tokens | 6789 |\n"
        "| Total Cost (USD) | 0.42 |\n"
        "| Commands logged | 5 |\n"
        "| Last updated | 2026-07-08 |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    tu = feat["token_usage"]
    assert tu["total_input"] == "12345"
    assert tu["total_output"] == "6789"
    assert tu["total_cost"] == "0.42"
    assert tu["commands_logged"] == "5"


def test_token_usage_parsed_from_legacy_est_labels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "token-usage.md").write_text(
        "## Running Totals\n\n"
        "| Metric | Value |\n"
        "|---|---|\n"
        "| Total Est. Input Tokens | 12345 |\n"
        "| Total Est. Output Tokens | 6789 |\n"
        "| Total Est. Cost (USD) | 0.42 |\n"
        "| Commands logged | 5 |\n"
        "| Last updated | 2026-07-08 |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    tu = feat["token_usage"]
    assert tu["total_input"] == "12345"
    assert tu["total_output"] == "6789"
    assert tu["total_cost"] == "0.42"
    assert tu["commands_logged"] == "5"


def test_token_usage_absent_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    feat = build_feature_status(tmp_path, "payments")
    assert feat["token_usage"] is None


def test_constitution_gate1_pending_with_no_downstream_docs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text("# Constitution\n")
    status = build_project_status(".")
    assert status["constitution"]["exists"] is True
    assert status["constitution"]["gate1_inferred"] == "pending_or_unknown"


def test_constitution_gate1_passed_when_downstream_doc_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text("# Constitution\n")
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Draft\n")
    status = build_project_status(".")
    assert status["constitution"]["gate1_inferred"] == "passed"


def test_constitution_gate1_passed_for_micro_style_tasks_only(tmp_path, monkeypatch):
    """sdd-micro never writes a per-feature spec doc besides tasks.md —
    GATE-1 must still be inferred as passed once tasks.md exists, since
    /task refuses to run before GATE-1 in that pack too."""
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text("# Constitution\n")
    feature_dir = tmp_path / ".specify" / "features" / "greeter"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text("## TASK-001 — x\n- **Status:** Not Started\n")
    status = build_project_status(".")
    assert status["constitution"]["gate1_inferred"] == "passed"


def test_constitution_missing_reports_not_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    status = build_project_status(".")
    assert status["constitution"]["exists"] is False


def test_constitution_freshly_scaffolded_template_is_not_part2_generated(tmp_path, monkeypatch):
    """Regression: `sdd init` scaffolds constitution.md for every project,
    Part 2 full of {extracted from context} / {derived} / {date}
    placeholders, before /specify ever runs. That file existing on disk
    must not be reported as Part 2 having been generated."""
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n"
        "# PART 2 — PROJECT (Generated by SPECIFY from context.md)\n"
        "## Tech Stack\n"
        "| Concern | Choice |\n"
        "|---|---|\n"
        "| Language | {extracted from context} |\n"
    )
    status = build_project_status(".")
    assert status["constitution"]["exists"] is True
    assert status["constitution"]["part2_generated"] is False
    assert status["constitution"]["gate1_inferred"] == "unknown"


def test_constitution_part2_filled_in_is_reported_as_generated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n"
        "# PART 2 — PROJECT (Generated by SPECIFY from context.md)\n"
        "## Tech Stack\n"
        "| Concern | Choice |\n"
        "|---|---|\n"
        "| Language | Python |\n"
    )
    status = build_project_status(".")
    assert status["constitution"]["part2_generated"] is True


# ── Local Jira/Confluence link resolution (no network) ────────────────────

def test_jira_keys_yield_no_links_without_keys_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["jira"] == {"epic": None, "stories": [], "tasks": []}


def test_jira_keys_parsed_with_base_url(tmp_path, monkeypatch):
    """Real keys.yml shape, as actually written by jira.py's
    _save_keys_summary(): epic is a plain string, stories/tasks are
    {sdd_id: jira_key} dicts -- NOT dicts/lists of {"jira_key": ...}."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: "https://acme.atlassian.net")
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    jira_dir = tmp_path / "docs" / "jira" / "payments"
    jira_dir.mkdir(parents=True)
    (jira_dir / "keys.yml").write_text(
        "epic: PROJ-1\n"
        "stories:\n  STORY-001: PROJ-2\n  STORY-002: PROJ-3\n"
        "tasks:\n  TASK-001: PROJ-4\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    jira = feat["local_links"]["jira"]
    assert jira["epic"] == {"key": "PROJ-1", "url": "https://acme.atlassian.net/browse/PROJ-1"}
    assert sorted(s["key"] for s in jira["stories"]) == ["PROJ-2", "PROJ-3"]
    assert jira["tasks"][0]["url"] == "https://acme.atlassian.net/browse/PROJ-4"


def test_jira_keys_legacy_dict_shape_still_parses(tmp_path, monkeypatch):
    """Regression: a real user's dashboard crashed with AttributeError
    ('str' object has no attribute 'get') because status.py's reader
    assumed keys.yml's epic/stories/tasks were dicts/lists of dicts with a
    'jira_key' field, while jira.py's actual writer produces a plain
    string for epic and flat {id: key} dicts for stories/tasks. Verify the
    real (current) shape parses AND the old {"jira_key": ...}-per-entry
    shape (in case of a hand-edited or pre-migration keys.yml) doesn't
    crash either -- both must resolve to the same links."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: "https://acme.atlassian.net")
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    jira_dir = tmp_path / "docs" / "jira" / "payments"
    jira_dir.mkdir(parents=True)
    (jira_dir / "keys.yml").write_text(
        "epic:\n  jira_key: PROJ-1\n"
        "stories:\n  - jira_key: PROJ-2\n  - jira_key: PROJ-3\n"
        "tasks:\n  - jira_key: PROJ-4\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    jira = feat["local_links"]["jira"]
    assert jira["epic"] == {"key": "PROJ-1", "url": "https://acme.atlassian.net/browse/PROJ-1"}
    assert sorted(s["key"] for s in jira["stories"]) == ["PROJ-2", "PROJ-3"]
    assert jira["tasks"][0]["key"] == "PROJ-4"


def test_jira_keys_round_trip_through_real_writer(tmp_path, monkeypatch):
    """End-to-end: call jira.py's actual _save_keys_summary() (the real
    writer of docs/jira/{feature}/keys.yml), then confirm status.py's
    reader parses exactly what it wrote. Locks the writer/reader contract
    together so a future change to either side that breaks the other
    fails a test instead of only surfacing as a live dashboard crash."""
    from sdd.commands.jira import _save_keys_summary

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: "https://acme.atlassian.net")
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)

    _save_keys_summary(
        "payments", "PROJ-1",
        {"STORY-001": "PROJ-2", "STORY-002": "PROJ-3"},
        {"TASK-001": "PROJ-4"},
        None, {},
    )

    feat = build_feature_status(tmp_path, "payments")
    jira = feat["local_links"]["jira"]
    assert jira["epic"] == {"key": "PROJ-1", "url": "https://acme.atlassian.net/browse/PROJ-1"}
    assert sorted(s["key"] for s in jira["stories"]) == ["PROJ-2", "PROJ-3"]
    assert jira["tasks"][0]["key"] == "PROJ-4"


def test_jira_keys_scoped_to_own_feature(tmp_path, monkeypatch):
    """A different feature's keys.yml must never leak into this feature's links."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: "https://acme.atlassian.net")
    _write_manifest(tmp_path)
    for f in ["payments", "dashboard"]:
        (tmp_path / ".specify" / "features" / f).mkdir(parents=True)
    jira_dir = tmp_path / "docs" / "jira" / "dashboard"
    jira_dir.mkdir(parents=True)
    (jira_dir / "keys.yml").write_text("epic: OTHER-1\n")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["jira"]["epic"] is None


def test_jira_keys_without_base_url_omit_url_but_keep_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    jira_dir = tmp_path / "docs" / "jira" / "payments"
    jira_dir.mkdir(parents=True)
    (jira_dir / "keys.yml").write_text("epic: PROJ-1\n")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["jira"]["epic"] == {"key": "PROJ-1", "url": None}


def test_confluence_drafts_parsed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: "https://acme.atlassian.net")
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    (tmp_path / ".specify" / ".confluence-drafts.json").write_text(
        '{"brd": {"page_id": "123", "title": "Acme \\u2014 BRD"}}'
    )
    feat = build_feature_status(tmp_path, "payments")
    cf = feat["local_links"]["confluence"]
    assert cf["brd"]["url"] == "https://acme.atlassian.net/wiki/pages/viewpage.action?pageId=123"
    assert cf["brd"]["title"] == "Acme — BRD"


def test_confluence_drafts_absent_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["confluence"] == {}


def test_review_links_parsed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: "https://acme.atlassian.net")
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    (tmp_path / ".specify" / ".jira-review-links.json").write_text(
        '{"brd": {"key": "PROJ-9"}}'
    )
    feat = build_feature_status(tmp_path, "payments")
    review_links = feat["local_links"]["jira_review"]
    assert review_links["brd"] == {
        "key": "PROJ-9",
        "url": "https://acme.atlassian.net/browse/PROJ-9",
    }


def test_review_links_without_base_url_omit_url_but_keep_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    (tmp_path / ".specify" / ".jira-review-links.json").write_text(
        '{"brd": {"key": "PROJ-9"}}'
    )
    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["jira_review"]["brd"] == {"key": "PROJ-9", "url": None}


def test_review_links_absent_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["jira_review"] == {}


def test_malformed_review_links_json_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    (tmp_path / ".specify" / ".jira-review-links.json").write_text("not valid json {")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["jira_review"] == {}


def test_review_links_entry_missing_key_is_skipped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    (tmp_path / ".specify" / ".jira-review-links.json").write_text(
        '{"brd": {}, "srd": {"key": "PROJ-2"}}'
    )
    feat = build_feature_status(tmp_path, "payments")
    review_links = feat["local_links"]["jira_review"]
    assert "brd" not in review_links
    assert review_links["srd"]["key"] == "PROJ-2"


def test_review_links_round_trip_through_real_writer(tmp_path, monkeypatch):
    """End-to-end: call review.py's actual _record_review_link() (the real
    writer of .specify/.jira-review-links.json), then confirm status.py's
    reader parses exactly what it wrote. Same writer/reader contract lock
    as test_jira_keys_round_trip_through_real_writer above."""
    from sdd.commands.review import _record_review_link

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: "https://acme.atlassian.net")
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)

    _record_review_link("brd", "PROJ-9")

    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["jira_review"]["brd"] == {
        "key": "PROJ-9",
        "url": "https://acme.atlassian.net/browse/PROJ-9",
    }


def test_malformed_keys_yml_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    jira_dir = tmp_path / "docs" / "jira" / "payments"
    jira_dir.mkdir(parents=True)
    (jira_dir / "keys.yml").write_text("not: valid: yaml: [")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["local_links"]["jira"] == {"epic": None, "stories": [], "tasks": []}


# ── Approval / comment state surfaced per doc ──────────────────────────────

def test_doc_has_no_local_approval_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Draft\n")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["docs"][0]["local_approval"] is None
    assert feat["docs"][0]["comments"] == []


def test_doc_local_approval_read_from_approvals_file(tmp_path, monkeypatch):
    """Same file/key format `sdd review approve --local` writes — bare doc
    name, not feature-scoped (see dashboard.py's _do_approve docstring)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Approved\n")
    (tmp_path / ".specify" / ".local-approvals.yml").write_text(
        "brd:\n  approved_by: \"Jane\"\n  approved_at: \"2026-07-09\"\n  note: \"lgtm\"\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    approval = feat["docs"][0]["local_approval"]
    assert approval["approved_by"] == "Jane"
    assert approval["note"] == "lgtm"


def test_malformed_local_approvals_file_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Draft\n")
    (tmp_path / ".specify" / ".local-approvals.yml").write_text("not: valid: [")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["docs"][0]["local_approval"] is None


def test_doc_comments_read_and_feature_scoped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    for f in ["payments", "dashboard"]:
        feature_dir = tmp_path / ".specify" / "features" / f
        feature_dir.mkdir(parents=True)
        (feature_dir / "brd.md").write_text("> Status: Draft\n")
    (tmp_path / ".specify" / ".dashboard-comments.json").write_text(
        '{"payments/brd": [{"by": "Jane", "text": "looks good", "at": "2026-07-09T00:00:00+00:00"}],'
        ' "dashboard/brd": [{"by": "Bob", "text": "different feature", "at": "2026-07-09T00:00:00+00:00"}]}'
    )
    payments = build_feature_status(tmp_path, "payments")
    dashboard = build_feature_status(tmp_path, "dashboard")
    assert [c["text"] for c in payments["docs"][0]["comments"]] == ["looks good"]
    assert [c["text"] for c in dashboard["docs"][0]["comments"]] == ["different feature"]


def test_malformed_comments_file_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Draft\n")
    (tmp_path / ".specify" / ".dashboard-comments.json").write_text("not valid json {")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["docs"][0]["comments"] == []


# ── Full Pipeline (build_pipeline) ──────────────────────────────────────

_NO_TASKS = {"total": 0, "done": 0}
_NOT_STARTED = {"exists": False, "gate1_inferred": "unknown"}
_GATE1_PASSED = {"exists": True, "part2_generated": True, "gate1_inferred": "passed"}


def _step(pipeline, step_id):
    return next(s for s in pipeline["steps"] if s["id"] == step_id)


def test_pipeline_fresh_project_starts_at_specify():
    p = build_pipeline([], _NO_TASKS, _NOT_STARTED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot")
    assert _step(p, "specify")["state"] == "upcoming"
    assert p["next_step_id"] == "specify"
    assert "/specify" in p["next_action"]


def test_pipeline_awaiting_gate1_after_constitution_exists():
    p = build_pipeline([], _NO_TASKS,
                        {"exists": True, "part2_generated": True, "gate1_inferred": "pending_or_unknown"},
                        service_docs_exist=False, plan_mode="unified", scope="pilot")
    assert _step(p, "specify")["state"] == "done"
    assert _step(p, "gate1")["state"] == "current"
    assert p["next_step_id"] == "gate1"
    assert "finalized" in p["next_action"]


def test_pipeline_constitution_file_scaffolded_but_specify_not_run_yet_is_upcoming():
    """Regression: constitution.md is scaffolded by `sdd init` for every
    project (Part 1 boilerplate + a Part 2 template full of placeholders) --
    the file existing on disk must NOT make the 'Constitution (Part 2)' step
    show done before /specify has actually filled it in."""
    p = build_pipeline([], _NO_TASKS,
                        {"exists": True, "part2_generated": False, "gate1_inferred": "unknown"},
                        service_docs_exist=False, plan_mode="unified", scope="pilot")
    assert _step(p, "specify")["state"] == "upcoming"
    assert _step(p, "gate1")["state"] == "upcoming"
    assert p["next_step_id"] == "specify"


def test_pipeline_doc_awaiting_review_is_current_not_done():
    docs = [{"key": "brd", "status": "Draft"}]
    p = build_pipeline(docs, _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot")
    assert _step(p, "brd")["state"] == "current"
    assert p["next_step_id"] == "brd"
    assert "sdd review check --doc brd" in p["next_action"]


def test_pipeline_approved_doc_counts_as_done():
    docs = [{"key": "brd", "status": "Approved"}]
    p = build_pipeline(docs, _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot")
    assert _step(p, "brd")["state"] == "done"
    assert p["next_step_id"] == "use-cases"


def test_pipeline_bypassed_optional_step_does_not_win_next_action():
    """Regression: user-reported. At pilot scope, checklist is optional
    (step.optional=True) and this project never ran /checklist -- but BRD/
    Use Cases/SRD are approved and validate.md already exists (awaiting
    review). Since checklist's doc never exists, _step_state alone always
    returns "upcoming" for it, and the old code picked the first non-done
    step in list order -- surfacing "Run /checklist" as the dashboard's
    Next: text while the pipeline diagram itself showed validate as the
    current step. The bypass check must let build_pipeline skip past an
    optional step once a later step already exists on disk."""
    docs = [
        {"key": "brd", "status": "Approved"},
        {"key": "use-cases", "status": "Approved"},
        {"key": "srd", "status": "Approved"},
        {"key": "validate", "status": "Draft"},
    ]
    p = build_pipeline(docs, _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot")
    assert _step(p, "checklist")["state"] == "upcoming"
    assert _step(p, "validate")["state"] == "current"
    assert p["next_step_id"] == "validate"
    assert "checklist" not in p["next_action"].lower()
    assert "sdd review check --doc validate" in p["next_action"]


def test_pipeline_optional_step_not_yet_reached_is_still_picked_as_next():
    """Sanity check the fix doesn't over-trigger: when checklist genuinely
    hasn't been reached yet (nothing later exists either), it must still
    be picked as next_action like any other upcoming step."""
    docs = [
        {"key": "brd", "status": "Approved"},
        {"key": "use-cases", "status": "Approved"},
        {"key": "srd", "status": "Approved"},
    ]
    p = build_pipeline(docs, _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot")
    assert p["next_step_id"] == "checklist"
    assert "/checklist" in p["next_action"]


def test_pipeline_pilot_scope_skips_lld_adr_extended_specs_runbook_qa():
    p = build_pipeline([], _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot")
    for step_id in ("extended-specs", "lld", "runbook", "qa-testcases"):
        step = _step(p, step_id)
        assert step["state"] == "skipped", step_id
        assert step["skip"]
    # pilot uses smoke-tests instead of qa-testcases
    assert _step(p, "smoke-tests")["skip"] is None


def test_pipeline_mvp_scope_includes_lld_adr_runbook_qa_skips_smoke_tests():
    p = build_pipeline([], _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="separate", scope="mvp")
    for step_id in ("extended-specs", "lld", "runbook", "qa-testcases", "adr"):
        assert _step(p, step_id)["skip"] is None, step_id
    assert _step(p, "smoke-tests")["skip"]


def test_pipeline_unified_plan_mode_skips_arch_hld_adr_uses_design():
    p = build_pipeline([], _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="mvp")
    assert _step(p, "design")["skip"] is None
    for step_id in ("arch", "hld", "adr"):
        assert _step(p, step_id)["skip"], step_id


def test_pipeline_separate_plan_mode_skips_design_uses_arch_hld_adr():
    p = build_pipeline([], _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="separate", scope="mvp")
    assert _step(p, "design")["skip"]
    for step_id in ("arch", "hld", "adr"):
        assert _step(p, step_id)["skip"] is None, step_id


def test_pipeline_implement_reflects_task_progress():
    approved = {"status": "Approved"}
    docs = [{"key": k, **approved} for k in
            ("brd", "use-cases", "srd", "checklist", "validate", "analyze", "clarify",
             "design", "stories", "tasks", "smoke-tests")]
    p = build_pipeline(docs, {"total": 4, "done": 2}, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot")
    assert _step(p, "implement")["state"] == "current"
    assert "2/4" in p["next_action"]


def test_pipeline_all_done_reports_complete():
    approved = {"status": "Approved"}
    docs = [{"key": k, **approved} for k in
            ("brd", "use-cases", "srd", "checklist", "validate", "analyze", "clarify",
             "design", "stories", "tasks", "smoke-tests", "release")]
    tasks = {"total": 2, "done": 2}
    p = build_pipeline(docs, tasks, _GATE1_PASSED, service_docs_exist=True,
                        plan_mode="unified", scope="pilot")
    assert p["next_step_id"] is None
    assert "complete" in p["next_action"]


def test_pipeline_micro_scope_none_uses_3_command_flow():
    p = build_pipeline([], _NO_TASKS, _NOT_STARTED, service_docs_exist=False,
                        plan_mode="unified", scope=None)
    assert [s["id"] for s in p["steps"]] == ["specify", "gate1", "task", "implement"]


# ── Persona Hints (Virtual Team) ─────────────────────────────────────────

def test_pipeline_next_persona_names_the_owning_team_member():
    docs = [{"key": "brd", "status": "Approved"}]
    p = build_pipeline(docs, _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot", feature="payments")
    assert p["next_step_id"] == "use-cases"
    assert p["next_persona"]["name"] == "Maya"
    assert p["next_persona"]["role"] == "Business Analyst"
    assert "payments" in p["next_persona"]["ask"]


def test_step_persona_present_on_every_resolved_step_with_an_owner():
    p = build_pipeline([], _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot", feature="payments")
    assert _step(p, "srd")["persona"]["name"] == "Rex"
    assert _step(p, "design")["persona"]["name"] == "Ava"
    assert _step(p, "release")["persona"]["name"] == "Riley"


def test_specify_and_gate1_have_no_persona_owner():
    """Run before any Virtual Team member takes over -- see _STEP_PERSONA's
    docstring in status.py."""
    p = build_pipeline([], _NO_TASKS, _NOT_STARTED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot")
    assert _step(p, "specify")["persona"] is None
    assert _step(p, "gate1")["persona"] is None


def test_micro_scope_never_gets_a_persona_hint():
    """sdd-micro has no Virtual Team at all (see its own CLAUDE.md)."""
    p = build_pipeline([], _NO_TASKS, _NOT_STARTED, service_docs_exist=False,
                        plan_mode="unified", scope=None)
    for step in p["steps"]:
        assert step["persona"] is None
    assert p["next_persona"] is None


def test_pipeline_awaiting_review_suppresses_the_creation_phrased_ask():
    """A doc that already exists and is awaiting review isn't waiting to be
    *created* -- the ask templates are all creation-phrased ('create the
    BRD'), which would misleadingly suggest it doesn't exist yet."""
    docs = [{"key": "brd", "status": "Draft"}]
    p = build_pipeline(docs, _NO_TASKS, _GATE1_PASSED, service_docs_exist=False,
                        plan_mode="unified", scope="pilot", feature="payments")
    assert p["next_step_id"] == "brd"
    assert p["next_persona"] is None
    # the per-step badge/tooltip still names the general owner, though
    assert _step(p, "brd")["persona"]["name"] == "Maya"


def test_build_feature_status_includes_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path, '  scope: "pilot"\n')
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text("# Constitution\n")
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Draft\n")
    feat = build_feature_status(tmp_path, "payments", scope="pilot")
    assert "pipeline" in feat
    assert feat["pipeline"]["next_step_id"] == "brd"
    # brd.md exists and is awaiting review -- no creation-phrased ask (see
    # test_pipeline_awaiting_review_suppresses_the_creation_phrased_ask)
    assert feat["pipeline"]["next_persona"] is None
    # but current_stage agrees: BRD is the last known doc, awaiting approval
    assert feat["current_stage"]["next"] == "(awaiting approval)"
    assert feat["current_stage"]["persona"] is None


# ── Documents Card "Next" Hint (_current_stage) ──────────────────────────

def test_current_stage_fresh_project_hints_the_first_doc_owner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path, '  scope: "pilot"\n')
    feat = build_feature_status(tmp_path, "payments", scope="pilot")
    stage = feat["current_stage"]
    assert stage["next"] == "BRD"
    assert stage["persona"]["name"] == "Maya"
    assert "payments" in stage["persona"]["ask"]


def test_current_stage_next_upcoming_doc_carries_a_persona(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path, '  scope: "pilot"\n')
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Approved\n")
    feat = build_feature_status(tmp_path, "payments", scope="pilot")
    stage = feat["current_stage"]
    assert stage["next"] == "Use Cases"
    assert stage["persona"]["name"] == "Maya"
    assert "payments" in stage["persona"]["ask"]


def test_current_stage_awaiting_approval_has_no_persona(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path, '  scope: "pilot"\n')
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Draft\n")
    feat = build_feature_status(tmp_path, "payments", scope="pilot")
    stage = feat["current_stage"]
    assert stage["next"] == "(awaiting approval)"
    assert stage["persona"] is None


def test_current_stage_micro_scope_never_gets_a_persona_hint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)  # no scope line -- sdd-micro shape
    feat = build_feature_status(tmp_path, "payments", scope=None)
    assert feat["current_stage"]["persona"] is None


def test_persona_for_public_wrapper_matches_internal_lookup():
    assert persona_for("srd", "payments", "pilot") == {
        "name": "Rex", "role": "Requirements Engineer",
        "ask": "write the SRD for payments",
    }
    assert persona_for("srd", "payments", None) is None
    assert persona_for("specify", "payments", "pilot") is None
