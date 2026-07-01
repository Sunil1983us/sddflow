#!/usr/bin/env python3
"""
jira-push.py — Push SDD artifacts to Jira via REST API.

Usage:
  python3 .specify/scripts/jira-push.py --level epic
  python3 .specify/scripts/jira-push.py --level story
  python3 .specify/scripts/jira-push.py --level task
  python3 .specify/scripts/jira-push.py --level chg --cr CR-001
  python3 .specify/scripts/jira-push.py --level all
  python3 .specify/scripts/jira-push.py --level task --dry-run

Reads:  .specify/jira-config.yml  (copy from .specify/templates/jira-config-template.yml)
Reads:  .specify/manifest.yml
Reads:  docs/jira/epic.md, stories-refined.md, stories-draft.md
Reads:  .specify/features/{feature}/tasks.md
Reads:  .specify/features/{feature}/changesets/CR-NNN.md
Writes: docs/jira/keys.yml

Requirements: pip install pyyaml
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────────
# Script lives at .specify/scripts/jira-push.py → parents[2] is project root
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".specify" / "jira-config.yml"
MANIFEST_PATH = ROOT / ".specify" / "manifest.yml"
KEYS_PATH = ROOT / "docs" / "jira" / "keys.yml"
TODAY = date.today().isoformat()


# ── Utilities ──────────────────────────────────────────────────────────────────

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def warn(msg):
    print(f"WARNING: {msg}")

def resolve_env(val):
    """Replace ${VAR} placeholders with environment variable values."""
    if not isinstance(val, str):
        return val
    return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), m.group(0)), val)


# ── Config / manifest / keys ───────────────────────────────────────────────────

def load_config():
    if not CONFIG_PATH.exists():
        die(
            f"Jira config not found at {CONFIG_PATH}.\n"
            "Copy .specify/templates/jira-config-template.yml to .specify/jira-config.yml "
            "and fill in your Jira project values. Add .specify/jira-config.yml to .gitignore."
        )
    with open(CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    cfg = raw.get("jira", {})
    cfg["base_url"]   = resolve_env(cfg.get("base_url", "")).rstrip("/")
    cfg["email"]      = resolve_env(cfg.get("email", ""))
    cfg["api_token"]  = resolve_env(cfg.get("api_token", ""))
    return cfg

def load_manifest():
    if not MANIFEST_PATH.exists():
        die("manifest.yml not found. Is this an SDD project?")
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f) or {}

def load_keys():
    if not KEYS_PATH.exists():
        return {}
    with open(KEYS_PATH) as f:
        return yaml.safe_load(f) or {}

def save_keys(keys):
    KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(KEYS_PATH, "w") as f:
        yaml.dump(keys, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ── Jira REST client ───────────────────────────────────────────────────────────

class JiraClient:
    def __init__(self, cfg, dry_run=False):
        self.base_url = cfg["base_url"]
        self.api_ver  = cfg.get("api_version", "3")
        self._api     = f"{self.base_url}/rest/api/{self.api_ver}"
        self.dry_run  = dry_run
        creds = f"{cfg['email']}:{cfg['api_token']}"
        self._auth = "Basic " + base64.b64encode(creds.encode()).decode()

    def _request(self, method, path, body=None):
        url  = f"{self._api}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req  = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": self._auth,
                "Accept":        "application/json",
                "Content-Type":  "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req) as resp:
                content = resp.read()
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as e:
            body_bytes = e.read()
            body_text  = body_bytes.decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code} {method} {url} — {body_text}") from e

    def test_connectivity(self):
        try:
            self._request("GET", "/myself")
        except RuntimeError as e:
            msg = str(e)
            if "HTTP 401" in msg:
                die("Invalid credentials. Verify JIRA_EMAIL and JIRA_API_TOKEN.")
            if "HTTP 403" in msg:
                die("Insufficient permissions. Verify your Jira user has Create Issue permission for the target project.")
            die(f"Cannot reach Jira at {self.base_url}: {msg}")

    def validate_custom_fields(self, cfg):
        """Cross-check configured customfield_NNN IDs against what Jira returns."""
        all_fields = {f["id"]: f["name"] for f in self._request("GET", "/field")}
        fm = cfg.get("field_mappings", {})
        tf = cfg.get("traceability_fields", {})
        for section_name, section in [("field_mappings", fm), ("traceability_fields", tf)]:
            for sdd_key, jira_id in section.items():
                if jira_id and str(jira_id).startswith("customfield_") and jira_id not in all_fields:
                    warn(f"{section_name}.{sdd_key} references '{jira_id}' which was not found "
                         f"in this Jira instance — it will be skipped. Update jira-config.yml to fix.")

    def find_existing(self, project, issuetype, summary):
        """Return the issue key if an issue with this summary already exists, else None."""
        safe_summary = summary[:60].replace('"', '\\"')
        jql = f'project="{project}" AND issuetype="{issuetype}" AND summary~"{safe_summary}"'
        result = self._request(
            "GET",
            f"/issue/search?jql={urllib.parse.quote(jql)}&fields=key,summary&maxResults=10"
        )
        for issue in result.get("issues", []):
            if issue["fields"]["summary"].strip().lower() == summary.strip().lower():
                return issue["key"]
        return None

    def create_issue(self, payload):
        if self.dry_run:
            print(f"    DRY-RUN CREATE:\n{json.dumps(payload, indent=4)}")
            return "__DRY_RUN__"
        result = self._request("POST", "/issue", payload)
        return result["key"]

    def update_issue(self, key, fields):
        if self.dry_run:
            print(f"    DRY-RUN UPDATE {key}:\n{json.dumps({'fields': fields}, indent=4)}")
            return
        self._request("PUT", f"/issue/{key}", {"fields": fields})

    def upsert(self, project, issuetype, summary, fields, upsert_mode=True):
        """Create or update a Jira issue. Returns (key, action)."""
        if upsert_mode:
            existing_key = self.find_existing(project, issuetype, summary)
            if existing_key:
                self.update_issue(existing_key, fields)
                return existing_key, "updated"
        payload = {"fields": fields}
        key = self.create_issue(payload)
        return key, "created"


# ── ADF (Atlassian Document Format) helpers ────────────────────────────────────

def adf_paragraph(text):
    return {"type": "paragraph", "content": [{"type": "text", "text": str(text)}]}

def adf_bullet_list(items):
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [adf_paragraph(item)]}
            for item in items if item
        ]
    }

def adf_doc(*paragraphs, bullet_list=None):
    content = [adf_paragraph(p) for p in paragraphs if p and str(p).strip()]
    if bullet_list:
        content.append(adf_bullet_list(bullet_list))
    return {"type": "doc", "version": 1, "content": content or [adf_paragraph(" ")]}


# ── Field builder ──────────────────────────────────────────────────────────────

def build_fields(cfg, level, summary, description_adf, priority):
    """Build the base Jira fields dict from config."""
    return {
        "project":     {"key": cfg["projects"][level]},
        "issuetype":   {"name": cfg["issue_types"][level]},
        "summary":     summary,
        "description": description_adf,
        "priority":    {"name": priority},
        "labels":      cfg.get("default_labels", {}).get(level, []),
    }

def add_optional_field(fields, cfg_field_id, value):
    """Add a field to fields dict only if cfg_field_id is set and value is non-empty."""
    if cfg_field_id and value:
        fields[cfg_field_id] = value

def apply_parent_link(fields, cfg, parent_key):
    """Attach parent link using the configured strategy."""
    strategy = cfg.get("parent_link_strategy", "parent")
    if strategy == "parent":
        fields["parent"] = {"key": parent_key}
    elif strategy == "epic_link":
        epic_link_field = cfg.get("field_mappings", {}).get("epic_link", "customfield_10014")
        fields[epic_link_field] = parent_key

def sprint_value(cfg, sprint_num):
    pattern = cfg.get("sprint_name_pattern", "Sprint {N}")
    return {"name": pattern.replace("{N}", str(sprint_num))}

def moscow_priority(cfg, moscow):
    mapping = cfg.get("moscow_to_jira_priority", {
        "Must Have": "High", "Should Have": "Medium",
        "Could Have": "Low", "Won't Have": "Lowest",
    })
    return mapping.get(moscow, "Medium")


# ── Markdown parsers ───────────────────────────────────────────────────────────

def parse_brd(feature):
    """Extract BO-NNN objectives from brd.md."""
    path = ROOT / ".specify" / "features" / feature / "brd.md"
    if not path.exists():
        return []
    text = path.read_text()
    objectives = []
    for m in re.finditer(r"(BO-\d+[^\n]*)", text):
        line = re.sub(r"[|*`_]", "", m.group(1)).strip()
        if line and len(line) > 5:
            objectives.append(line)
    return objectives[:10]

def parse_stories_file(path):
    """
    Parse docs/jira/stories-refined.md or stories-draft.md.
    Returns list of story dicts.
    """
    if not path.exists():
        return []
    text = path.read_text()
    stories = []
    blocks = re.split(r"\n(?=## (?:STORY-(?:DRAFT-)?|UC-))", text)
    for block in blocks:
        if not re.match(r"## ", block):
            continue
        story = {}
        m = re.match(r"## ([^\s:]+):\s*(.+)", block)
        if m:
            story["sdd_id"] = m.group(1).strip()
            story["title"]  = m.group(2).strip()
        for key, pattern in [
            ("summary",       r"^Summary:\s*(.+)$"),
            ("uc_reference",  r"^UC Reference:\s*(.+)$"),
            ("fr_reference",  r"^FR Reference:\s*(.+)$"),
            ("moscow",        r"^MoSCoW:\s*(.+)$"),
            ("story_points",  r"^Story Points:\s*(.+)$"),
            ("actor",         r"^Actor:\s*(.+)$"),
            ("nfr_reference", r"^NFR Reference:\s*(.+)$"),
        ]:
            m = re.search(pattern, block, re.MULTILINE)
            if m:
                val = m.group(1).strip()
                if val and "TBD" not in val and "set by" not in val:
                    story[key] = val
        # Acceptance criteria lines
        ac_start = block.find("Acceptance Criteria:")
        if ac_start >= 0:
            story["acceptance_criteria"] = re.findall(r"^\s*[-*]\s+(.+)$", block[ac_start:], re.MULTILINE)
        if story.get("sdd_id") or story.get("summary"):
            stories.append(story)
    return stories

def parse_tasks_md(feature):
    """Parse tasks.md. Returns list of task dicts."""
    path = ROOT / ".specify" / "features" / feature / "tasks.md"
    if not path.exists():
        return []
    text = path.read_text()
    tasks = []
    blocks = re.split(r"\n(?=### (?:TASK|PERF)-)", text)
    for block in blocks:
        if not re.match(r"### (?:TASK|PERF)-", block):
            continue
        task = {}
        m = re.match(r"### ((?:TASK|PERF)-[^\s—–-]+)\s*[—–-]+\s*(.+)", block)
        if m:
            task["sdd_id"] = m.group(1).strip()
            task["title"]  = m.group(2).strip()
        for key, pattern in [
            ("story",           r"^Story:\s*(STORY-\S+)"),
            ("satisfies",       r"^Satisfies:\s*(.+)"),
            ("verifies",        r"^Verifies:\s*(.+)"),
            ("risk",            r"^Risk:\s*(R-\d+[^\n]*)"),
            ("estimated_lines", r"Estimated lines:\s*~?(\d+)"),
            ("sprint",          r"Sprint:\s*(\d+)"),
        ]:
            m = re.search(pattern, block, re.MULTILINE)
            if m:
                task[key] = m.group(1).strip()
        ac_start = block.find("Acceptance criteria:")
        if ac_start >= 0:
            task["acceptance_criteria"] = re.findall(r"- \[ \]\s*(.+)", block[ac_start:])
        # Estimate story points from line count (1 SP per ~20 lines, capped at 8)
        if task.get("estimated_lines"):
            task["story_points"] = max(1, min(8, int(task["estimated_lines"]) // 20 + 1))
        if task.get("sdd_id"):
            tasks.append(task)
    return tasks

def parse_changeset(cr_id, feature):
    """Parse §4 CHG-NNN tasks table from a changeset file."""
    path = ROOT / ".specify" / "features" / feature / "changesets" / f"{cr_id}.md"
    if not path.exists():
        die(f"Changeset not found: {path}")
    text = path.read_text()
    chg_tasks = []
    # Match table rows in §4: | CHG-NNN | description | satisfies | ~N | ... |
    for m in re.finditer(
        r"\|\s*(CHG-\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*~?(\d+)[^|]*\|",
        text
    ):
        chg_tasks.append({
            "sdd_id":      m.group(1).strip(),
            "description": m.group(2).strip(),
            "satisfies":   m.group(3).strip(),
            "est_lines":   int(m.group(4)),
        })
    return chg_tasks


# ── Push functions ─────────────────────────────────────────────────────────────

def push_epic(client, cfg, feature, feature_name, keys):
    print("\n── Epic ─────────────────────────────────────────────────────")
    objectives = parse_brd(feature)
    description = adf_doc(
        "Business Objectives:",
        bullet_list=objectives if objectives else ["See brd.md for full objectives."]
    )
    fields = build_fields(cfg, "epic", feature_name, description, "High")

    # Classic Jira: set Epic Name custom field if configured
    epic_name_field = cfg.get("field_mappings", {}).get("epic_name")
    if epic_name_field:
        fields[epic_name_field] = feature_name

    print(f"  '{feature_name}'")
    key, action = client.upsert(
        cfg["projects"]["epic"], cfg["issue_types"]["epic"],
        feature_name, fields,
        upsert_mode=cfg.get("upsert_mode", True)
    )
    print(f"  {action.upper()}: {key} — {cfg['base_url']}/browse/{key}")

    keys["epic"] = {"jira_key": key, "summary": feature_name, "stage": "after-brd", "pushed": TODAY}
    return key


def push_stories(client, cfg, feature, keys):
    print("\n── Stories ──────────────────────────────────────────────────")
    refined = ROOT / "docs" / "jira" / "stories-refined.md"
    draft   = ROOT / "docs" / "jira" / "stories-draft.md"
    source  = refined if refined.exists() else draft
    if not source.exists():
        die("No story definitions found. Run /specify-uc to generate docs/jira/stories-draft.md.")
    stage   = "after-srd" if source == refined else "after-uc"
    stories = parse_stories_file(source)
    if not stories:
        die(f"No stories parsed from {source}. Check the file format.")

    epic_key = keys.get("epic", {}).get("jira_key")
    if not epic_key:
        warn("Epic key not in keys.yml — Stories will be created without Epic parent link. Run --level epic first.")

    fm = cfg.get("field_mappings", {})
    tf = cfg.get("traceability_fields", {})
    created_stories = list(keys.get("stories") or [])

    for story in stories:
        sdd_id  = story.get("sdd_id", "?")
        summary = story.get("summary") or story.get("title", sdd_id)
        moscow  = story.get("moscow", "Should Have")
        ac_text = "; ".join(story.get("acceptance_criteria") or [])

        description = adf_doc(
            f"UC Reference: {story.get('uc_reference', '')}",
            f"Actor: {story['actor']}" if story.get("actor") else "",
            f"FR References: {story.get('fr_reference', 'TBD')}",
            f"Acceptance Criteria: {ac_text}" if ac_text else "",
        )
        fields = build_fields(cfg, "story", summary, description, moscow_priority(cfg, moscow))

        if epic_key:
            apply_parent_link(fields, cfg, epic_key)

        add_optional_field(fields, fm.get("acceptance_criteria"), ac_text)
        add_optional_field(fields, tf.get("uc_reference"),   story.get("uc_reference"))
        add_optional_field(fields, tf.get("fr_reference"),   story.get("fr_reference"))
        add_optional_field(fields, tf.get("moscow_priority"), moscow)
        add_optional_field(fields, tf.get("sdd_stage"),      stage)

        print(f"  '{summary}' [{moscow}]")
        key, action = client.upsert(
            cfg["projects"]["story"], cfg["issue_types"]["story"],
            summary, fields,
            upsert_mode=cfg.get("upsert_mode", True)
        )
        print(f"  {action.upper()}: {key}")

        existing = next((s for s in created_stories if s.get("sdd_id") == sdd_id), None)
        entry = {"sdd_id": sdd_id, "jira_key": key, "summary": summary,
                 "moscow": moscow, "fr_reference": story.get("fr_reference"),
                 "stage": stage, "pushed": TODAY}
        if existing:
            existing.update(entry)
        else:
            created_stories.append(entry)

    keys["stories"] = created_stories
    return created_stories


def push_tasks(client, cfg, feature, keys):
    print("\n── Tasks ────────────────────────────────────────────────────")
    tasks = parse_tasks_md(feature)
    if not tasks:
        die(f"No tasks found in tasks.md for feature '{feature}'. Run /task first.")

    # Build STORY-NNN → jira_key lookup
    story_lookup = {s["sdd_id"]: s["jira_key"] for s in (keys.get("stories") or []) if s.get("sdd_id")}

    fm = cfg.get("field_mappings", {})
    tf = cfg.get("traceability_fields", {})
    created_tasks = list(keys.get("tasks") or [])

    for task in tasks:
        sdd_id    = task.get("sdd_id", "?")
        title     = task.get("title", sdd_id)
        story_ref = task.get("story", "")
        parent_key = story_lookup.get(story_ref)
        if not parent_key:
            warn(f"  {sdd_id}: parent story '{story_ref}' not in keys.yml — no parent link")

        ac_text = "; ".join(task.get("acceptance_criteria") or [])
        description = adf_doc(
            f"Story: {story_ref}",
            f"Satisfies: {task.get('satisfies', '')}",
            f"Verifies: {task.get('verifies', '')}",
            f"Risk: {task.get('risk', '')}" if task.get("risk") else "",
            f"Acceptance Criteria: {ac_text}" if ac_text else "",
        )
        fields = build_fields(cfg, "task", title, description, "Medium")

        if parent_key:
            apply_parent_link(fields, cfg, parent_key)

        sp_field = fm.get("story_points")
        add_optional_field(fields, sp_field, task.get("story_points"))
        if task.get("sprint") and fm.get("sprint"):
            fields[fm["sprint"]] = sprint_value(cfg, task["sprint"])
        add_optional_field(fields, fm.get("acceptance_criteria"), ac_text)
        add_optional_field(fields, tf.get("fr_reference"),  task.get("satisfies"))
        add_optional_field(fields, tf.get("tc_reference"),  task.get("verifies"))
        add_optional_field(fields, tf.get("risk_reference"), task.get("risk"))

        print(f"  '{title}'")
        key, action = client.upsert(
            cfg["projects"]["task"], cfg["issue_types"]["task"],
            title, fields,
            upsert_mode=cfg.get("upsert_mode", True)
        )
        print(f"  {action.upper()}: {key}")

        existing = next((t for t in created_tasks if t.get("sdd_id") == sdd_id), None)
        entry = {"sdd_id": sdd_id, "jira_key": key, "parent_story": story_ref,
                 "parent_jira_key": parent_key or "", "summary": title, "pushed": TODAY}
        if existing:
            existing.update(entry)
        else:
            created_tasks.append(entry)

    keys["tasks"] = created_tasks
    return created_tasks


def push_chg(client, cfg, feature, keys, cr_id):
    print(f"\n── CHG tasks ({cr_id}) ───────────────────────────────────────")
    chg_tasks = parse_changeset(cr_id, feature)
    if not chg_tasks:
        die(f"No CHG tasks found in changesets/{cr_id}.md §4.")

    tf = cfg.get("traceability_fields", {})
    # FR-NNN → story jira_key
    fr_to_story = {}
    for s in (keys.get("stories") or []):
        for fr in re.findall(r"FR-\d+", s.get("fr_reference") or ""):
            fr_to_story[fr] = s.get("jira_key", "")
    epic_key = keys.get("epic", {}).get("jira_key")
    created_chg = list(keys.get("chg_tasks") or [])

    for chg in chg_tasks:
        sdd_id    = chg["sdd_id"]
        desc      = chg["description"]
        satisfies = chg.get("satisfies", "")
        parent_key = next(
            (fr_to_story[fr] for fr in re.findall(r"FR-\d+", satisfies) if fr in fr_to_story),
            epic_key
        )
        description = adf_doc(
            f"Change Request: {cr_id}",
            f"Satisfies: {satisfies}",
            f"Description: {desc}",
        )
        fields = build_fields(cfg, "chg", desc, description, "Medium")
        if parent_key:
            apply_parent_link(fields, cfg, parent_key)
        add_optional_field(fields, tf.get("fr_reference"), satisfies)

        print(f"  '{desc}'")
        key, action = client.upsert(
            cfg["projects"]["chg"], cfg["issue_types"]["chg"],
            desc, fields,
            upsert_mode=cfg.get("upsert_mode", True)
        )
        print(f"  {action.upper()}: {key}")
        created_chg.append({"sdd_id": sdd_id, "cr": cr_id, "jira_key": key,
                             "parent_jira_key": parent_key or "", "pushed": TODAY})

    keys["chg_tasks"] = created_chg
    return created_chg


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Push SDD artifacts to Jira via REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--level", choices=["epic", "story", "task", "chg", "all"],
                        help="SDD level to push (inferred from existing files if omitted)")
    parser.add_argument("--cr",      default=None, metavar="CR-NNN",
                        help="Change request ID (required for --level chg)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print payloads without making any API calls")
    parser.add_argument("--feature", default=None,
                        help="Override feature name (default: from manifest.yml)")
    args = parser.parse_args()

    cfg      = load_config()
    manifest = load_manifest()
    keys     = load_keys()

    dry_run = args.dry_run or cfg.get("dry_run", False)
    if dry_run:
        print("DRY-RUN mode — no API calls will be made.\n")

    # Validate credentials
    email = cfg.get("email", "")
    token = cfg.get("api_token", "")
    if not email or "${JIRA_EMAIL}" in email:
        die("JIRA_EMAIL environment variable is not set.")
    if not token or "${JIRA_API_TOKEN}" in token:
        die("JIRA_API_TOKEN environment variable is not set.")

    # Feature name
    project_cfg = manifest.get("project", {})
    feature     = args.feature or project_cfg.get("feature", "")
    feature_name = project_cfg.get("name") or feature.replace("-", " ").title()

    client = JiraClient(cfg, dry_run=dry_run)

    if not dry_run:
        print("Testing Jira connectivity...")
        client.test_connectivity()
        print("Connected.")
        print("Validating custom field IDs...")
        client.validate_custom_fields(cfg)

    # Infer level if not provided
    level = args.level
    if not level:
        features_dir = ROOT / ".specify" / "features" / feature
        has_brd    = (features_dir / "brd.md").exists()
        has_uc     = (features_dir / "use-cases.md").exists()
        has_tasks  = (features_dir / "tasks.md").exists()
        epic_done  = bool((keys.get("epic") or {}).get("jira_key"))
        story_done = bool(keys.get("stories"))
        task_done  = bool(keys.get("tasks"))

        if   has_tasks  and not task_done:  level = "task"
        elif has_uc     and not story_done: level = "story"
        elif has_brd    and not epic_done:  level = "epic"
        else:                               level = "all"
        print(f"Inferred level: {level}")

    if level == "chg" and not args.cr:
        die("--cr CR-NNN is required when --level chg")

    levels = ["epic", "story", "task"] if level == "all" else [level]

    for lv in levels:
        if   lv == "epic":  push_epic(client, cfg, feature, feature_name, keys)
        elif lv == "story": push_stories(client, cfg, feature, keys)
        elif lv == "task":  push_tasks(client, cfg, feature, keys)
        elif lv == "chg":   push_chg(client, cfg, feature, keys, args.cr)

    if not dry_run:
        save_keys(keys)

    # ── Summary ───────────────────────────────────────────────────────────────
    base = cfg["base_url"]
    print("\n── Summary ──────────────────────────────────────────────────")
    if (keys.get("epic") or {}).get("jira_key"):
        ek = keys["epic"]["jira_key"]
        print(f"  Epic:    {ek} — {base}/browse/{ek}")
    if keys.get("stories"):
        keys_list = ", ".join(s["jira_key"] for s in keys["stories"][:6])
        print(f"  Stories: {len(keys['stories'])} — {keys_list}")
    if keys.get("tasks"):
        keys_list = ", ".join(t["jira_key"] for t in keys["tasks"][:6])
        print(f"  Tasks:   {len(keys['tasks'])} — {keys_list}")
    if keys.get("chg_tasks"):
        keys_list = ", ".join(c["jira_key"] for c in keys["chg_tasks"][:6])
        print(f"  CHG:     {len(keys['chg_tasks'])} — {keys_list}")
    if not dry_run:
        print(f"\n  Keys saved: docs/jira/keys.yml")
    else:
        print("\n  Dry run complete — no changes made. Remove --dry-run to push.")
    print("─────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
