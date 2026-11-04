"""The manual builder: a table column must never be too narrow for its own words.

A starved column breaks its content mid-word, and a broken code reference is
a defect the reader sees: `sources.py:4` on one line and `96` on the next is
no longer a file reference. These tests pin the width model so the defect
cannot come back.
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BUILDER = os.path.join(os.path.dirname(HERE), "scripts", "build_manual_docx.py")


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_manual_docx", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()


class ColumnWidthTest(unittest.TestCase):

    def test_the_grid_is_exactly_the_text_width(self):
        header = ["Table", "Holds", "Consequence if it is missing"]
        rows = [["documents", "one row per book or article", "nothing can be cited"],
                ["search_log", "every retrieval", "the corpus cannot learn"]]
        widths = builder._column_widths(header, rows)
        self.assertEqual(sum(widths), builder.CONTENT_W)

    def test_a_short_column_is_not_starved_by_a_long_one(self):
        """The identifier column keeps room for its own longest word."""
        header = ["Table", "Holds", "Consequence if it is missing"]
        rows = [["documents", "one row per book or article", "nothing can be cited"],
                ["ingest_log", "an audit of every ingest", "a corrupt file is undetectable"],
                ["search_log", "every retrieval", "the corpus cannot learn"],
                ["seen_sources", "every source a search saw", "a source keeps recurring"]]
        widths = builder._column_widths(header, rows)
        needed = len("seen_sources") * builder.SERIF_CHAR + builder.CELL_MARGIN
        self.assertGreaterEqual(widths[0], needed)

    def test_a_code_token_is_measured_in_the_monospace_font(self):
        """An inline code span is wider than the same characters in serif."""
        header = ["Where"]
        rows = [["`sources.py:496`"]]
        widths = builder._column_widths(header, rows)
        needed = len("sources.py:496") * builder.MONO_CHAR + builder.CELL_MARGIN
        self.assertGreaterEqual(widths[0], needed)

    def test_a_table_that_cannot_fit_every_word_still_fills_the_page(self):
        header = ["A", "B"]
        rows = [["`" + "x" * 120 + "`", "`" + "y" * 120 + "`"]]
        widths = builder._column_widths(header, rows)
        self.assertEqual(sum(widths), builder.CONTENT_W)
        self.assertTrue(all(width > 0 for width in widths))

    def test_a_very_wide_table_does_not_produce_a_negative_column(self):
        header = ["C%d" % index for index in range(20)]
        rows = [["value %d" % index for index in range(20)]]
        widths = builder._column_widths(header, rows)
        self.assertEqual(sum(widths), builder.CONTENT_W)
        self.assertTrue(all(width > 0 for width in widths))


class MarkdownSubsetTest(unittest.TestCase):
    """The builder's markdown subset is what the manuals are written in."""

    def test_inline_runs_keep_code_bold_and_italic_apart(self):
        runs = builder.inline_runs("plain `code` **bold** *italic*")
        kinds = [(text, is_bold, is_italic, is_code) for text, is_bold, is_italic, is_code in runs]
        self.assertIn(("code", False, False, True), kinds)
        self.assertIn(("bold", True, False, False), kinds)
        self.assertIn(("italic", False, True, False), kinds)

    def test_italic_is_recognised_after_a_space(self):
        """`*why*` standing on its own is emphasis, not literal asterisks."""
        runs = builder.inline_runs("the *why*; the *how*")
        kinds = [(text, is_bold, is_italic, is_code) for text, is_bold, is_italic, is_code in runs]
        self.assertIn(("why", False, True, False), kinds)
        self.assertIn(("how", False, True, False), kinds)
        self.assertNotIn("*why*", [text for text, _, _, _ in kinds])

    def test_arithmetic_is_not_italic(self):
        runs = builder.inline_runs("2 * 3 * 4")
        self.assertFalse(any(is_italic for _, _, is_italic, _ in runs))

    def test_bold_wins_over_italic(self):
        runs = builder.inline_runs("**bold**")
        kinds = [(text, is_bold, is_italic, is_code) for text, is_bold, is_italic, is_code in runs]
        self.assertIn(("bold", True, False, False), kinds)

    def test_a_table_is_read_as_a_table(self):
        blocks = builder.parse_markdown(
            "| A | B |\n|---|---|\n| one | two |\n")
        tables = [block for block in blocks if block[0] == "table"]
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0][1], ["A", "B"])
        self.assertEqual(tables[0][2], [["one", "two"]])


if __name__ == "__main__":
    unittest.main()
