# Unit tests for cf_to_md.py's Confluence-storage -> Markdown converter.
# Regression coverage for the table-flattening bug: cf_to_md() had no
# <table> handling at all, so the generic "strip any remaining HTML
# tags" step at the end of the pipeline stripped <table>/<tr>/<th>/<td>
# with no row or column delimiters inserted anywhere -- every table
# came back as one run-on line of concatenated cell text. Reported by
# a user testing the Confluence review round-trip (draft -> edit in
# Confluence -> `sdd confluence pull`) on a Tech Stack table.
#
# md_to_cf.py (the push direction) had this exact bug class fixed once
# already (see test_md_to_cf.py's TestTables) -- the pull direction
# just never got the equivalent treatment. Run from repo root:
# pytest cli-python/tests -q
from __future__ import annotations

from sdd.utils.cf_to_md import cf_to_md
from sdd.utils.md_to_cf import md_to_storage


class TestTables:
    def test_simple_table_round_trips_as_a_pipe_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        assert "| A | B |" in back
        assert "| 1 | 2 |" in back
        # Regression: previously this was one run-on line with no pipes
        # separating cells at all.
        assert back.count("\n") >= 2


class TestHtmlComments:
    """Regression coverage: an HTML comment surviving push (see
    test_md_to_cf.py's matching TestHtmlComments) still has to survive
    the pull direction too. Before this fix, "Strip any remaining HTML
    tags" near the end of cf_to_md()'s pipeline deleted any <!-- ... -->
    outright -- it matches that step's generic <[^>]+> pattern exactly
    like a real tag would, since the regex has no notion of comments vs.
    tags. Reported by a user: specify-doc.prompt.md's own
    "<!-- security-sign-off: ... -->" marker vanished after a Confluence
    review round-trip (draft -> edit in Confluence -> sdd confluence
    pull)."""

    def test_comment_survives_the_full_round_trip(self):
        md = (
            "# Security Design\n\n"
            "Some content.\n\n"
            "<!-- security-sign-off: pending | reviewer: X | date: 2026-08-08 -->\n\n"
            "## Approvals\n"
        )
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        assert (
            "<!-- security-sign-off: pending | reviewer: X | date: 2026-08-08 -->"
            in back
        )
        assert "Some content." in back
        assert "## Approvals" in back

    def test_comment_is_not_swallowed_by_the_generic_tag_stripper(self):
        """Direct test of the pull-side fix, independent of the push
        side -- feeds storage-format XML with a bare, unescaped comment
        straight in, matching what a real Confluence page returns."""
        html = "<p>Before.</p>\n<!-- a raw comment -->\n<p>After.</p>\n"
        back = cf_to_md(html)
        assert "<!-- a raw comment -->" in back
        assert "Before." in back
        assert "After." in back

    def test_comment_contents_are_not_touched_by_other_conversion_steps(self):
        """A comment containing characters that would otherwise trigger
        other regex passes (asterisks, pipes) must come back verbatim,
        not partially converted."""
        html = "<!-- *not bold* | not | a | table -->"
        back = cf_to_md(html)
        assert back == "<!-- *not bold* | not | a | table -->"


