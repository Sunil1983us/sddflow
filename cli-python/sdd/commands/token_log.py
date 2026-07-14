"""sdd token-log — record REAL token usage for one command from Claude
Code's local session transcript, instead of the character-count
estimate the framework's prompts fall back to on every other AI tool.

Claude Code-only by nature (see sdd/utils/claude_code_transcript.py for
why) -- exits with a distinct, documented code for every reason a
prompt calling this needs to branch on: opt-in gate not enabled, no
transcript found (fall back to the estimate), or nothing new to log.
None of these are errors in the usual sense; only exit 1 is."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re

import click
import yaml
from rich.console import Console

from sdd.utils.manifest import read_manifest
from sdd.utils.claude_code_transcript import find_session_transcripts, sum_usage_since

console = Console()

TOKEN_PRICING_PATH = Path(".specify") / "memory" / "token-pricing.yml"
TOKEN_USAGE_TEMPLATE_PATH = Path(".specify") / "templates" / "token-usage-template.md"

# Matches a markdown table separator row of ANY column count -- the
# Per-Command Log table gained a Source column in this version, so a
# file created by an earlier release has a 7-column separator
# (|---|---|---|---|---|---|---|), not the current 8-column one. Both
# must be found the same way, or upgrading silently breaks logging for
# every project that already has a token-usage.md.
_TABLE_SEP_RE = re.compile(r"^\|(?:-+\|)+$")


def _feature_dir(feature_name: str) -> Path:
    return Path(".specify") / "features" / feature_name


def _load_pricing() -> dict | None:
    if not TOKEN_PRICING_PATH.exists():
        return None
    return yaml.safe_load(TOKEN_PRICING_PATH.read_text()) or {}


def _cost_for(pricing: dict, model: str, input_tokens: int, output_tokens: int) -> str:
    models = pricing.get("models") or {}
    row = models.get(model)
    fallback = pricing.get("unknown_model_fallback", "n/a")
    if not row:
        return fallback
    in_rate = row.get("input_per_million")
    out_rate = row.get("output_per_million")
    if in_rate is None or out_rate is None:
        return fallback
    cost = (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate
    return f"${cost:.4f}"


def _parse_table_row(line: str) -> dict | None:
    """Parses one Per-Command Log row, tolerating both the current
    8-column format (with Source) and the legacy 7-column format from
    before that column existed -- older rows must never be silently
    dropped just because this version added a column. Returns None for
    any line that isn't a data row (header, separator, blank, prose)."""
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    if len(cells) not in (7, 8) or not cells[0].isdigit():
        return None
    if len(cells) == 8:
        _, command, model, inp, out, cost, source, ts = cells
    else:
        _, command, model, inp, out, cost, ts = cells
        source = "Estimated"  # legacy rows pre-date this column
    return {
        "command": command, "model": model, "input": inp,
        "output": out, "cost": cost, "source": source, "timestamp": ts,
    }


def _existing_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        row = _parse_table_row(line)
        if row:
            rows.append(row)
    return rows


def _last_timestamp(rows: list[dict]) -> datetime | None:
    for row in reversed(rows):
        raw = row["timestamp"]
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
    return None


def _parse_amount(cell: str) -> float | None:
    cell = cell.strip().lstrip("$")
    try:
        return float(cell)
    except ValueError:
        return None


def _parse_int(cell: str) -> int:
    try:
        return int(cell.strip())
    except ValueError:
        return 0


