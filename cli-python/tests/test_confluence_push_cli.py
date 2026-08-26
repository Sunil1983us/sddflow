# Unit tests for `sdd confluence push --summary` -- pushes a doc's
# .summary.md to its own Confluence page instead of the full .md.
# Run from repo root: pytest cli-python/tests -q
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sdd.commands import confluence


class FakeConfluenceClient:
    def __init__(self, session=None, base_url=None):
        self.pages_by_title: dict[str, dict] = {}
        self.pages_by_id: dict[str, dict] = {}
        self.body_by_title: dict[str, str] = {}
        self._next_id = 1

    def get_page_by_title(self, space_key, title):
        return self.pages_by_title.get(title)

    def get_page_with_body(self, page_id):
        page = dict(self.pages_by_id[page_id])
        page["body"] = {"storage": {"value": self.body_by_title.get(page["title"], "")}}
        return page

    def create_page(self, space_key, title, body_html, parent_id=None):
        page = {
            "id": str(self._next_id),
            "title": title,
            "version": {"number": 1, "by": {"displayName": "sddflow"}, "when": ""},
            "_links": {"webui": f"/pages/{self._next_id}"},
        }
        self._next_id += 1
        self.pages_by_title[title] = page
        self.pages_by_id[page["id"]] = page
        self.body_by_title[title] = body_html
        return page

    def upsert_page(self, space_key, title, body_html, parent_id=None):
        existing = self.get_page_by_title(space_key, title)
        if existing:
            self.body_by_title[title] = body_html
            existing["version"] = {
                "number": existing["version"]["number"] + 1,
                "by": {"displayName": "sddflow"},
                "when": "",
            }
            return existing, False
        return self.create_page(space_key, title, body_html, parent_id), True

    def bump_version_externally(self, title, by="Someone Else", when="2026-01-01"):
        """Test helper: simulate a human editing the page directly in
        Confluence, outside sddflow -- bumps the version the way a real
        Confluence PUT from the web UI would, without touching
        body_by_title (sddflow never sees what they actually changed)."""
        page = self.pages_by_title[title]
        page["version"] = {
            "number": page["version"]["number"] + 1,
            "by": {"displayName": by},
            "when": when,
        }

    def upload_attachment(self, page_id, filename, content, media_type="image/svg+xml"):
        return {"id": f"att-{filename}"}


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    features = tmp_path / ".specify" / "features" / "auth"
    features.mkdir(parents=True)
    (tmp_path / ".specify" / "manifest.yml").write_text(
        yaml.dump({"project": {"name": "Demo", "feature": "auth"}})
    )
    (tmp_path / ".specify" / "integrations.yml").write_text(
        "profile: default\n"
        "confluence:\n"
        "  space_key: ENG\n"
        "  page_map:\n"
        "    brd: '{feature} — Business Requirements'\n"
    )
    (features / "brd.md").write_text("# BRD\n\nFull content.\n")
    (features / "brd.summary.md").write_text("# BRD Summary\n\nShort version.\n")
    return tmp_path


def _patched(cf_client):
    from sdd.utils.atlassian_auth import Profile

    return (
        patch(
            "sdd.commands.confluence.load_confluence_session",
            return_value=(
                Profile(auth_mode="basic", base_url="https://x.atlassian.net"),
                object(),
            ),
        ),
        patch("sdd.commands.confluence.ConfluenceClient", return_value=cf_client),
    )


class TestConfluencePushSummaryFlag:
    def test_summary_flag_pushes_summary_file_to_suffixed_title(self, project, runner):
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(
                confluence.confluence_command, ["push", "--doc", "brd", "--summary"]
            )

        assert result.exit_code == 0, result.output
        assert "auth — Business Requirements — Summary" in cf_client.pages_by_title
        assert (
            "Short version."
            in cf_client.body_by_title["auth — Business Requirements — Summary"]
        )

    def test_without_summary_flag_pushes_full_doc_unsuffixed(self, project, runner):
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(
                confluence.confluence_command, ["push", "--doc", "brd"]
            )

        assert result.exit_code == 0, result.output
        assert "auth — Business Requirements" in cf_client.pages_by_title
        assert "auth — Business Requirements — Summary" not in cf_client.pages_by_title
        assert (
            "Full content." in cf_client.body_by_title["auth — Business Requirements"]
        )

    def test_summary_flag_skips_doc_with_no_summary_file(self, project, runner):
        (project / ".specify" / "features" / "auth" / "brd.summary.md").unlink()
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(
                confluence.confluence_command, ["push", "--doc", "brd", "--summary"]
            )

        assert result.exit_code == 0, result.output
        assert cf_client.pages_by_title == {}
        assert "not found" in result.output

    def test_summary_dry_run_shows_summary_path(self, project, runner):
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(
                confluence.confluence_command,
                ["push", "--doc", "brd", "--summary", "--dry-run"],
            )

        assert result.exit_code == 0, result.output
        assert "brd.summary.md" in result.output
        assert "— Summary" in result.output
        assert cf_client.pages_by_title == {}


