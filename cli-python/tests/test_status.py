# Unit tests for sdd/utils/status.py — the read-only snapshot that
# `sdd dashboard` and `sdd status` render. Pure filesystem reads, no
# network/Jira dependency (unlike `sdd review status`).
from pathlib import Path

import sdd.utils.status as status_mod
from sdd.utils.status import (
    _doc_timing,
    _normalize_role_key,
    _parse_approvals_table,
    _parse_brd_bo,
    _parse_iso_date,
    _parse_release_bo_closure,
    _parse_srd_fr,
    _parse_uc_traces,
    _parse_version_history_table,
    _resolve_expected_approver,
    _service_level_docs,
    build_bo_rollup,
    build_feature_status,
    build_pipeline,
    build_project_status,
    persona_for,
)


def _write_manifest(root: Path, scope_line: str = "") -> None:
    (root / ".specify").mkdir(parents=True, exist_ok=True)
    (root / ".specify" / "manifest.yml").write_text(
        "project:\n"
        '  name: "Demo"\n'
        '  feature: "payments"\n'
        '  context_file: "payments.md"\n'
        + scope_line
        + 'project_type: "backend-service"\n'
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


def test_normalize_role_key_matches_roles_yml_convention():
    assert _normalize_role_key("Product Owner") == "product_owner"
    assert _normalize_role_key("QA Lead") == "qa_lead"
    assert _normalize_role_key("DevOps/SRE") == "devops_sre"
    assert _normalize_role_key("Tech Lead") == "tech_lead"


def test_normalize_role_key_strips_raci_annotation_from_real_template_shape():
    """Regression: every real template's Approvals table Role cell carries
    a RACI annotation in parentheses -- e.g. brd-template.md's actual text
    "Product Owner (accountable -- business objectives sign-off)" -- never
    just the bare role name the pre-fix tests exercised. Before this fix,
    normalizing that full string produced
    "product_owner_accountable_business_objectives_sign_off", which never
    matched any roles.yml key -- so a fully filled-in roles.yml still
    showed every role as unresolved on the dashboard."""
    assert (
        _normalize_role_key(
            "Product Owner (accountable — business objectives sign-off)"
        )
        == "product_owner"
    )
    assert (
        _normalize_role_key("Business Analyst (responsible — requirements accuracy)")
        == "business_analyst"
    )
    assert (
        _normalize_role_key("QA Lead (consulted — test case mapping confirmed, mvp+)")
        == "qa_lead"
    )
    assert (
        _normalize_role_key("DevOps/SRE (consulted — deployment readiness)")
        == "devops_sre"
    )
    assert _normalize_role_key("Architect (consulted, mvp+)") == "architect"


def test_resolve_expected_approver_looks_up_roles_map():
    roles_map = {"product_owner": "Jane Smith", "tech_lead": ""}
    assert _resolve_expected_approver("Product Owner", roles_map) == "Jane Smith"
    assert (
        _resolve_expected_approver("Tech Lead", roles_map) is None
    )  # blank in roles.yml
    assert _resolve_expected_approver("Unknown Role", roles_map) is None


def test_resolve_expected_approver_with_real_template_role_label(tmp_path):
    """Same regression as above, exercised through the public resolver
    with the exact Role cell text brd-template.md ships."""
    roles_map = {"product_owner": "Sunil PO"}
    assert (
        _resolve_expected_approver(
            "Product Owner (accountable — business objectives sign-off)", roles_map
        )
        == "Sunil PO"
    )


def test_parse_approvals_table_current_4column_format(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text(
        "# BRD\nStatus: Approved\n\n"
        "## Approvals\n\n"
        "| Role | Approver | Status | Date |\n"
        "|---|---|---|---|\n"
        "| Product Owner | Jane Smith | Approved | 2026-07-10 |\n\n"
        "## Version History\n"
    )
    rows = _parse_approvals_table(doc)
    assert rows == [
        {
            "role": "Product Owner",
            "approver": "Jane Smith",
            "status": "Approved",
            "date": "2026-07-10",
        }
    ]


def test_parse_approvals_table_legacy_3column_format(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text(
        "# BRD\nStatus: Approved\n\n"
        "## Approvals\n\n"
        "| Role | Status | Date |\n"
        "|---|---|---|\n"
        "| Product Owner | Approved | 2026-06-28 |\n"
    )
    rows = _parse_approvals_table(doc)
    assert rows == [
        {
            "role": "Product Owner",
            "approver": None,
            "status": "Approved",
            "date": "2026-06-28",
        }
    ]


def test_parse_approvals_table_skips_unfilled_placeholder_row(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text(
        "# BRD\nStatus: Draft\n\n"
        "## Approvals\n\n"
        "| Role | Approver | Status | Date |\n"
        "|---|---|---|---|\n"
        "| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |\n"
    )
    assert _parse_approvals_table(doc) == []


def test_parse_approvals_table_missing_section_returns_empty(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text("# BRD\nStatus: Draft\n")
    assert _parse_approvals_table(doc) == []


# --- Version History / stage timing (created/approved dates, duration,
# revision-round count) --------------------------------------------------


def test_parse_version_history_table_basic(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text(
        "# BRD\n\n## Version History\n\n"
        "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
        "|---|---|---|---|---|\n"
        "| 1.0 | 2026-01-01 | Jane | Initial draft | — |\n"
        "| 1.1 | 2026-01-03 | reviewer feedback | Clarified scope | — |\n"
        "| 1.1 | 2026-01-05 | Jane Smith | Approved | — |\n"
    )
    assert _parse_version_history_table(doc) == [
        {
            "version": "1.0",
            "date": "2026-01-01",
            "changed_by": "Jane",
            "summary": "Initial draft",
        },
        {
            "version": "1.1",
            "date": "2026-01-03",
            "changed_by": "reviewer feedback",
            "summary": "Clarified scope",
        },
        {
            "version": "1.1",
            "date": "2026-01-05",
            "changed_by": "Jane Smith",
            "summary": "Approved",
        },
    ]


def test_parse_version_history_table_missing_section_returns_empty(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text("# BRD\nStatus: Draft\n")
    assert _parse_version_history_table(doc) == []


def test_parse_version_history_table_skips_unfilled_placeholder(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text(
        "# BRD\n\n## Version History\n\n"
        "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
        "|---|---|---|---|---|\n"
        "| {version} | {date: YYYY-MM-DD} | {author} | Initial draft | — |\n"
    )
    assert _parse_version_history_table(doc) == []


def test_parse_iso_date_accepts_strict_format():
    parsed = _parse_iso_date("2026-01-01")
    assert parsed is not None
    assert parsed.isoformat() == "2026-01-01"


def test_parse_iso_date_rejects_free_text_missing_and_invalid():
    assert _parse_iso_date("January 1, 2026") is None
    assert _parse_iso_date("") is None
    assert _parse_iso_date(None) is None
    assert _parse_iso_date("2026-13-01") is None  # invalid month


def test_doc_timing_computes_duration_and_revision_rounds(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text(
        "# BRD\n> Version: 1.1 | Status: Approved | Date: 2026-01-05\n\n"
        "## Version History\n\n"
        "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
        "|---|---|---|---|---|\n"
        "| 1.0 | 2026-01-01 | Jane | Initial draft | — |\n"
        "| 1.1 | 2026-01-03 | reviewer feedback | Clarified scope | — |\n"
        "| 1.1 | 2026-01-05 | Jane Smith | Approved | — |\n"
    )
    assert _doc_timing(doc, "Approved", []) == {
        "created_date": "2026-01-01",
        "approved_date": "2026-01-05",
        "duration_days": 4,
        "revision_rounds": 1,
    }


def test_doc_timing_not_yet_approved_has_no_approved_date_or_duration(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text(
        "# BRD\n\n## Version History\n\n"
        "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
        "|---|---|---|---|---|\n"
        "| 1.0 | 2026-01-01 | Jane | Initial draft | — |\n"
    )
    timing = _doc_timing(doc, "Draft", [])
    assert timing["created_date"] == "2026-01-01"
    assert timing["approved_date"] is None
    assert timing["duration_days"] is None
    assert timing["revision_rounds"] == 0


def test_doc_timing_falls_back_to_approvals_table_when_no_version_history(tmp_path):
    doc = tmp_path / "release.md"
    doc.write_text("# Release\n> Version: 1.0 | Date: 2026-02-01\n")
    approvals = [
        {
            "role": "QA Lead",
            "approver": "Sam",
            "status": "Approved",
            "date": "2026-02-10",
        }
    ]
    timing = _doc_timing(doc, "Approved", approvals)
    assert timing["created_date"] is None
    assert timing["approved_date"] == "2026-02-10"
    assert timing["duration_days"] is None  # no created_date to diff against
    assert timing["revision_rounds"] is None  # no Version History table at all


def test_doc_timing_unparseable_dates_are_silently_none(tmp_path):
    doc = tmp_path / "brd.md"
    doc.write_text(
        "# BRD\n\n## Version History\n\n"
        "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
        "|---|---|---|---|---|\n"
        "| 1.0 | January 1, 2026 | Jane | Initial draft | — |\n"
    )
    timing = _doc_timing(doc, "Draft", [])
    assert timing["created_date"] is None
    assert timing["duration_days"] is None


def test_feature_timeline_start_is_earliest_created_date_no_release_yet(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\n> Version: 1.0 | Status: Approved | Date: 2026-01-01\n\n"
        "## Version History\n\n"
        "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
        "|---|---|---|---|---|\n"
        "| 1.0 | 2026-01-01 | Jane | Initial draft | — |\n"
        "| 1.0 | 2026-01-02 | Jane | Approved | — |\n"
    )
    (feature_dir / "srd.md").write_text(
        "# SRD\n> Version: 1.0 | Status: Draft | Date: 2026-01-05\n\n"
        "## Version History\n\n"
        "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
        "|---|---|---|---|---|\n"
        "| 1.0 | 2026-01-05 | Jane | Initial draft | — |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    assert feat["timeline"]["start_date"] == "2026-01-01"
    assert feat["timeline"]["end_date"] is None
    assert feat["timeline"]["duration_days"] is None


def test_feature_timeline_end_is_release_approved_date(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\n> Version: 1.0 | Status: Approved | Date: 2026-01-01\n\n"
        "## Version History\n\n"
        "| Version | Date | Changed By | Summary of Changes | CHG-NNN |\n"
        "|---|---|---|---|---|\n"
        "| 1.0 | 2026-01-01 | Jane | Initial draft | — |\n"
    )
    (feature_dir / "release.md").write_text(
        "# Release\n> Version: 1.0 | Status: Approved | Date: 2026-03-01\n\n"
        "## Approvals\n\n"
        "| Role | Approver | Status | Date |\n"
        "|---|---|---|---|\n"
        "| QA Lead | Sam | Approved | 2026-03-01 |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    assert feat["timeline"]["start_date"] == "2026-01-01"
    assert feat["timeline"]["end_date"] == "2026-03-01"
    assert feat["timeline"]["duration_days"] == 59


def test_feature_timeline_empty_when_no_dated_docs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("# BRD\n> Version: 1.0 | Status: Draft\n")
    feat = build_feature_status(tmp_path, "payments")
    assert feat["timeline"] == {
        "start_date": None,
        "end_date": None,
        "duration_days": None,
    }


def test_feature_docs_approvals_resolve_expected_approver_when_pending(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "roles.yml").write_text(
        'roles:\n  product_owner: Jane Smith\n  tech_lead: ""\n'
    )
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\nStatus: Draft\n\n"
        "## Approvals\n\n"
        "| Role | Approver | Status | Date |\n"
        "|---|---|---|---|\n"
        "| Product Owner | | Pending | |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    brd = next(d for d in feat["docs"] if d["key"] == "brd")
    assert brd["approvals"] == [
        {
            "role": "Product Owner",
            "approver": None,
            "status": "Pending",
            "date": None,
            "expected_approver": "Jane Smith",
        }
    ]


def test_feature_docs_approvals_resolve_expected_approver_with_real_brd_role_label(
    tmp_path, monkeypatch
):
    """End-to-end regression for the reported bug: a fully filled-in
    roles.yml still showed no expected approver, because the real BRD
    template's Role cell ("Product Owner (accountable -- business
    objectives sign-off)") carries a RACI annotation the old
    _normalize_role_key never stripped."""
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "roles.yml").write_text(
        "roles:\n"
        '  product_owner: "Sunil PO"\n'
        '  business_analyst: "Sunil Business Analyst"\n'
    )
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\nStatus: Draft\n\n"
        "## Approvals\n\n"
        "| Role | Approver | Status | Date |\n"
        "|---|---|---|---|\n"
        "| Product Owner (accountable — business objectives sign-off) | | Pending | |\n"
        "| Business Analyst (responsible — requirements accuracy) | | Pending | |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    brd = next(d for d in feat["docs"] if d["key"] == "brd")
    assert brd["approvals"][0]["expected_approver"] == "Sunil PO"
    assert brd["approvals"][1]["expected_approver"] == "Sunil Business Analyst"


def test_feature_docs_approvals_no_expected_approver_when_roles_yml_missing(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\nStatus: Draft\n\n"
        "## Approvals\n\n"
        "| Role | Approver | Status | Date |\n"
        "|---|---|---|---|\n"
        "| Product Owner | | Pending | |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    brd = next(d for d in feat["docs"] if d["key"] == "brd")
    assert brd["approvals"][0]["expected_approver"] is None


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


def test_tasks_full_pack_format_counts_perf_and_chg_headings(tmp_path, monkeypatch):
    """PERF-NNN (perf tasks from /task) and CHG-NNN (post-approval /change
    work appended to tasks.md) must count toward progress the same way
    TASK-NNN does -- previously _TASK_HEADING_RE only matched TASK-\\d+."""
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text(
        "### TASK-001 — Scaffold\n"
        "Acceptance criteria:\n"
        "  - [x] one\n"
        "### PERF-001 — Load test checkout\n"
        "Acceptance criteria:\n"
        "  - [x] one\n"
        "## Change Set: CR-001 — 2026-01-01\n"
        "### CHG-001 — Add retry to payment call\n"
        "Satisfies: FR-010\n"
        "Acceptance criteria:\n"
        "  - [ ] one\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    tasks = feat["tasks"]
    assert tasks["total"] == 3
    assert tasks["done"] == 2
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


def test_token_usage_source_mix_counts_real_vs_estimated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "token-usage.md").write_text(
        "## Running Totals\n\n"
        "| Metric | Value |\n"
        "|---|---|\n"
        "| Total Input Tokens | 300 |\n"
        "| Commands logged | 3 |\n\n"
        "## Per-Command Log\n\n"
        "| # | Command | Model | Input Tokens | Output Tokens | Cost (USD) | Source | Timestamp |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | specify | claude-sonnet-5 | 100 | 50 | $0.01 | Real (Claude Code) | 2026-07-08T10:00:00Z |\n"
        "| 2 | plan | claude-sonnet-5 | 100 | 50 | $0.01 | Real (Claude Code) | 2026-07-08T11:00:00Z |\n"
        "| 3 | task | gpt-4 | 100 | 50 | n/a | Estimated | 2026-07-08T12:00:00Z |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    tu = feat["token_usage"]
    assert tu["real_commands"] == 2
    assert tu["estimated_commands"] == 1


def test_token_usage_source_mix_legacy_rows_all_estimated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "token-usage.md").write_text(
        "## Running Totals\n\n"
        "| Metric | Value |\n"
        "|---|---|\n"
        "| Total Est. Input Tokens | 200 |\n\n"
        "## Per-Command Log\n\n"
        "| # | Command | Model | Input Tokens | Output Tokens | Cost (USD) | Timestamp |\n"
        "|---|---|---|---|---|---|---|\n"
        "| 1 | specify | claude-sonnet-5 | 100 | 50 | n/a | 2026-07-08T10:00:00Z |\n"
        "| 2 | plan | claude-sonnet-5 | 100 | 50 | n/a | 2026-07-08T11:00:00Z |\n"
    )
    feat = build_feature_status(tmp_path, "payments")
    tu = feat["token_usage"]
    assert tu["real_commands"] == 0
    assert tu["estimated_commands"] == 2


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
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n"
    )
    status = build_project_status(".")
    assert status["constitution"]["exists"] is True
    assert status["constitution"]["gate1_inferred"] == "pending_or_unknown"


def test_constitution_gate1_passed_when_downstream_doc_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n"
    )
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "brd.md").write_text("> Status: Draft\n")
    status = build_project_status(".")
    assert status["constitution"]["gate1_inferred"] == "passed"


def test_constitution_gate1_pending_when_only_token_usage_file_exists(
    tmp_path, monkeypatch
):
    """Regression: token-usage.md is appended to by every command including
    /specify itself (and even /create-context) whenever token-pricing.yml
    is configured -- both run before GATE-1 can possibly pass. Its mere
    presence in the feature directory must not be mistaken for a real
    downstream spec doc and flip GATE-1 to "passed" before the user has
    reviewed anything."""
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n"
    )
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "token-usage.md").write_text("## Running Totals\n")
    status = build_project_status(".")
    assert status["constitution"]["gate1_inferred"] == "pending_or_unknown"


def test_constitution_gate1_passed_when_downstream_doc_exists_alongside_token_usage(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n"
    )
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True)
    (feature_dir / "token-usage.md").write_text("## Running Totals\n")
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
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n"
    )
    feature_dir = tmp_path / ".specify" / "features" / "greeter"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text(
        "## TASK-001 — x\n- **Status:** Not Started\n"
    )
    status = build_project_status(".")
    assert status["constitution"]["gate1_inferred"] == "passed"


def test_constitution_missing_reports_not_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    status = build_project_status(".")
    assert status["constitution"]["exists"] is False


def test_constitution_freshly_scaffolded_template_is_not_part2_generated(
    tmp_path, monkeypatch
):
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
    monkeypatch.setattr(
        status_mod, "_local_base_url", lambda: "https://acme.atlassian.net"
    )
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
    assert jira["epic"] == {
        "key": "PROJ-1",
        "url": "https://acme.atlassian.net/browse/PROJ-1",
    }
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
    monkeypatch.setattr(
        status_mod, "_local_base_url", lambda: "https://acme.atlassian.net"
    )
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
    assert jira["epic"] == {
        "key": "PROJ-1",
        "url": "https://acme.atlassian.net/browse/PROJ-1",
    }
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
    monkeypatch.setattr(
        status_mod, "_local_base_url", lambda: "https://acme.atlassian.net"
    )
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)

    _save_keys_summary(
        "payments",
        "PROJ-1",
        {"STORY-001": "PROJ-2", "STORY-002": "PROJ-3"},
        {"TASK-001": "PROJ-4"},
        None,
        {},
    )

    feat = build_feature_status(tmp_path, "payments")
    jira = feat["local_links"]["jira"]
    assert jira["epic"] == {
        "key": "PROJ-1",
        "url": "https://acme.atlassian.net/browse/PROJ-1",
    }
    assert sorted(s["key"] for s in jira["stories"]) == ["PROJ-2", "PROJ-3"]
    assert jira["tasks"][0]["key"] == "PROJ-4"


def test_jira_keys_scoped_to_own_feature(tmp_path, monkeypatch):
    """A different feature's keys.yml must never leak into this feature's links."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        status_mod, "_local_base_url", lambda: "https://acme.atlassian.net"
    )
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
    monkeypatch.setattr(
        status_mod, "_local_base_url", lambda: "https://acme.atlassian.net"
    )
    _write_manifest(tmp_path)
    (tmp_path / ".specify" / "features" / "payments").mkdir(parents=True)
    (tmp_path / ".specify" / ".confluence-drafts.json").write_text(
        '{"brd": {"page_id": "123", "title": "Acme \\u2014 BRD"}}'
    )
    feat = build_feature_status(tmp_path, "payments")
    cf = feat["local_links"]["confluence"]
    assert (
        cf["brd"]["url"]
        == "https://acme.atlassian.net/wiki/pages/viewpage.action?pageId=123"
    )
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
    monkeypatch.setattr(
        status_mod, "_local_base_url", lambda: "https://acme.atlassian.net"
    )
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
    monkeypatch.setattr(
        status_mod, "_local_base_url", lambda: "https://acme.atlassian.net"
    )
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
        'brd:\n  approved_by: "Jane"\n  approved_at: "2026-07-09"\n  note: "lgtm"\n'
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
    assert [c["text"] for c in dashboard["docs"][0]["comments"]] == [
        "different feature"
    ]


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
_NO_SERVICE_DOCS = {}
_SERVICE_DOCS_ALL_APPROVED = {
    "data-model": {"exists": True, "status": "Approved"},
    "security-design": {"exists": True, "status": "Approved"},
}
# security-design is required at every scope (never skipped, unlike
# data-model) -- tests that exercise steps *after* it in pipeline order
# need it approved, or it (correctly) blocks next_action first.
_SECURITY_APPROVED = {"security-design": {"exists": True, "status": "Approved"}}


def _step(pipeline, step_id):
    return next(s for s in pipeline["steps"] if s["id"] == step_id)


def test_pipeline_fresh_project_starts_at_specify():
    p = build_pipeline(
        [],
        _NO_TASKS,
        _NOT_STARTED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
    )
    assert _step(p, "specify")["state"] == "upcoming"
    assert p["next_step_id"] == "specify"
    assert "/specify" in p["next_action"]


def test_pipeline_awaiting_gate1_after_constitution_exists():
    p = build_pipeline(
        [],
        _NO_TASKS,
        {
            "exists": True,
            "part2_generated": True,
            "gate1_inferred": "pending_or_unknown",
        },
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
    )
    assert _step(p, "specify")["state"] == "done"
    assert _step(p, "gate1")["state"] == "current"
    assert p["next_step_id"] == "gate1"
    assert "finalized" in p["next_action"]


def test_pipeline_constitution_file_scaffolded_but_specify_not_run_yet_is_upcoming():
    """Regression: constitution.md is scaffolded by `sdd init` for every
    project (Part 1 boilerplate + a Part 2 template full of placeholders) --
    the file existing on disk must NOT make the 'Constitution (Part 2)' step
    show done before /specify has actually filled it in."""
    p = build_pipeline(
        [],
        _NO_TASKS,
        {"exists": True, "part2_generated": False, "gate1_inferred": "unknown"},
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
    )
    assert _step(p, "specify")["state"] == "upcoming"
    assert _step(p, "gate1")["state"] == "upcoming"
    assert p["next_step_id"] == "specify"


def test_pipeline_doc_awaiting_review_is_current_not_done():
    docs = [{"key": "brd", "status": "Draft"}]
    p = build_pipeline(
        docs,
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
    )
    assert _step(p, "brd")["state"] == "current"
    assert p["next_step_id"] == "brd"
    assert "sdd review check --doc brd" in p["next_action"]


def test_pipeline_approved_doc_counts_as_done():
    docs = [{"key": "brd", "status": "Approved"}]
    p = build_pipeline(
        docs,
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
    )
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
    p = build_pipeline(
        docs,
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_SECURITY_APPROVED,
        plan_mode="unified",
        scope="pilot",
    )
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
    p = build_pipeline(
        docs,
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_SECURITY_APPROVED,
        plan_mode="unified",
        scope="pilot",
    )
    assert p["next_step_id"] == "checklist"
    assert "/checklist" in p["next_action"]


def test_pipeline_pilot_scope_skips_lld_adr_runbook_qa():
    """data-model/security-design are no longer per-feature pipeline
    steps at all (see _service_level_docs()'s dedicated scope-gating
    tests below) -- this only covers the genuinely per-feature steps."""
    p = build_pipeline(
        [],
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
    )
    for step_id in ("lld", "runbook", "qa-testcases"):
        step = _step(p, step_id)
        assert step["state"] == "skipped", step_id
        assert step["skip"]
    # pilot uses smoke-tests instead of qa-testcases
    assert _step(p, "smoke-tests")["skip"] is None
    assert "data-model" not in {s["id"] for s in p["steps"]}
    assert "security-design" not in {s["id"] for s in p["steps"]}


def test_pipeline_mvp_scope_includes_lld_adr_runbook_qa_skips_smoke_tests():
    p = build_pipeline(
        [],
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="separate",
        scope="mvp",
    )
    for step_id in ("lld", "runbook", "qa-testcases", "adr"):
        assert _step(p, step_id)["skip"] is None, step_id
    assert _step(p, "smoke-tests")["skip"]


def test_service_level_docs_security_design_required_even_at_pilot_scope(
    tmp_path, monkeypatch
):
    """Regression: security-design.md (living, .specify/service/) is
    required at every scope per CLAUDE.md's Scope Reference table --
    pilot gets §1 (Threat Assessment) only, but the document itself is
    never skipped the way data-model is."""
    monkeypatch.chdir(tmp_path)
    docs = _service_level_docs(tmp_path, "payments", "pilot")
    by_key = {d["key"]: d for d in docs}
    assert by_key["security-design"]["skip"] is None
    assert by_key["data-model"]["skip"]


def test_pipeline_resilience_investigation_require_full_scope():
    for scope in ("pilot", "mvp"):
        p = build_pipeline(
            [],
            _NO_TASKS,
            _GATE1_PASSED,
            service_docs=_NO_SERVICE_DOCS,
            plan_mode="unified",
            scope=scope,
        )
        assert _step(p, "resilience")["skip"], scope
        assert _step(p, "investigation")["skip"], scope
    p = build_pipeline(
        [],
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="full",
    )
    assert _step(p, "resilience")["skip"] is None
    assert _step(p, "investigation")["skip"] is None


def test_pipeline_type_specific_extended_docs_omitted_when_not_applicable():
    """component-spec/ux-flow/screen-spec shouldn't even appear as steps
    for a project type that doesn't use them (e.g. backend-service) --
    not shown as a permanent 'not applicable' row, just absent."""
    p = build_pipeline(
        [],
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="mvp",
    )
    ids = {s["id"] for s in p["steps"]}
    assert "component-spec" not in ids
    assert "ux-flow" not in ids
    assert "screen-spec" not in ids


def test_pipeline_type_specific_extended_docs_included_when_applicable():
    p = build_pipeline(
        [],
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="mvp",
        applicable_extended=frozenset({"component-spec", "ux-flow"}),
    )
    assert _step(p, "component-spec")["skip"] is None
    assert _step(p, "ux-flow")["skip"] is None
    assert "screen-spec" not in {s["id"] for s in p["steps"]}


def test_service_level_docs_track_independently(tmp_path, monkeypatch):
    """generating only security-design.md must not make data-model.md
    look done too (and vice versa) -- each living doc's state must come
    from its own file, not a folder-wide existence check."""
    monkeypatch.chdir(tmp_path)
    service_dir = tmp_path / ".specify" / "service"
    service_dir.mkdir(parents=True)
    (service_dir / "security-design.md").write_text(
        "# Security Design\nStatus: Approved\n"
    )
    docs = _service_level_docs(tmp_path, "payments", "mvp")
    by_key = {d["key"]: d for d in docs}
    assert by_key["security-design"]["exists"] is True
    assert by_key["security-design"]["status"] == "Approved"
    assert by_key["data-model"]["exists"] is False
    assert by_key["data-model"]["status"] is None


def test_service_level_docs_awaiting_review_status_is_not_approved(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    service_dir = tmp_path / ".specify" / "service"
    service_dir.mkdir(parents=True)
    (service_dir / "data-model.md").write_text("# Data Model\nStatus: Draft\n")
    docs = _service_level_docs(tmp_path, "payments", "mvp")
    by_key = {d["key"]: d for d in docs}
    assert by_key["data-model"]["exists"] is True
    assert by_key["data-model"]["status"] == "Draft"


def test_pipeline_unified_plan_mode_skips_arch_hld_adr_uses_design():
    p = build_pipeline(
        [],
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="mvp",
    )
    assert _step(p, "design")["skip"] is None
    for step_id in ("arch", "hld", "adr"):
        assert _step(p, step_id)["skip"], step_id


def test_pipeline_separate_plan_mode_skips_design_uses_arch_hld_adr():
    p = build_pipeline(
        [],
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="separate",
        scope="mvp",
    )
    assert _step(p, "design")["skip"]
    for step_id in ("arch", "hld", "adr"):
        assert _step(p, step_id)["skip"] is None, step_id


def test_pipeline_implement_reflects_task_progress():
    approved = {"status": "Approved"}
    docs = [
        {"key": k, **approved}
        for k in (
            "brd",
            "use-cases",
            "srd",
            "checklist",
            "validate",
            "analyze",
            "clarify",
            "design",
            "stories",
            "tasks",
            "smoke-tests",
        )
    ]
    p = build_pipeline(
        docs,
        {"total": 4, "done": 2},
        _GATE1_PASSED,
        service_docs=_SECURITY_APPROVED,
        plan_mode="unified",
        scope="pilot",
    )
    assert _step(p, "implement")["state"] == "current"
    assert "2/4" in p["next_action"]


def test_pipeline_all_done_reports_complete():
    approved = {"status": "Approved"}
    docs = [
        {"key": k, **approved}
        for k in (
            "brd",
            "use-cases",
            "srd",
            "checklist",
            "validate",
            "analyze",
            "clarify",
            "design",
            "stories",
            "tasks",
            "smoke-tests",
            "release",
        )
    ]
    tasks = {"total": 2, "done": 2}
    p = build_pipeline(
        docs,
        tasks,
        _GATE1_PASSED,
        service_docs=_SERVICE_DOCS_ALL_APPROVED,
        plan_mode="unified",
        scope="pilot",
    )
    assert p["next_step_id"] is None
    assert "complete" in p["next_action"]


def test_pipeline_micro_scope_none_uses_3_command_flow():
    p = build_pipeline(
        [],
        _NO_TASKS,
        _NOT_STARTED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope=None,
    )
    assert [s["id"] for s in p["steps"]] == ["specify", "gate1", "task", "implement"]


# ── Persona Hints (Virtual Team) ─────────────────────────────────────────


def test_pipeline_next_persona_names_the_owning_team_member():
    docs = [{"key": "brd", "status": "Approved"}]
    p = build_pipeline(
        docs,
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
        feature="payments",
    )
    assert p["next_step_id"] == "use-cases"
    assert p["next_persona"]["name"] == "Maya"
    assert p["next_persona"]["role"] == "Business Analyst"
    assert "payments" in p["next_persona"]["ask"]


def test_step_persona_present_on_every_resolved_step_with_an_owner():
    p = build_pipeline(
        [],
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
        feature="payments",
    )
    assert _step(p, "srd")["persona"]["name"] == "Rex"
    assert _step(p, "design")["persona"]["name"] == "Ava"
    assert _step(p, "release")["persona"]["name"] == "Riley"


def test_specify_and_gate1_have_no_persona_owner():
    """Run before any Virtual Team member takes over -- see _STEP_PERSONA's
    docstring in status.py."""
    p = build_pipeline(
        [],
        _NO_TASKS,
        _NOT_STARTED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
    )
    assert _step(p, "specify")["persona"] is None
    assert _step(p, "gate1")["persona"] is None


def test_micro_scope_never_gets_a_persona_hint():
    """sdd-micro has no Virtual Team at all (see its own CLAUDE.md)."""
    p = build_pipeline(
        [],
        _NO_TASKS,
        _NOT_STARTED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope=None,
    )
    for step in p["steps"]:
        assert step["persona"] is None
    assert p["next_persona"] is None


def test_pipeline_awaiting_review_suppresses_the_creation_phrased_ask():
    """A doc that already exists and is awaiting review isn't waiting to be
    *created* -- the ask templates are all creation-phrased ('create the
    BRD'), which would misleadingly suggest it doesn't exist yet."""
    docs = [{"key": "brd", "status": "Draft"}]
    p = build_pipeline(
        docs,
        _NO_TASKS,
        _GATE1_PASSED,
        service_docs=_NO_SERVICE_DOCS,
        plan_mode="unified",
        scope="pilot",
        feature="payments",
    )
    assert p["next_step_id"] == "brd"
    assert p["next_persona"] is None
    # the per-step badge/tooltip still names the general owner, though
    assert _step(p, "brd")["persona"]["name"] == "Maya"


def test_build_feature_status_includes_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status_mod, "_local_base_url", lambda: None)
    _write_manifest(tmp_path, '  scope: "pilot"\n')
    (tmp_path / ".specify" / "memory").mkdir(parents=True)
    (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n"
    )
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
        "name": "Rex",
        "role": "Requirements Engineer",
        "ask": "write the SRD for payments",
    }
    assert persona_for("srd", "payments", None) is None


# ── BO → BR → FR → TASK Rollup (build_bo_rollup) ─────────────────────────
# Chains brd.md §2 Business Objectives -> §5 "Serves BO" -> srd.md
# Functional Requirements "Source"/"Satisfies" column -> tasks.md
# "Satisfies:" field + completion status. use-cases.md/srd.md UC Trace
# columns are display-only (which UCs implement a BO), not part of the
# completion count.


def _write_brd_bo(feature_dir: Path, four_col_objectives: bool = False) -> None:
    if four_col_objectives:
        obj_table = (
            "| ID | Objective | Metric | Target |\n"
            "|---|---|---|---|\n"
            "| BO-001 | Increase conversion | Conversion rate | +5% |\n"
        )
    else:
        obj_table = (
            "| ID | Objective | Success Metric |\n"
            "|---|---|---|\n"
            "| BO-001 | Increase conversion | Conversion rate +5% |\n"
        )
    (feature_dir / "brd.md").write_text(
        "# BRD\n"
        "## 2. Business Objectives\n"
        f"{obj_table}\n"
        "## 5. Business Requirements\n"
        "| ID | Requirement | Priority | Serves BO |\n"
        "|---|---|---|---|\n"
        "| BR-001 | Allow signup | Must Have | BO-001 |\n"
        "| BR-002 | Allow checkout | Must Have | BO-001 |\n"
    )


def test_parse_brd_bo_canonical_3_column_objectives(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_brd_bo(feature_dir)
    result = _parse_brd_bo(feature_dir / "brd.md")
    assert result["objectives"]["BO-001"]["objective"] == "Increase conversion"
    assert result["br_to_bo"]["BR-001"] == ["BO-001"]
    assert result["br_to_bo"]["BR-002"] == ["BO-001"]


def test_parse_brd_bo_tolerates_4_column_objectives_table(tmp_path):
    """Real generated docs sometimes split Success Metric into Metric +
    Target (4 cells instead of the template's 3) -- must not come back
    empty just because of that."""
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_brd_bo(feature_dir, four_col_objectives=True)
    result = _parse_brd_bo(feature_dir / "brd.md")
    assert "BO-001" in result["objectives"]
    assert "Conversion rate" in result["objectives"]["BO-001"]["metric"]
    assert "+5%" in result["objectives"]["BO-001"]["metric"]


def test_parse_brd_bo_tolerates_legacy_satisfies_header(tmp_path):
    """Some existing docs header the BR->BO column 'Satisfies' (with
    free-text annotations) instead of the newer 'Serves BO' -- the BO-NNN
    token must still be extracted regardless of header wording."""
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\n"
        "## 2. Business Objectives\n"
        "| ID | Objective | Success Metric |\n"
        "|---|---|---|\n"
        "| BO-001 | Increase conversion | +5% |\n\n"
        "## 5. Business Requirements\n"
        "| ID | Requirement | Priority | Satisfies |\n"
        "|---|---|---|---|\n"
        "| BR-001 | Allow signup | Must Have | BO-001 (trust/compliance) |\n"
    )
    result = _parse_brd_bo(feature_dir / "brd.md")
    assert result["br_to_bo"]["BR-001"] == ["BO-001"]


def test_parse_brd_bo_ignores_unfilled_template_placeholders(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\n"
        "## 2. Business Objectives\n"
        "| ID | Objective | Success Metric |\n"
        "|---|---|---|\n"
        "| BO-{NNN} | {objective} | {metric} |\n"
    )
    result = _parse_brd_bo(feature_dir / "brd.md")
    assert result["objectives"] == {}


def test_parse_brd_bo_missing_file_returns_empty(tmp_path):
    result = _parse_brd_bo(tmp_path / "nonexistent" / "brd.md")
    assert result == {"objectives": {}, "br_to_bo": {}}


def test_parse_uc_traces_from_index_table(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "use-cases.md").write_text(
        "## §2 Use Case Index\n"
        "| UC-ID | Title | Actor(s) | Priority | BR Traces | FR Traces (SRD) |\n"
        "|---|---|---|---|---|---|\n"
        "| UC-001 | Sign up | ACT-001 | High | BR-001 | FR-001 |\n"
    )
    result = _parse_uc_traces(feature_dir / "use-cases.md")
    assert result["UC-001"] == {"br_ids": ["BR-001"], "fr_ids": ["FR-001"]}


def test_parse_uc_traces_falls_back_to_narrative_sections(tmp_path):
    """Real docs sometimes never had a '## Use Case Index' table at all
    (older generations) -- falls back to scanning each '### UC-NNN'
    section's '**Trace:**' line."""
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "use-cases.md").write_text(
        "## 2. Use Cases\n"
        "### UC-001 — Create Task\n"
        "**Actor:** ACT-001\n"
        "**Trace:** BR-001, BR-002\n"
        "### UC-002 — List Tasks\n"
        "**Actor:** ACT-001\n"
        "**Trace:** BR-002\n"
    )
    result = _parse_uc_traces(feature_dir / "use-cases.md")
    assert result["UC-001"]["br_ids"] == ["BR-001", "BR-002"]
    assert result["UC-002"]["br_ids"] == ["BR-002"]
    assert result["UC-001"]["fr_ids"] == []


def test_parse_uc_traces_missing_file_returns_empty(tmp_path):
    assert _parse_uc_traces(tmp_path / "nonexistent" / "use-cases.md") == {}


def test_parse_srd_fr_canonical_5_column(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "srd.md").write_text(
        "## 2. Functional Requirements\n"
        "| ID | Requirement | UC Trace | Source | Priority |\n"
        "|---|---|---|---|---|\n"
        "| FR-001 | Create task | UC-001 | BR-001 | Must Have |\n"
    )
    result = _parse_srd_fr(feature_dir / "srd.md")
    assert result["FR-001"] == {"br_ids": ["BR-001"], "uc_ids": ["UC-001"]}


def test_parse_srd_fr_tolerates_4_column_satisfies_variant(tmp_path):
    """Some existing docs skip the UC Trace column entirely (ID |
    Requirement | Priority | Satisfies)."""
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "srd.md").write_text(
        "## Functional Requirements\n"
        "| ID | Requirement | Priority | Satisfies |\n"
        "|---|---|---|---|\n"
        "| FR-001 | Create task | HIGH | BR-001, BR-002 |\n"
    )
    result = _parse_srd_fr(feature_dir / "srd.md")
    assert result["FR-001"]["br_ids"] == ["BR-001", "BR-002"]
    assert result["FR-001"]["uc_ids"] == []


def test_parse_srd_fr_use_case_coverage_supplements_uc_ids(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "srd.md").write_text(
        "## Functional Requirements\n"
        "| ID | Requirement | Priority | Satisfies |\n"
        "|---|---|---|---|\n"
        "| FR-001 | Create task | HIGH | BR-001 |\n\n"
        "## 4. Use Case Coverage\n"
        "| FR-NNN | UC Trace | Coverage Confirmed? |\n"
        "|---|---|---|\n"
        "| FR-001 | UC-001 | [x] |\n"
    )
    result = _parse_srd_fr(feature_dir / "srd.md")
    assert result["FR-001"]["uc_ids"] == ["UC-001"]


def _write_full_chain(root: Path, feature: str, task_status_line: str) -> Path:
    feature_dir = root / ".specify" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_brd_bo(feature_dir)
    (feature_dir / "use-cases.md").write_text(
        "## §2 Use Case Index\n"
        "| UC-ID | Title | Actor(s) | Priority | BR Traces | FR Traces (SRD) |\n"
        "|---|---|---|---|---|---|\n"
        "| UC-001 | Sign up | ACT-001 | High | BR-001 | |\n"
    )
    (feature_dir / "srd.md").write_text(
        "## 2. Functional Requirements\n"
        "| ID | Requirement | UC Trace | Source | Priority |\n"
        "|---|---|---|---|---|\n"
        "| FR-001 | Create account | UC-001 | BR-001 | Must Have |\n"
    )
    (feature_dir / "tasks.md").write_text(
        "### TASK-001 — Build signup\n"
        "**Satisfies:** FR-001\n"
        f"{task_status_line}\n"
        "  - [x] done marker\n"
    )
    return feature_dir


def test_build_bo_rollup_full_chain_done(tmp_path):
    _write_full_chain(tmp_path, "payments", "")
    rollup = build_bo_rollup(tmp_path, "payments")
    assert len(rollup) == 1
    bo = rollup[0]
    assert bo["bo_id"] == "BO-001"
    assert bo["uc_ids"] == ["UC-001"]
    assert bo["task_count"] == 1
    assert bo["tasks_done"] == 1
    assert bo["percent_done"] == 100
    assert bo["status"] == "Done"


def test_build_bo_rollup_not_started_when_task_incomplete(tmp_path):
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_brd_bo(feature_dir)
    (feature_dir / "srd.md").write_text(
        "## 2. Functional Requirements\n"
        "| ID | Requirement | UC Trace | Source | Priority |\n"
        "|---|---|---|---|---|\n"
        "| FR-001 | Create account | UC-001 | BR-001 | Must Have |\n"
    )
    (feature_dir / "tasks.md").write_text(
        "### TASK-001 — Build signup\n**Satisfies:** FR-001\n  - [ ] not done yet\n"
    )
    rollup = build_bo_rollup(tmp_path, "payments")
    assert rollup[0]["tasks_done"] == 0
    assert rollup[0]["status"] == "Not Started"


def test_build_bo_rollup_empty_when_no_brd(tmp_path):
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True, exist_ok=True)
    assert build_bo_rollup(tmp_path, "payments") == []


def test_build_bo_rollup_orphaned_br_not_served_by_any_bo_contributes_nothing(tmp_path):
    """A BR-NNN whose 'Serves BO' cell is blank (or cites a BO not in §2)
    must not silently attach its tasks to some other objective."""
    feature_dir = tmp_path / ".specify" / "features" / "payments"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "brd.md").write_text(
        "# BRD\n"
        "## 2. Business Objectives\n"
        "| ID | Objective | Success Metric |\n"
        "|---|---|---|\n"
        "| BO-001 | Increase conversion | +5% |\n\n"
        "## 5. Business Requirements\n"
        "| ID | Requirement | Priority | Serves BO |\n"
        "|---|---|---|---|\n"
        "| BR-001 | Orphan requirement | Must Have | |\n"
    )
    (feature_dir / "srd.md").write_text(
        "## 2. Functional Requirements\n"
        "| ID | Requirement | UC Trace | Source | Priority |\n"
        "|---|---|---|---|---|\n"
        "| FR-001 | Orphan FR | | BR-001 | Must Have |\n"
    )
    (feature_dir / "tasks.md").write_text(
        "### TASK-001 — Orphan task\n**Satisfies:** FR-001\n  - [x] done\n"
    )
    rollup = build_bo_rollup(tmp_path, "payments")
    assert rollup[0]["task_count"] == 0
    assert rollup[0]["status"] == "Not Started"


def test_parse_release_bo_closure_reads_checked_yes(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "release.md").write_text(
        "## 6. Business Objective Closure\n"
        "| BO-NNN | Success Metric (from BRD) | Measured Result | Met? |\n"
        "|---|---|---|---|\n"
        "| BO-001 | Conversion +5% | Measured +6% | [x] Yes  [ ] No  [ ] Pending |\n"
    )
    result = _parse_release_bo_closure(feature_dir / "release.md")
    assert result["BO-001"] == {"outcome": "met", "measured_result": "Measured +6%"}


def test_parse_release_bo_closure_reads_checked_no(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "release.md").write_text(
        "## 6. Business Objective Closure\n"
        "| BO-NNN | Success Metric (from BRD) | Measured Result | Met? |\n"
        "|---|---|---|---|\n"
        "| BO-001 | Conversion +5% | Measured +1% | [ ] Yes  [x] No  [ ] Pending |\n"
    )
    result = _parse_release_bo_closure(feature_dir / "release.md")
    assert result["BO-001"]["outcome"] == "not_met"


def test_parse_release_bo_closure_reads_checked_pending(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "release.md").write_text(
        "## 6. Business Objective Closure\n"
        "| BO-NNN | Success Metric (from BRD) | Measured Result | Met? |\n"
        "|---|---|---|---|\n"
        "| BO-001 | Conversion +5% | measure after 30 days | [ ] Yes  [ ] No  [X] Pending |\n"
    )
    result = _parse_release_bo_closure(feature_dir / "release.md")
    assert result["BO-001"]["outcome"] == "pending"


def test_parse_release_bo_closure_unfilled_checkbox_is_none(tmp_path):
    feature_dir = tmp_path
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "release.md").write_text(
        "## 6. Business Objective Closure\n"
        "| BO-NNN | Success Metric (from BRD) | Measured Result | Met? |\n"
        "|---|---|---|---|\n"
        "| BO-{NNN} | {metric} | {result} | [ ] Yes  [ ] No  [ ] Pending |\n"
    )
    result = _parse_release_bo_closure(feature_dir / "release.md")
    assert result == {}


def test_parse_release_bo_closure_missing_file_returns_empty(tmp_path):
    assert _parse_release_bo_closure(tmp_path / "nonexistent" / "release.md") == {}


def test_build_bo_rollup_wires_release_outcome(tmp_path):
    feature_dir = _write_full_chain(tmp_path, "payments", "")
    (feature_dir / "release.md").write_text(
        "## 6. Business Objective Closure\n"
        "| BO-NNN | Success Metric (from BRD) | Measured Result | Met? |\n"
        "|---|---|---|---|\n"
        "| BO-001 | Conversion +5% | Measured +6% | [x] Yes  [ ] No  [ ] Pending |\n"
    )
    rollup = build_bo_rollup(tmp_path, "payments")
    assert rollup[0]["outcome"] == "met"
    assert rollup[0]["measured_result"] == "Measured +6%"
    # task-completion-derived status is untouched by release outcome
    assert rollup[0]["status"] == "Done"


def test_build_bo_rollup_outcome_none_when_no_release_yet(tmp_path):
    _write_full_chain(tmp_path, "payments", "")
    rollup = build_bo_rollup(tmp_path, "payments")
    assert rollup[0]["outcome"] is None
    assert rollup[0]["measured_result"] is None


def test_build_project_status_flattens_bo_rollup_with_feature_tag(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path)
    _write_full_chain(tmp_path, "payments", "")
    status = build_project_status(".")
    assert len(status["business_objectives"]) == 1
    assert status["business_objectives"][0]["feature"] == "payments"
    assert status["business_objectives"][0]["bo_id"] == "BO-001"
    assert persona_for("specify", "payments", "pilot") is None


class TestLivingDocumentsProjectLevel:
    """Regression coverage for a user-reported dashboard gap: Data Model
    (living/service-level, one file for the whole project) wasn't visible
    on the dashboard at all -- it only ever showed as a bare progress dot
    buried inside a per-feature pipeline card, with no Approve button,
    no Confluence/Jira links, and (on a multi-feature project) duplicated
    once per feature card even though there's only one underlying file."""

    def test_living_documents_appear_at_project_level(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path, '  scope: "mvp"\n')
        service_dir = tmp_path / ".specify" / "service"
        service_dir.mkdir(parents=True)
        (service_dir / "data-model.md").write_text("# Data Model\nStatus: Draft\n")
        status = build_project_status(".")
        keys = {d["key"] for d in status["living_documents"]}
        assert keys == {"data-model", "security-design"}
        data_model = next(
            d for d in status["living_documents"] if d["key"] == "data-model"
        )
        assert data_model["exists"] is True
        assert data_model["status"] == "Draft"
        assert "living_local_links" in status

    def test_living_documents_not_duplicated_across_multiple_features(
        self, tmp_path, monkeypatch
    ):
        """The exact bug: a shared, project-wide doc must not show up as
        a separate per-feature pipeline step on each feature's card."""
        monkeypatch.chdir(tmp_path)
        _write_manifest(tmp_path, '  scope: "mvp"\n')
        for f in ["payments", "checkout"]:
            (tmp_path / ".specify" / "features" / f).mkdir(parents=True)
        service_dir = tmp_path / ".specify" / "service"
        service_dir.mkdir(parents=True)
        (service_dir / "data-model.md").write_text("# Data Model\nStatus: Draft\n")
        status = build_project_status(".")
        assert len(status["living_documents"]) == 2  # data-model + security-design once
        for feature in status["features"]:
            step_ids = {s["id"] for s in feature["pipeline"]["steps"]}
            assert "data-model" not in step_ids
            assert "security-design" not in step_ids

    def test_micro_style_project_has_no_living_documents(self, tmp_path, monkeypatch):
        """sdd-micro has no scope field at all (scope is None) -- must not
        crash and must report an empty list, not the backend-service
        default pair."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify").mkdir(parents=True)
        (tmp_path / ".specify" / "manifest.yml").write_text(
            'project:\n  name: "Demo"\n  feature: "greeter"\n'
        )
        status = build_project_status(".")
        assert status["living_documents"] == []
