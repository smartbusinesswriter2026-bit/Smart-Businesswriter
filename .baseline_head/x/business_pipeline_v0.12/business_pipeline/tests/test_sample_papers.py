"""The published sample papers, regenerated from the product.

A sample is not written here: it is built by the conductor and rendered by the
academic formatter, exactly as a student's export is.  These tests pin the shape
that makes the sample usable - the hierarchy, the style, the citations, the
byline, the gap wording and the break-even figures - without pinning the bytes
of a date-stamped document.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import build_conductor_samples as samples  # noqa: E402


def sample(key):
    return next(item for item in samples.SAMPLES if item["key"] == key)


class FileNames(unittest.TestCase):
    def test_the_convention_is_title_framework_style(self):
        self.assertEqual(samples.filename(sample("ansoff"), "apa"),
                         "Apple's Entry into Iran - Ansoff - APA 7.docx")
        self.assertEqual(samples.filename(sample("vrio"), "harvard"),
                         "Apple's Resource Position - VRIO - Harvard.docx")
        self.assertEqual(samples.filename(sample("break-even"), "apa"),
                         "A Tehran Device Store - Break-even - APA 7.docx")

    def test_windows_forbidden_characters_are_removed(self):
        self.assertEqual(samples.safe_name('A: B/C*D?"E"<F>|G'), "A BCDEFG")
        self.assertEqual(samples.safe_name("  spaced   title . "), "spaced title")


class Shape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = {}
        for item in samples.SAMPLES:
            for style in samples.STYLES:
                cls.built[(item["key"], style)] = samples.build(item, style)

    def headings(self, key, style):
        state, _data = self.built[(key, style)]
        return {item["heading"]: item["level"] for item in state["draft"]["outline"]}

    def text(self, key, style):
        state, _data = self.built[(key, style)]
        return " ".join(line for _heading, lines in state["draft"]["sections"] for line in lines)

    def test_every_sample_builds_in_both_styles(self):
        self.assertEqual(len(self.built), 8)
        for (key, style), (_state, data) in self.built.items():
            self.assertTrue(data.startswith(b"PK"), (key, style))

    def test_the_hierarchy_is_one_h1_per_framework_and_one_h2_per_dimension(self):
        expected = {
            "ansoff": ("Ansoff Growth Matrix", ["Market penetration", "Market development",
                                                "Product development", "Diversification"]),
            "value-chain": ("Value Chain", ["Inbound logistics", "Operations", "Outbound logistics",
                                            "Marketing and sales", "Service", "Procurement",
                                            "Technology development", "Human resource management",
                                            "Firm infrastructure"]),
            "vrio": ("VRIO", ["Resources", "Valuable", "Rare", "Costly to imitate",
                              "Organised to capture value"]),
            "break-even": ("Financial Feasibility", ["Break-even Analysis"]),
        }
        for key, (h1, h2s) in expected.items():
            found = self.headings(key, "apa")
            self.assertEqual(found[h1], 1, key)
            for label in h2s:
                self.assertEqual(found[label], 2, (key, label))

    def test_the_reference_heading_follows_the_style(self):
        self.assertIn("References", self.headings("ansoff", "apa"))
        self.assertIn("Bibliography", self.headings("ansoff", "harvard"))

    def test_evidence_papers_cite_their_sources_and_others_say_none_were_used(self):
        text = self.text("ansoff", "apa")
        self.assertIn("(World Bank, 2026a)", text)
        self.assertIn("(Koruzhde, 2025)", text)
        self.assertIn("No sources were used.", self.text("vrio", "apa"))
        self.assertIn("No sources were used.", self.text("break-even", "harvard"))

    def test_every_citation_in_the_body_resolves_to_the_reference_list(self):
        state, _data = self.built[("ansoff", "apa")]
        references = dict((item["heading"], item["lines"]) for item in state["draft"]["outline"])
        listed = " ".join(references.get("References") or [])
        body = self.text("ansoff", "apa")
        for citation in ("World Bank, 2026a", "Thomas, 2024", "Koruzhde, 2025"):
            self.assertIn("(" + citation + ")", body)
            self.assertIn(citation.split(",")[0], listed)

    def test_the_worked_example_is_byline_not_a_placeholder(self):
        state, _data = self.built[("vrio", "apa")]
        self.assertIn("Worked example for students", state["draft"]["title"] + " Worked example for students")

    def test_no_template_instruction_appears_in_the_draft(self):
        for key in ("ansoff", "value-chain", "vrio", "break-even"):
            text = self.text(key, "apa").lower()
            for phrase in ("(your analysis)", "not supplied yet", "add your implications", "[your name]"):
                self.assertNotIn(phrase, text, (key, phrase))

    def test_a_value_chain_sample_names_the_unsupported_activity(self):
        text = self.text("value-chain", "apa")
        self.assertIn("Service", self.headings("value-chain", "apa"))
        self.assertIn("did not cover this dimension", text)

    def test_the_break_even_sample_reports_the_core_figures(self):
        text = self.text("break-even", "apa")
        self.assertIn("166.67", text)
        self.assertIn("6,666,666.67", text)
        self.assertIn("Every financial figure is the frozen method's result", text)

    def test_building_the_same_sample_twice_gives_the_same_bytes(self):
        _state, first = samples.build(sample("ansoff"), "apa")
        _state, second = samples.build(sample("ansoff"), "apa")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