class TestAcTagStripping:
    """Regression coverage for a severe, real data-loss bug: the
    "strip remaining ac:* elements" cleanup step used
    `<ac:[^>]+>.*?</ac:[^>]+>` -- pairing an opening ac: tag with the
    next ac: CLOSING tag of ANY name, not necessarily its own. Reported
    by a user: a page with a local-svg <ac:image> diagram, followed
    later by another unhandled/nested ac: element (e.g. a structured-
    macro's own nested <ac:rich-text-body>), had everything between the
    <ac:image> and that unrelated LATER closing tag silently deleted --
    6 tables and an entire numbered section, in their case. The fix
    requires the closing tag to match the opening tag's own name via a
    backreference."""

    def test_diagram_image_followed_by_unrelated_content_is_preserved(self):
        """The exact reported shape: an <ac:image> diagram, then real
        document content (a table, a heading, a paragraph), then a
        later unhandled macro with its OWN nested ac: element. Before
        the fix, everything between <ac:image> and the nested
        <ac:rich-text-body>'s closing tag vanished."""
        html = (
            '<ac:image ac:width="900">'
            '<ri:attachment ri:filename="diagram-1.svg" />'
            "</ac:image>\n"
            "<table><tbody><tr><td>Table 1 content</td></tr></tbody></table>\n"
            "<h2>3. Enums</h2>\n"
            "<p>RuleVersionStatus values</p>\n"
            '<ac:structured-macro ac:name="info">'
            "<ac:rich-text-body><p>unrelated note</p></ac:rich-text-body>"
            "</ac:structured-macro>\n"
        )
        back = cf_to_md(html)
        assert "Table 1 content" in back
        assert "## 3. Enums" in back
        assert "RuleVersionStatus values" in back
        # The diagram reference itself and the unrelated macro are both
        # correctly stripped (neither has a markdown equivalent) -- just
        # not the real content sitting between them.
        assert "ac:image" not in back
        assert "ac:structured-macro" not in back
        assert "unrelated note" not in back

    def test_diagram_alone_on_a_page_is_stripped_cleanly(self):
        html = (
            "<p>Before the diagram.</p>\n"
            '<ac:image ac:width="900">'
            '<ri:attachment ri:filename="diagram-1.svg" />'
            "</ac:image>\n"
            "<p>After the diagram.</p>\n"
        )
        back = cf_to_md(html)
        assert "Before the diagram." in back
        assert "After the diagram." in back
        assert "ac:image" not in back
        assert "ri:attachment" not in back

    def test_two_separate_macros_each_only_consume_their_own_content(self):
        html = (
            '<ac:structured-macro ac:name="note">'
            "<ac:rich-text-body><p>first macro body</p></ac:rich-text-body>"
            "</ac:structured-macro>\n"
            "<p>Real content between the two macros must survive.</p>\n"
            '<ac:structured-macro ac:name="warning">'
            "<ac:rich-text-body><p>second macro body</p></ac:rich-text-body>"
            "</ac:structured-macro>\n"
        )
        back = cf_to_md(html)
        assert "Real content between the two macros must survive." in back
        assert "first macro body" not in back
        assert "second macro body" not in back

    def test_no_run_on_line_for_a_wide_table(self):
        """The exact shape reported as broken: a multi-column,
        multi-row table must come back as one row per line, not one
        line total."""
        md = (
            "| Layer | Choice | Notes |\n"
            "|---|---|---|\n"
            "| Backend | Python | FastAPI |\n"
            "| DB | Postgres | primary store |\n"
            "| Cache | Redis | session state |\n"
        )
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        lines = [line for line in back.splitlines() if line.strip()]
        # header + separator + 3 body rows == 5 distinct lines, not 1
        assert len(lines) == 5
        assert lines[0].startswith("| Layer")
        assert lines[-1].startswith("| Cache")

    def test_alignment_markers_round_trip(self):
        md = "| L | C | R |\n|:---|:---:|---:|\n| a | b | c |\n"
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        assert "|:---|:---:|---:|" in back

    def test_inline_formatting_inside_cells_round_trips(self):
        md = "| A | B |\n|---|---|\n| `code` | **bold** and [link](https://example.com) |\n"
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        assert "`code`" in back
        assert "**bold**" in back
        assert "[link](https://example.com)" in back

    def test_literal_pipe_in_a_cell_round_trips_escaped(self):
        md = "| A | B |\n|---|---|\n| x | contains a \\| pipe |\n"
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        assert r"contains a \| pipe" in back

    def test_ragged_row_shorter_than_header_is_padded(self):
        """A body row with fewer cells than the header (tolerated on
        the push side by _render_table's pad()) must still produce a
        well-formed row on the way back, not a short/malformed line."""
        md = "| A | B | C |\n|---|---|---|\n| 1 | 2 |\n"
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        body_lines = [
            line
            for line in back.splitlines()
            if line.strip().startswith("|") and "---" not in line and "A" not in line
        ]
        assert len(body_lines) == 1
        assert body_lines[0].count("|") == 4  # | 1 | 2 |  |

    def test_table_followed_by_paragraph_both_survive(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |\n\nA paragraph after the table.\n"
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        assert "| 1 | 2 |" in back
        assert "A paragraph after the table." in back

    def test_heading_before_table_both_survive(self):
        md = "# Tech Stack\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        assert "# Tech Stack" in back
        assert "| 1 | 2 |" in back

    def test_two_tables_in_one_document_both_round_trip(self):
        md = (
            "| A | B |\n|---|---|\n| 1 | 2 |\n\n"
            "Some text between the tables.\n\n"
            "| X | Y |\n|---|---|\n| 9 | 8 |\n"
        )
        storage = md_to_storage(md)[0]
        back = cf_to_md(storage)
        assert "| 1 | 2 |" in back
        assert "| 9 | 8 |" in back
        assert "Some text between the tables." in back

    def test_no_table_in_document_is_unaffected(self):
        """A plain document with no tables should convert exactly as
        before -- the new table regex must not misfire on unrelated
        content."""
        storage = md_to_storage("# Title\n\nJust a paragraph, no tables here.\n")[0]
        back = cf_to_md(storage)
        assert "# Title" in back
        assert "Just a paragraph, no tables here." in back
        assert "|" not in back
