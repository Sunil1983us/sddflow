from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml

INTEGRATIONS_PATH = ".specify/integrations.yml"

_DEFAULT_PAGE_MAP = {
    "brd":       "{project} — Business Requirements",
    "use-cases": "{project} — Use Cases",
    "srd":       "{project} — System Requirements",
    "design":    "{project} — Design",
    "arch":      "{project} — Architecture Overview",
    "hld":       "{project} — High-Level Design",
    "adr":       "{project} — Architecture Decisions",
    "lld":       "{project} — Low-Level Design",
    "runbook":   "{project} — Runbook",
}

_DEFAULT_PRIORITY_MAP = {
    "must-have":   "High",
    "should-have": "Medium",
    "could-have":  "Low",
    "wont-have":   "Lowest",
}


@dataclass
class JiraConfig:
    project_key: str
    issue_hierarchy: dict = field(default_factory=lambda: {
        "feature": "Feature",
        "story":   "Story",
        "task":    "Task",
    })
    parent_field: str = "parent"
    priority_map: dict = field(default_factory=lambda: dict(_DEFAULT_PRIORITY_MAP))
    labels: list = field(default_factory=lambda: ["sdd-generated"])
    fix_version: str | None = None
    custom_fields: dict = field(default_factory=dict)


@dataclass
class ConfluenceConfig:
    space_key: str
    parent_page_id: str | None = None
    page_map: dict = field(default_factory=lambda: dict(_DEFAULT_PAGE_MAP))


@dataclass
class DocumentReview:
    reviewer_jira_user: str   # Jira accountId (Cloud) or username (Server/DC)
    reviewer_role: str        # Human-readable label e.g. "Product Owner"
    phase: str                # specify | planning | tasks | release
    sequence: int             # 1-based order within the phase
    confluence_page: str      # page title template, supports {project}


@dataclass
class PrAutomation:
    enabled: bool = True
    branch_pattern: str = "feature/{task_id}-{slug}"
    pr_title_pattern: str = "feat({task_id}): {title}"


@dataclass
class CodeReviewConfig:
    enabled: bool = True
    pre_review: bool = True   # false = skip pre-review, go straight to human review


@dataclass
class IntegrationsConfig:
    profile: str | None
    jira: JiraConfig | None
    confluence: ConfluenceConfig | None
    document_reviews: dict[str, DocumentReview] = field(default_factory=dict)
    approved_statuses: list[str] = field(
        default_factory=lambda: ["Done", "Approved"]
    )
    approved_keywords: list[str] = field(
        default_factory=lambda: ["approved", "lgtm", "looks good", "go ahead", "confirmed"]
    )
    pr_automation: PrAutomation = field(default_factory=PrAutomation)
    code_review: CodeReviewConfig = field(default_factory=CodeReviewConfig)


def load_integrations(path: str = INTEGRATIONS_PATH) -> IntegrationsConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"{path} not found. Run 'sdd config init' or copy "
            ".specify/integrations.yml.example to .specify/integrations.yml"
        )
    raw = yaml.safe_load(p.read_text()) or {}

    jira: JiraConfig | None = None
    jira_raw = raw.get("jira")
    if jira_raw:
        hierarchy = jira_raw.get("issue_hierarchy", {})
        bf = jira_raw.get("base_fields", {})
        jira = JiraConfig(
            project_key=jira_raw["project_key"],
            issue_hierarchy={
                "feature": hierarchy.get("feature", "Feature"),
                "story":   hierarchy.get("story",   "Story"),
                "task":    hierarchy.get("task",     "Task"),
            },
            parent_field=jira_raw.get("parent_field", "parent"),
            priority_map=bf.get("priority_map", dict(_DEFAULT_PRIORITY_MAP)),
            labels=bf.get("labels", ["sdd-generated"]),
            fix_version=bf.get("fix_version"),
            custom_fields=jira_raw.get("custom_fields", {}),
        )

    confluence: ConfluenceConfig | None = None
    cf_raw = raw.get("confluence")
    if cf_raw:
        confluence = ConfluenceConfig(
            space_key=cf_raw["space_key"],
            parent_page_id=(
                str(cf_raw["parent_page_id"]) if cf_raw.get("parent_page_id") else None
            ),
            page_map=cf_raw.get("page_map", dict(_DEFAULT_PAGE_MAP)),
        )

    document_reviews: dict[str, DocumentReview] = {}
    for doc_key, dr_raw in (raw.get("document_reviews") or {}).items():
        document_reviews[doc_key] = DocumentReview(
            reviewer_jira_user=dr_raw.get("reviewer_jira_user", ""),
            reviewer_role=dr_raw.get("reviewer_role", ""),
            phase=dr_raw.get("phase", "specify"),
            sequence=int(dr_raw.get("sequence", 1)),
            confluence_page=dr_raw.get(
                "confluence_page",
                _DEFAULT_PAGE_MAP.get(doc_key, f"{{project}} — {doc_key.upper()}")
            ),
        )

    pr_raw = raw.get("pr_automation") or {}
    pr_automation = PrAutomation(
        enabled=pr_raw.get("enabled", True),
        branch_pattern=pr_raw.get("branch_pattern", "feature/{task_id}-{slug}"),
        pr_title_pattern=pr_raw.get("pr_title_pattern", "feat({task_id}): {title}"),
    )

    cr_raw = raw.get("code_review") or {}
    code_review = CodeReviewConfig(
        enabled=cr_raw.get("enabled", True),
        pre_review=cr_raw.get("pre_review", True),
    )

    return IntegrationsConfig(
        profile=raw.get("profile"),
        jira=jira,
        confluence=confluence,
        document_reviews=document_reviews,
        approved_statuses=raw.get("approved_statuses", ["Done", "Approved"]),
        approved_keywords=raw.get(
            "approved_keywords",
            ["approved", "lgtm", "looks good", "go ahead", "confirmed"]
        ),
        pr_automation=pr_automation,
        code_review=code_review,
    )
