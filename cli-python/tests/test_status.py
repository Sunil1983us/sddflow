# Unit tests for sdd/utils/status.py — the read-only snapshot that
# `sdd dashboard` and `sdd status` render. Pure filesystem reads, no
# network/Jira dependency (unlike `sdd review status`).
from pathlib import Path

from sdd.utils.status import build_project_status, build_feature_status


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
