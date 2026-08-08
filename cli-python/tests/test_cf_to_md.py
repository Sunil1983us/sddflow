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
