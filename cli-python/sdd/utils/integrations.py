from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

INTEGRATIONS_PATH = ".specify/integrations.yml"


class _DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that errors on a duplicate mapping key instead of
    silently keeping the last occurrence (PyYAML's default behavior).

    Root-caused from a real user report: a hand-edited integrations.yml
    had a second `project_key:` block under `jira:` (that one should
    have been `project_keys:` -- plural, for the per-level override
    section right below it in integrations.yml.example, whose own
    comment says so). Because YAML mappings silently keep the last
    duplicate key, the plain string project_key from the first block
    was clobbered by the dict from the second, and jira.project_key
    resolved to {"story": "...", "task": "..."} instead of a string --
    which then crashed three call frames away in jira_client.py's
    find_by_label() with a bare `AttributeError: 'dict' object has no
    attribute 'replace'`, nowhere near the actual mistake. Catching the
    duplicate key right here, at parse time, points at the exact line
    instead."""


def _construct_mapping_no_duplicates(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict:
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            hint = ""
            if key == "project_key":
                hint = ' (did you mean "project_keys" -- plural -- for the second one?)'
            raise yaml.YAMLError(
                f'Duplicate key "{key}" at line {key_node.start_mark.line + 1} '
                f"in .specify/integrations.yml{hint} -- YAML silently keeps only "
                f"the LAST occurrence of a duplicate key, so this replaced the "
                f"earlier value instead of raising an error on its own."
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_no_duplicates
)

_PAGE_ID_URL_PATTERNS = [
    re.compile(
        r"/pages/(\d+)(?:/|$)"
    ),  # Cloud: .../wiki/spaces/ENG/pages/123456789/Title
    re.compile(r"[?&]pageId=(\d+)"),  # Server/DC: viewpage.action?pageId=123456
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
    # {feature} included for every per-feature key -- without it, two
    # features sharing this fallback (no explicit confluence_page of
    # their own) would upsert the same Confluence page and overwrite
    # each other's content, since Confluence page lookup is by title
    # (see confluence.py's _resolve_page_title docstring and the
    # sdd_version migration that fixed this class of bug).
    "brd": "{project} — {feature} — Business Requirements",
    "use-cases": "{project} — {feature} — Use Cases",
    "srd": "{project} — {feature} — System Requirements",
    "design": "{project} — {feature} — Design",
    "arch": "{project} — {feature} — Architecture Overview",
    "hld": "{project} — {feature} — High-Level Design",
    "adr": "{project} — {feature} — Architecture Decisions",
    "lld": "{project} — {feature} — Low-Level Design",
    "runbook": "{project} — Runbook",
    # The title value here is actually ignored -- _resolve_page_title()
    # in confluence.py special-cases "constitution" to always use
    # "{project} — Constitution" regardless of what's mapped here (same
    # as integrations.yml.example's own comment on this key explains).
    # Its only real job is *presence*: a bare `sdd confluence push` (no
    # --doc) iterates page_map.keys(), so omitting this key (as this
    # dict did until this fix) means a bulk push silently never attempts
    # the constitution page at all -- reported by a user who ran the
    # normal create-context -> confluence push flow and found the
    # Constitution page was never created. `sdd confluence draft --doc
    # constitution` was unaffected (it takes --doc directly, bypassing
    # page_map entirely) -- only the no --doc bulk-push default set had
    # this gap.
    "constitution": "{project} — Constitution",
    # Same story as "constitution" above -- _resolve_page_title() also
    # special-cases "context" to always use "{feature} — Context"
    # regardless of what's mapped here; this key's only job is presence
    # in page_map.keys() so a bare `sdd confluence push` (no --doc)
    # includes it. `sdd confluence draft --doc context` (what
    # /create-context actually calls) was never affected -- found while
    # auditing this file for the same gap after fixing "constitution".
    "context": "{feature} — Context",
}

_DEFAULT_PRIORITY_MAP = {
    "must-have": "High",
    "should-have": "Medium",
    "could-have": "Low",
    "wont-have": "Lowest",
}

# Every level this CLI ever creates a Jira issue for, and the built-in
# Jira issue type it uses unless overridden. "review" and "cr" default to
# the same type "story"/"task" always used before this map covered them
# explicitly (see jira.py's _push_uc_draft_stories docstring on why
# review tickets sit at Story level, and cr.py's cr_submit on the CR
# review task), so an unconfigured project behaves identically to before
# -- the only change is that a user can now override review/chg/cr
# independently instead of them silently riding along with story/task's
# type. Keys match project_keys' -- feature/story/task/review/chg/cr
# (plus "epic" as a bidirectional alias for "feature", same as
# project_keys -- see _level_lookup/_level_source_key below).
_DEFAULT_ISSUE_HIERARCHY = {
    "feature": "Feature",
    "story": "Story",
    "task": "Task",
    "review": "Story",
    "chg": "Task",
    "cr": "Task",
}

# The CLI's public `sdd jira push --level` flag calls the top-level
# issue "epic" (see jira.py's _LEVELS); every config-facing lookup
# (project_keys, custom_fields_by_level, parent_field_by_level,
# issue_hierarchy) keys off "feature" instead, per the "Valid keys"
# list in integrations.yml.example -- and jira.py's own call sites
# always resolve via key_for("feature"), never key_for("epic"). So the
# alias has to work in BOTH directions: a caller resolving "feature"
# must also find an override written under "epic" (the natural thing
# for a user to write, matching the CLI's own terminology), not just
# the reverse. A one-way dict (only mapping "epic" -> "feature") looks
# right but is dead code in practice, since nothing ever looks up
# "epic" -- it would never actually find a user's `epic:` override.
_LEVEL_ALIASES = {"epic": "feature", "feature": "epic"}


def _level_lookup(mapping: dict, level: str, default):
    """Look up `level` in `mapping`, then its alias (see _LEVEL_ALIASES),
    then fall back to `default` -- the exact key actually present in
    `mapping` wins if both the level and its alias happen to be set."""
    if level in mapping:
        return mapping[level]
    alias = _LEVEL_ALIASES.get(level)
    if alias is not None and alias in mapping:
        return mapping[alias]
    return default


def _level_source_key(mapping: dict, level: str) -> str | None:
    """Which literal key in `mapping` a _level_lookup() call actually
    resolved through (for error messages) -- None if it fell through to
    the default (mapping has neither the level nor its alias)."""
    if level in mapping:
        return level
    alias = _LEVEL_ALIASES.get(level)
    if alias is not None and alias in mapping:
        return alias
    return None


class IntegrationsConfigError(Exception):
    """Raised for a structural or type problem in integrations.yml that
    isn't "file missing" (that's FileNotFoundError) -- a duplicate YAML
    key silently clobbering an earlier value, or a value with the wrong
    shape for what it's used for. Callers of load_integrations() and of
    JiraConfig's key_for()/parent_field_for() should let this propagate
    to a top-level error print, not swallow it alongside
    FileNotFoundError; it exists specifically to replace a cryptic
    AttributeError several call frames deep in jira_client.py with a
    message that names the actual bad YAML key."""


class JiraConfigError(IntegrationsConfigError):
    """IntegrationsConfigError specifically from resolving a JiraConfig
    value (key_for()/parent_field_for()) to the wrong type -- e.g. a
    mapping where a plain project-key or field-name string was
    expected."""


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
    # Per-level Jira issue type overrides -- e.g. {"chg": "Change"}.
    # Empty by default, exactly like project_keys above -- every call
    # site must resolve through issue_type_for() below, never index this
    # dict directly. (An earlier version of this field pre-filled full
    # defaults here so raw dict access stayed safe; that broke the
    # "epic" alias, since "feature" was then always present in the dict
    # and the alias fallback never got a chance to fire for a user's
    # `issue_hierarchy: {epic: ...}` override -- same class of bug
    # key_for()'s docstring describes for project_keys, avoided the same
    # way: never merge defaults into the stored dict, only at lookup
    # time.)
    issue_hierarchy: dict = field(default_factory=dict)
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
        field is explicitly set.

        Accepts "epic" as an alias for "feature" in both directions --
        the CLI's own `--level epic` flag uses that name, but
        project_keys / custom_fields_by_level / parent_field_by_level /
        issue_hierarchy all key off "feature" instead (see the "Valid
        keys" comment in integrations.yml.example), and jira.py always
        calls this with level="feature", never "epic". Without the
        alias working in the "feature" -> also-check-"epic" direction,
        a project_keys entry written as `epic: SUN` -- the natural
        thing to write given the CLI's own terminology -- is silently
        ignored: .get() just falls through to the base project_key with
        no error at all.

        Raises JiraConfigError if the resolved value isn't a plain
        string -- most commonly an accidental YAML mapping under
        project_key/project_keys in integrations.yml (e.g. copying the
        `{key: "..."}` shape Jira's own REST payloads use, instead of a
        bare string). Left unvalidated, that value propagates three call
        frames deep into jira_client.py's find_by_label(), which fails
        with a bare `AttributeError: 'dict' object has no attribute
        'replace'` -- true but useless for tracing back to the actual
        misconfigured YAML key."""
        value = _level_lookup(self.project_keys, level, self.project_key)
        if not isinstance(value, str):
            source_key = _level_source_key(self.project_keys, level)
            source = f"project_keys.{source_key}" if source_key else "project_key"
            raise JiraConfigError(
                f"jira.{source} in .specify/integrations.yml must be a plain "
                f'string project key (e.g. "MYPROJ"), not a '
                f"{type(value).__name__} ({value!r}). Check for accidental "
                f"YAML nesting under {source}."
            )
        return value

    def issue_type_for(self, level: str) -> str:
        """The Jira issue type name to use for a given hierarchy level
        (feature/story/task/review/chg/cr), honoring issue_hierarchy
        overrides and falling back to _DEFAULT_ISSUE_HIERARCHY otherwise.
        Mirrors key_for()'s alias semantics -- also accepts "epic" as an
        alias for "feature" (both directions).

        Before this method existed, only "feature"/"story"/"task" were
        ever loaded from integrations.yml's issue_hierarchy section at
        all (load_integrations() built the JiraConfig with those three
        keys hardcoded) -- a user writing `issue_hierarchy: {review:
        "Task"}` or `{chg: "Change"}` had it silently discarded, with
        review/chg/cr always riding along on story's/task's/task's type
        with no way to override them independently, contrary to what the
        per-call-site `.get("chg", ...)` fallback code implied was
        possible."""
        return _level_lookup(
            self.issue_hierarchy, level, _DEFAULT_ISSUE_HIERARCHY.get(level, "Task")
        )

    def fields_for(self, level: str) -> dict:
        """Custom field ID mapping (logical name -> Jira field ID) to use
        for a given hierarchy level, merging any custom_fields_by_level
        override over the common custom_fields mapping (override wins
        per-key). Mirrors key_for()'s fallback semantics -- every project
        with no custom_fields_by_level entries behaves exactly as before
        this field existed. Also accepts "epic" as an alias for
        "feature" (both directions) -- see key_for()'s docstring."""
        by_level = _level_lookup(self.custom_fields_by_level, level, {})
        return {**self.custom_fields, **by_level}

    def parent_field_for(self, level: str) -> str:
        """The parent-link field to use when linking a *child issue at
        this level* to its parent (e.g. level="story" when linking a
        Story under its Epic) -- honors parent_field_by_level overrides
        and falls back to the single parent_field otherwise. Mirrors
        key_for()/fields_for()'s fallback semantics, including the
        "epic"/"feature" alias (both directions) and the same type
        validation (a parent-field name must be a plain string)."""
        value = _level_lookup(self.parent_field_by_level, level, self.parent_field)
        if not isinstance(value, str):
            source_key = _level_source_key(self.parent_field_by_level, level)
            source = (
                f"parent_field_by_level.{source_key}" if source_key else "parent_field"
            )
            raise JiraConfigError(
                f"jira.{source} in .specify/integrations.yml must be a plain "
                f'string field name (e.g. "parent" or "customfield_10014"), '
                f"not a {type(value).__name__} ({value!r}). Check for "
                f"accidental YAML nesting under {source}."
            )
        return value


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
    reviewer_jira_user: str  # Jira accountId (Cloud) or username (Server/DC)
    reviewer_role: str  # Human-readable label e.g. "Product Owner"
    phase: str  # specify | planning | tasks | release
    sequence: int  # 1-based order within the phase
    confluence_page: str  # page title template, supports {project}