def _init_from_template(feature_name: str) -> str:
    if TOKEN_USAGE_TEMPLATE_PATH.exists():
        return TOKEN_USAGE_TEMPLATE_PATH.read_text().replace("{Feature Name}", feature_name)
    # Extremely defensive fallback -- the template ships in every pack,
    # this only triggers if someone deleted it from their own copy.
    return (
        f"# Token Usage Log\n# Feature: {feature_name}\n\n"
        "## Running Totals\n\n| Metric | Value |\n|---|---|\n\n---\n\n"
        "## Per-Command Log\n\n"
        "| # | Command | Model | Input Tokens | Output Tokens | Cost (USD) | Source | Timestamp |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )


def _rewrite_running_totals(text: str, all_rows: list[dict]) -> str:
    import re
    total_input = sum(_parse_int(r["input"]) for r in all_rows)
    total_output = sum(_parse_int(r["output"]) for r in all_rows)
    amounts = [_parse_amount(r["cost"]) for r in all_rows]
    if all_rows and all(a is not None for a in amounts):
        total_cost = f"${sum(amounts):.4f}"
    elif all_rows:
        total_cost = "n/a — see notes"
    else:
        total_cost = "$0.0000"
    last_updated = all_rows[-1]["timestamp"] if all_rows else ""

    for label, value in [
        ("Total Input Tokens", str(total_input)),
        ("Total Output Tokens", str(total_output)),
        ("Total Est. Input Tokens", str(total_input)),   # legacy label, if still present
        ("Total Est. Output Tokens", str(total_output)), # legacy label, if still present
        ("Total Cost (USD)", total_cost),
        ("Total Est. Cost (USD)", total_cost),            # legacy label, if still present
        ("Commands logged", str(len(all_rows))),
        ("Last updated", last_updated),
    ]:
        pattern = rf"(\|\s*{re.escape(label)}\s*\|)[^|]*(\|)"
        text = re.sub(pattern, rf"\g<1> {value} \g<2>", text, count=1)
    return text


@click.command()
@click.option("--feature", default=None, help="Feature name (default: from manifest.yml)")
@click.option("--command", "command_name", required=True,
              help="Label for this command, e.g. specify-brd")
@click.option("--dry-run", is_flag=True, help="Print what would be logged without writing")
def token_log_command(feature, command_name, dry_run):
    """Log REAL token usage for one command, read from Claude Code's own
    local session transcript. Exits non-zero for every reason a caller
    should fall back to the character-count estimate instead -- see
    HOW-TO-USE.md for the exact codes."""
    manifest = read_manifest() or {}
    proj = manifest.get("project") or {}
    feature_name = feature or proj.get("feature", "")
    if not feature_name:
        console.print("[red]✗  No feature name -- pass --feature or set manifest.yml → project.feature[/red]")
        raise SystemExit(1)

    pricing = _load_pricing()
    if pricing is None:
        console.print(
            "[dim]·  Token usage logging is off -- .specify/memory/token-pricing.yml "
            "doesn't exist. Not logging (real or estimated).[/dim]"
        )
        raise SystemExit(2)

    main_transcript, subagent_transcripts = find_session_transcripts()
    if main_transcript is None:
        console.print(
            "[dim]·  No Claude Code session transcript found for this project -- "
            "not running under Claude Code, or no session has touched it yet. "
            "Falling back to the character-count estimate.[/dim]"
        )
        raise SystemExit(3)

    token_usage_path = _feature_dir(feature_name) / "token-usage.md"
    existing_rows = _existing_rows(token_usage_path)
    since = _last_timestamp(existing_rows)

    usage_by_model = sum_usage_since([main_transcript] + subagent_transcripts, since)
    # Some transcript entries carry a placeholder model (observed:
    # "<synthetic>") with an all-zero usage object -- an internal Claude
    # Code implementation detail (e.g. title generation), not real
    # command work. Nothing meaningful to log for a bucket that's zero
    # across every field.
    usage_by_model = {
        model: usage for model, usage in usage_by_model.items()
        if usage.billed_input_tokens or usage.output_tokens
    }
    if not usage_by_model:
        console.print("[dim]·  No new Claude Code usage since the last logged row -- nothing to log.[/dim]")
        raise SystemExit(0)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_rows: list[dict] = []
    for model, usage in sorted(usage_by_model.items()):
        input_tokens = usage.billed_input_tokens
        output_tokens = usage.output_tokens
        new_rows.append({
            "command": command_name,
            "model": model,
            "input": str(input_tokens),
            "output": str(output_tokens),
            "cost": _cost_for(pricing, model, input_tokens, output_tokens),
            "source": "Real (Claude Code)",
            "timestamp": now,
        })

    if dry_run:
        for r in new_rows:
            console.print(
                f"[dim]would log[/dim]  {r['command']}  [cyan]{r['model']}[/cyan]  "
                f"in={r['input']} out={r['output']} cost={r['cost']}"
            )
        return

    if not token_usage_path.exists():
        token_usage_path.parent.mkdir(parents=True, exist_ok=True)
        token_usage_path.write_text(_init_from_template(feature_name))

    lines = token_usage_path.read_text().splitlines()
    try:
        # The file's FIRST table separator belongs to Running Totals
        # (|---|---|), not Per-Command Log -- must anchor the search on
        # the heading first, or a bare "any separator row" search would
        # silently find and insert into the wrong table.
        heading_idx = next(i for i, l in enumerate(lines) if l.strip() == "## Per-Command Log")
        sep_idx = next(
            i for i in range(heading_idx, len(lines))
            if _TABLE_SEP_RE.match(lines[i].strip())
        )
    except StopIteration:
        console.print(f"[red]✗  {token_usage_path} doesn't match the expected template shape -- not touching it[/red]")
        raise SystemExit(1)

    # Find the end of the existing table rows -- new rows are appended
    # there, existing lines (whatever format they're in) are never
    # rewritten, so nothing already logged can be corrupted.
    insert_at = sep_idx + 1
    while insert_at < len(lines) and lines[insert_at].strip().startswith("|"):
        insert_at += 1

    next_num = len(existing_rows) + 1
    formatted_new = []
    for offset, r in enumerate(new_rows):
        formatted_new.append(
            f"| {next_num + offset} | {r['command']} | {r['model']} | {r['input']} | "
            f"{r['output']} | {r['cost']} | {r['source']} | {r['timestamp']} |"
        )
    lines[insert_at:insert_at] = formatted_new

    text = "\n".join(lines) + "\n"
    text = _rewrite_running_totals(text, existing_rows + new_rows)
    token_usage_path.write_text(text)

    for r in new_rows:
        console.print(
            f"[green]✓[/green]  Logged real usage for [cyan]{command_name}[/cyan] — "
            f"[cyan]{r['model']}[/cyan]: in={r['input']} out={r['output']} cost={r['cost']}"
        )
    console.print(f"  {token_usage_path}")
