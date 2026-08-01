from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
import yaml

INTEGRATIONS_PATH = ".specify/integrations.yml"

_PAGE_ID_URL_PATTERNS = [
    re.compile(r"/pages/(\d+)(?:/|$)"),   # Cloud: .../wiki/spaces/ENG/pages/123456789/Title
    re.compile(r"[?&]pageId=(\d+)"),      # Server/DC: viewpage.action?pageId=123456
]


def parse_confluence_page_id(raw: str | None) -> str | None:
    """Accepts either a bare numeric Confluence page ID or a full page URL
    pasted straight from the browser (Cloud '.../pages/<id>/Title' or
    Server/DC '.../viewpage.action?pageId=<id>') and returns just the
    numeric ID -- most users have the URL open, not the raw ID, when
    setting this up. Returns the input unchanged if no numeric ID can be
    extracted (e.g. a Confluence tiny link like '/x/AbCdEf', which is a
    short code, not a page ID, and can't be resolved without an API
    call) -- callers decide whether to warn on that case."""
    if not raw:
        return None
    raw = str(raw).strip()
    if not raw or raw.isdigit():
        return raw or None
    for pattern in _PAGE_ID_URL_PATTERNS:
        m = pattern.search(raw)
        if m:
            return m.group(1)
    return raw

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
    # Optional override of the top-level `profile:` for Jira calls only --
    # for orgs (typically Server/Data Center) where Jira and Confluence are
    # separate servers needing separate base_url + credentials, not the
    # single Atlassian Cloud site + token that "one profile" assumes. Falls
    # back to IntegrationsConfig.profile when unset (the common Cloud case,
    # where one profile genuinely does cover both).
    profile: str | None = None
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
class DiagramsConfig:
    """How ```mermaid / ```plantuml fenced code blocks are rendered when
    pushed to Confluence. "none" (default) leaves them as plain
    syntax-highlighted code -- Confluence has no native diagram
    renderer, so a fence's content shows as text, not a diagram, unless
    one of the other modes routes it through an installed Confluence app
    or a local renderer. Valid modes: none | mermaid-app | plantuml-macro
    | local-svg. "markdown-macro" is planned but not yet implemented --
    see README.md. An unrecognized mode string behaves exactly like
    "none" -- md_to_cf.py's dispatch only special-cases the four
    recognized values, so a typo never crashes, it just silently
    doesn't render diagrams."""
    mode: str = "none"
    # ac:name of the installed Mermaid-rendering app's macro. Only used
    # when mode == "mermaid-app"; a ```mermaid fence with no macro_name
    # configured silently falls back to the plain code-block rendering.
    mermaid_app_macro: str | None = None
    # ac:name of the installed PlantUML-rendering app's macro. Only
    # applies to fences already written as ```plantuml -- this does NOT
    # convert ```mermaid content to PlantUML syntax (they're different
    # diagram languages, not mechanically translatable).
    plantuml_macro: str | None = None
    # Pixel width Confluence renders a local-svg diagram at (via the
    # <ac:image ac:width="..."> attribute). Mermaid's own renderer emits
    # SVGs sized to the diagram's natural content -- often a few hundred
    # pixels -- which Confluence then displays at that literal size with
    # no attribute override, forcing the reader to open and zoom. Setting
    # ac:width forces a readable display size regardless of the SVG's
    # intrinsic dimensions; Confluence scales height to match, preserving
    # aspect ratio. Only applies when mode == "local-svg".
    local_svg_width: int = 900


@dataclass
class ConfluenceConfig:
    space_key: str
    # Optional override of the top-level `profile:` for Confluence calls
    # only -- see JiraConfig.profile for why this exists. Falls back to
    # IntegrationsConfig.profile when unset.
    profile: str | None = None
    parent_page_id: str | None = None
    page_map: dict = field(default_factory=lambda: dict(_DEFAULT_PAGE_MAP))
    diagrams: DiagramsConfig = field(default_factory=DiagramsConfig)


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

    def jira_profile_name(self) -> str | None:
        """Which ~/.sdd/config.yml profile to use for Jira calls: jira.profile
        if set, else the top-level profile. Separate from
        confluence_profile_name() so Jira and Confluence can point at
        different servers/credentials (Data Center orgs where they're not
        the same Atlassian Cloud site)."""
        return (self.jira.profile if self.jira else None) or self.profile

    def confluence_profile_name(self) -> str | None:
        """Which ~/.sdd/config.yml profile to use for Confluence calls:
        confluence.profile if set, else the top-level profile. See
        jira_profile_name()."""
        return (self.confluence.profile if self.confluence else None) or self.profile


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
            profile=jira_raw.get("profile"),
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
        diagrams_raw = cf_raw.get("diagrams") or {}
        confluence = ConfluenceConfig(
            space_key=cf_raw["space_key"],
            profile=cf_raw.get("profile"),
            parent_page_id=parse_confluence_page_id(cf_raw.get("parent_page_id")),
            page_map=cf_raw.get("page_map", dict(_DEFAULT_PAGE_MAP)),
            diagrams=DiagramsConfig(
                mode=diagrams_raw.get("mode", "none"),
                mermaid_app_macro=(diagrams_raw.get("mermaid_app") or {}).get("macro_name"),
                plantuml_macro=(diagrams_raw.get("plantuml_macro") or {}).get("macro_name"),
                local_svg_width=(diagrams_raw.get("local_svg") or {}).get("width", 900),
            ),
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
