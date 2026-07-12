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
    # Optional per-level overrides -- e.g. {"story": "SUNT"} when an org
    # keeps Stories/Tasks in a different Jira project than the Epic. Falls
    # back to project_key for any level not listed here. Levels match
    # issue_hierarchy's keys plus "review" (the review-gate Story each
    # `sdd review submit` creates) and "chg" (CHG-NNN change-request
    # tasks). See JiraConfig.key_for() and its docstring for the important
    # caveat: Jira's parent/Epic-Link field generally does not support
    # linking issues across projects, so overriding this can produce
    # issues that exist but aren't actually linked to their parent.
    project_keys: dict = field(default_factory=dict)
    issue_hierarchy: dict = field(default_factory=lambda: {
        "feature": "Feature",
        "story":   "Story",
        "task":    "Task",
    })
    parent_field: str = "parent"
    # Optional per-level overrides for parent_field -- e.g.
    # {"feature": "customfield_10014"} when the Epic's project (see
    # project_keys above) is a classic company-managed project needing
    # the Epic Link custom field, while Stories/Tasks live in a
    # next-gen project using the plain "parent" system field. Falls
    # back to parent_field for any level not listed here. See
    # parent_field_for() below.
    parent_field_by_level: dict = field(default_factory=dict)
    priority_map: dict = field(default_factory=lambda: dict(_DEFAULT_PRIORITY_MAP))
    labels: list = field(default_factory=lambda: ["sdd-generated"])
    fix_version: str | None = None
    custom_fields: dict = field(default_factory=dict)
    # Optional per-level overrides for custom field IDs -- e.g.
    # {"story": {"story_points": "customfield_10099"}} when the Jira
    # project a level lives in (see project_keys above) has a different
    # custom field scheme than the common one. Falls back to
    # custom_fields for any (level, field) pair not listed here. See
    # fields_for() below.
    custom_fields_by_level: dict = field(default_factory=dict)
    # Fixed team name/ID stamped on every issue this CLI creates, via
    # whichever custom field "team" maps to in custom_fields (or a
    # per-level override in custom_fields_by_level). None -- the
    # default -- means no team field is ever sent.
    team: str | None = None

    def key_for(self, level: str) -> str:
        """The Jira project key to use for a given hierarchy level
        (feature/story/task/chg/review), honoring project_keys overrides
        and falling back to the single project_key otherwise -- the
        common case, and the only case for every project until this
        field is explicitly set."""
        return self.project_keys.get(level, self.project_key)

    def fields_for(self, level: str) -> dict:
        """Custom field ID mapping (logical name -> Jira field ID) to use
        for a given hierarchy level, merging any custom_fields_by_level
        override over the common custom_fields mapping (override wins
        per-key). Mirrors key_for()'s fallback semantics -- every project
        with no custom_fields_by_level entries behaves exactly as before
        this field existed."""
        return {**self.custom_fields, **self.custom_fields_by_level.get(level, {})}

    def parent_field_for(self, level: str) -> str:
        """The parent-link field to use when linking a *child issue at
        this level* to its parent (e.g. level="story" when linking a
        Story under its Epic) -- honors parent_field_by_level overrides
        and falls back to the single parent_field otherwise. Mirrors
        key_for()/fields_for()'s fallback semantics."""
        return self.parent_field_by_level.get(level, self.parent_field)


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
            project_keys=jira_raw.get("project_keys", {}),
            issue_hierarchy={
                "feature": hierarchy.get("feature", "Feature"),
                "story":   hierarchy.get("story",   "Story"),
                "task":    hierarchy.get("task",     "Task"),
            },
            parent_field=jira_raw.get("parent_field", "parent"),
            parent_field_by_level=jira_raw.get("parent_field_by_level", {}),
            priority_map=bf.get("priority_map", dict(_DEFAULT_PRIORITY_MAP)),
            labels=bf.get("labels", ["sdd-generated"]),
            fix_version=bf.get("fix_version"),
            custom_fields=jira_raw.get("custom_fields", {}),
            custom_fields_by_level=jira_raw.get("custom_fields_by_level", {}),
            team=bf.get("team"),
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
