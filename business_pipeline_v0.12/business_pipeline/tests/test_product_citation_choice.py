"""The citation style a brief asks for: read from the brief, never guessed.

The quiet lanes ask no questions, so the brief is the only place a student can
state the style the paper must use.  Only the styles the product already
carries are recognised, and a name the product cannot render is ignored.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from bp.product import citation_choice, citation_styles  # noqa: E402


class CitationChoiceTest(unittest.TestCase):

    def test_a_brief_that_asks_for_harvard_says_harvard(self):
        self.assertEqual(citation_choice.read("Write the plan in Harvard style."),
                         "harvard")

    def test_a_brief_that_asks_for_apa_says_apa(self):
        self.assertEqual(citation_choice.read("Use APA 7 for the references."), "apa")

    def test_a_brief_that_asks_for_mla_says_mla(self):
        self.assertEqual(citation_choice.read("Cite the evidence in MLA style."), "mla")

    def test_a_style_named_in_passing_is_not_a_choice(self):
        self.assertEqual(citation_choice.read("A brief that mentions Harvard in passing."),
                         "")

    def test_a_brief_with_no_style_states_none(self):
        self.assertEqual(citation_choice.read("A plan for a community kitchen."), "")

    def test_every_name_the_reader_knows_resolves_to_a_supported_style(self):
        for style, name, _self_cue in citation_choice.NAMES:
            self.assertIn(style, citation_styles.STYLES, name)
            self.assertEqual(citation_choice.read("Cite in " + name + "."), style, name)

    def test_a_style_the_product_cannot_render_is_ignored(self):
        self.assertEqual(citation_choice.read("Cite in Turabian style."), "")

    def test_an_empty_brief_states_no_style(self):
        self.assertEqual(citation_choice.read(""), "")
        self.assertEqual(citation_choice.read(None), "")


if __name__ == "__main__":
    unittest.main()