class TestConfluencePushIncludesConstitutionByDefault:
    """Regression coverage for a real user-reported bug: a bare `sdd
    confluence push` (no --doc) run right after `create-context` never
    created the Constitution page. Root cause: `_DEFAULT_PAGE_MAP` (the
    code fallback used when integrations.yml has no explicit page_map:
    override -- the common case for anyone who ran the `sdd config
    init` wizard rather than hand-copying integrations.yml.example) had
    no "constitution" entry, so it was never in `keys_to_try` for a bulk
    push -- even though `sdd confluence draft --doc constitution` (and
    `push --doc constitution` explicitly) both worked fine on their own,
    since --doc bypasses page_map entirely."""

    @pytest.fixture()
    def bare_project(self, tmp_path, monkeypatch):
        """No explicit page_map: override in integrations.yml -- this is
        what actually exercises _DEFAULT_PAGE_MAP, unlike this file's
        `project` fixture above (which pins page_map to brd only)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify" / "memory").mkdir(parents=True)
        (tmp_path / ".specify" / "manifest.yml").write_text(
            yaml.dump({"project": {"name": "Demo", "feature": "auth"}})
        )
        (tmp_path / ".specify" / "integrations.yml").write_text(
            "profile: default\nconfluence:\n  space_key: ENG\n"
        )
        (tmp_path / ".specify" / "memory" / "constitution.md").write_text(
            "# Constitution\n\nPart 1: universal rules.\n"
        )
        return tmp_path

    def test_bare_push_creates_the_constitution_page(self, bare_project, runner):
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(confluence.confluence_command, ["push"])

        assert result.exit_code == 0, result.output
        assert "Demo — Constitution" in cf_client.pages_by_title
        assert "universal rules" in cf_client.body_by_title["Demo — Constitution"]

    def test_explicit_doc_constitution_also_works(self, bare_project, runner):
        """Was never broken -- --doc bypasses page_map lookup entirely
        (see _resolve_page_title's early return for "constitution").
        Included here so a future regression in either path is caught
        by the same test class."""
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(
                confluence.confluence_command, ["push", "--doc", "constitution"]
            )

        assert result.exit_code == 0, result.output
        assert "Demo — Constitution" in cf_client.pages_by_title


class TestConfluencePushIncludesContextByDefault:
    """Same bug class as TestConfluencePushIncludesConstitutionByDefault
    above, found while auditing _DEFAULT_PAGE_MAP for this exact gap
    after fixing "constitution": "context" was also missing, so a bare
    `sdd confluence push` never included the context.md page either --
    even though `sdd confluence draft --doc context` (what
    /create-context actually calls) worked fine on its own."""

    @pytest.fixture()
    def bare_project_with_context(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".specify" / "contexts").mkdir(parents=True)
        (tmp_path / ".specify" / "manifest.yml").write_text(
            yaml.dump({"project": {"name": "Demo", "feature": "auth"}})
        )
        (tmp_path / ".specify" / "integrations.yml").write_text(
            "profile: default\nconfluence:\n  space_key: ENG\n"
        )
        (tmp_path / ".specify" / "contexts" / "auth.md").write_text(
            "# System Context — Auth\n\nWhat this service does.\n"
        )
        return tmp_path

    def test_bare_push_creates_the_context_page(
        self, bare_project_with_context, runner
    ):
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(confluence.confluence_command, ["push"])

        assert result.exit_code == 0, result.output
        assert "auth — Context" in cf_client.pages_by_title
        assert "What this service does." in cf_client.body_by_title["auth — Context"]

    def test_explicit_doc_context_also_works(self, bare_project_with_context, runner):
        """Was never broken -- --doc bypasses page_map lookup entirely,
        same as --doc constitution."""
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(
                confluence.confluence_command, ["push", "--doc", "context"]
            )

        assert result.exit_code == 0, result.output
        assert "auth — Context" in cf_client.pages_by_title


class TestConfluencePushDriftDetection:
    """`sdd confluence push` warns and skips a page that was edited
    outside sddflow since the last push, instead of silently clobbering
    it -- see confluence_push_log.py. First push is never flagged
    (nothing tracked yet); a second push with no external edit isn't
    flagged either (the version we recorded still matches)."""

    def _push(self, runner, cf_client, *extra_args):
        p1, p2 = _patched(cf_client)
        with p1, p2:
            return runner.invoke(
                confluence.confluence_command, ["push", "--doc", "brd", *extra_args]
            )

    def test_first_push_is_never_flagged_as_drift(self, project, runner):
        cf_client = FakeConfluenceClient()
        result = self._push(runner, cf_client)
        assert result.exit_code == 0, result.output
        assert "edited by" not in result.output

    def test_repush_with_no_external_edit_is_not_flagged(self, project, runner):
        cf_client = FakeConfluenceClient()
        self._push(runner, cf_client)
        result = self._push(runner, cf_client)
        assert result.exit_code == 0, result.output
        assert "edited by" not in result.output
        assert (
            "Full content." in cf_client.body_by_title["auth — Business Requirements"]
        )

    def test_externally_edited_page_is_flagged_and_push_skipped(self, project, runner):
        cf_client = FakeConfluenceClient()
        self._push(runner, cf_client)
        cf_client.bump_version_externally(
            "auth — Business Requirements", by="Jane Reviewer", when="2026-03-01"
        )
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n\nUpdated content the push would otherwise write.\n"
        )

        result = self._push(runner, cf_client)

        assert "edited by Jane Reviewer on 2026-03-01" in result.output
        assert "skipped" in result.output
        # the push did NOT happen -- body is unchanged from the pre-edit state
        assert (
            "Updated content"
            not in cf_client.body_by_title["auth — Business Requirements"]
        )

    def test_force_overwrite_pushes_despite_external_edit(self, project, runner):
        cf_client = FakeConfluenceClient()
        self._push(runner, cf_client)
        cf_client.bump_version_externally("auth — Business Requirements")
        (project / ".specify" / "features" / "auth" / "brd.md").write_text(
            "# BRD\n\nOverwritten on purpose.\n"
        )

        result = self._push(runner, cf_client, "--force-overwrite")

        assert result.exit_code == 0, result.output
        assert (
            "Overwritten on purpose."
            in cf_client.body_by_title["auth — Business Requirements"]
        )

    def test_push_log_file_is_written(self, project, runner):
        cf_client = FakeConfluenceClient()
        self._push(runner, cf_client)
        log_path = project / "docs" / "confluence" / "push-log.yml"
        assert log_path.exists()
        data = yaml.safe_load(log_path.read_text())
        entry = next(iter(data.values()))
        assert entry["doc"] == "brd"
        assert entry["pushed_version"] == 1


class TestConfluenceVerify:
    def test_verify_with_nothing_tracked_yet(self, project, runner):
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            result = runner.invoke(confluence.confluence_command, ["verify"])
        assert result.exit_code == 0, result.output
        assert "run `sdd confluence push`" in result.output

    def test_verify_reports_up_to_date_after_a_clean_push(self, project, runner):
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            runner.invoke(confluence.confluence_command, ["push", "--doc", "brd"])
            result = runner.invoke(confluence.confluence_command, ["verify"])
        assert result.exit_code == 0, result.output
        assert "up to date" in result.output
        assert "All tracked pages match" in result.output

    def test_verify_reports_drifted_page(self, project, runner):
        cf_client = FakeConfluenceClient()
        p1, p2 = _patched(cf_client)
        with p1, p2:
            runner.invoke(confluence.confluence_command, ["push", "--doc", "brd"])
            cf_client.bump_version_externally(
                "auth — Business Requirements", by="Jane Reviewer", when="2026-03-01"
            )
            result = runner.invoke(confluence.confluence_command, ["verify"])
        assert result.exit_code == 0, result.output
        assert "edited by Jane Reviewer on 2026-03-01" in result.output
        assert "1 page(s) edited outside sddflow" in result.output
