from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml

INTEGRATIONS_PATH = ".specify/integrations.yml"

_DEFAULT_PAGE_MAP = {
    "brd":     "{project} — Business Requirements",
    "srd":     "{project} — System Requirements",
    "arch":    "{project} — Architecture Overview",
    "hld":     "{project} — High-Level Design",
    "lld":     "{project} — Low-Level Design",
    "adr":     "{project} — Architecture Decisions",
    "runbook": "{project} — Runbook",
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
class IntegrationsConfig:
    profile: str | None
    jira: JiraConfig | None
    confluence: ConfluenceConfig | None


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

    return IntegrationsConfig(
        profile=raw.get("profile"),
        jira=jira,
        confluence=confluence,
    )