@dataclass
class PrAutomation:
    enabled: bool = True
    branch_pattern: str = "feature/{task_id}-{slug}"
    pr_title_pattern: str = "feat({task_id}): {title}"


@dataclass
class CodeReviewConfig:
    enabled: bool = True
    pre_review: bool = True  # false = skip pre-review, go straight to human review


@dataclass
class IntegrationsConfig:
    profile: str | None
    jira: JiraConfig | None
    confluence: ConfluenceConfig | None
    document_reviews: dict[str, DocumentReview] = field(default_factory=dict)
    approved_statuses: list[str] = field(default_factory=lambda: ["Done", "Approved"])
    approved_keywords: list[str] = field(
        default_factory=lambda: [
            "approved",
            "lgtm",
            "looks good",
            "go ahead",
            "confirmed",
        ]
    )
    # Status to transition a review ticket to when `sdd review apply` fires
    # (a document changed post-approval -- e.g. /clarify patched an
    # Approved doc, or NEEDS REVISION feedback is being addressed). Must
    # name a real status in the Jira project's workflow; None (the
    # default -- unset in integrations.yml) skips the transition attempt
    # entirely. Deliberately opt-in rather than defaulting to a guessed
    # name like "In Review": workflow status names vary too much across
    # orgs to guess safely, and a wrong guess would just 400 silently
    # (transition_issue() no-ops instead of erroring either way, but an
    # unset default avoids the wasted API call altogether for anyone who
    # hasn't configured it).
    reopen_status: str | None = None
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
    try:
        # bandit's B506 pattern-matches the literal `Loader=` argument and
        # doesn't resolve subclasses -- _DuplicateKeyLoader IS a
        # yaml.SafeLoader subclass (see its definition above), just with an
        # extra duplicate-key check on top; no unsafe tag handlers are
        # added. Equivalent to yaml.safe_load() for anything this constructor
        # can actually parse.
        raw = yaml.load(p.read_text(encoding="utf-8"), Loader=_DuplicateKeyLoader) or {}  # nosec B506
    except yaml.YAMLError as e:
        raise IntegrationsConfigError(str(e)) from None

    jira: JiraConfig | None = None
    jira_raw = raw.get("jira")
    if jira_raw:
        hierarchy = jira_raw.get("issue_hierarchy", {})
        bf = jira_raw.get("base_fields", {})
        jira = JiraConfig(
            project_key=jira_raw["project_key"],
            profile=jira_raw.get("profile"),
            project_keys=jira_raw.get("project_keys", {}),
            # Passed through as-written -- previously this hardcoded only
            # feature/story/task, so a "review"/"chg"/"cr" override was
            # silently discarded no matter what was written in
            # integrations.yml. Resolution (including defaults and the
            # "epic" alias) happens entirely in issue_type_for().
            issue_hierarchy=hierarchy,
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
                mermaid_app_macro=(diagrams_raw.get("mermaid_app") or {}).get(
                    "macro_name"
                ),
                plantuml_macro=(diagrams_raw.get("plantuml_macro") or {}).get(
                    "macro_name"
                ),
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
                _DEFAULT_PAGE_MAP.get(doc_key, f"{{project}} — {doc_key.upper()}"),
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
            ["approved", "lgtm", "looks good", "go ahead", "confirmed"],
        ),
        reopen_status=raw.get("reopen_status"),
        pr_automation=pr_automation,
        code_review=code_review,
    )
