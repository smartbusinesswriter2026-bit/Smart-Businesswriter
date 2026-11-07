"""Word count replaces the short/mid/long bands.

The rules these tests protect:

- the student states a body-word target; the three band names are legacy;
- the body excludes the title page, the title, the headings and the reference
  list (the writer has no footnotes part, so none are emitted);
- the allowance is two-sided and reported, never an export gate;
- one repair pass adds whole analytical sections when short, or removes only
  sections it added when long, and then stops;
- a target the record cannot support is reported honestly, not padded.
"""

import unittest

from bp.product import completion, framework_profiles, length


class WordCountTest(unittest.TestCase):
    def test_a_raw_number_is_the_target(self):
        self.assertEqual(length.check("2400"), 2400)
        self.assertEqual(length.check(" 2,400 "), 2400)

    def test_a_legacy_band_name_still_resolves(self):
        self.assertEqual(length.check("short"), 600)
        self.assertEqual(length.check("mid"), 1200)
        self.assertEqual(length.check("long"), 2500)

    def test_below_the_floor_is_refused_with_the_reason(self):
        with self.assertRaises(ValueError) as raised:
            length.check("300")
        self.assertIn("600", str(raised.exception))

    def test_above_the_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            length.check(str(length.MAX_WORDS + 1))

    def test_body_words_excludes_headings_and_references(self):
        sections = [
            {"heading": "Introduction", "level": 1, "lines": ["one two three"]},
            {"heading": "Conclusion", "level": 1, "lines": ["four five"]},
            {"heading": "References", "level": 1, "lines": ["A source title " * 20]},
        ]
        self.assertEqual(length.body_words(sections), 5)

    def test_the_allowance_is_two_sided(self):
        low = length.report(2500, 2242)
        self.assertFalse(low["met"])
        self.assertEqual(low["range"], [2250, 2750])
        self.assertIn("below", low["note"])
        high = length.report(600, 965)
        self.assertFalse(high["met"])
        self.assertIn("above", high["note"])
        inside = length.report(2500, 2379)
        self.assertTrue(inside["met"])

    def test_a_zero_target_has_no_verdict(self):
        report = length.report(0, 800)
        self.assertIsNone(report["met"])
        self.assertIsNone(report["range"])


def _completion_result():
    profile = framework_profiles.profile_for("template_pestel")
    blocks = []
    for block in profile["blocks"]:
        blocks.append({
            "key": block["key"], "label": block["label"], "gap": None,
            "items": [{"text": ("Evidence about %s in the case. " % block["label"]) * 6,
                       "provenance": "user"},
                      {"text": ("A second observation about %s. " % block["label"]) * 6,
                       "provenance": "user"}],
        })
    return {"template": "template_pestel",
            "instruction": "A grocery chain is deciding whether to acquire a cold-chain provider.",
            "blocks": blocks}


class CompletionLengthTest(unittest.TestCase):
    def test_a_numeric_target_is_measured_on_the_body(self):
        report = completion.draft(_completion_result(), "apa", "draft", "mid", target_words=2500)
        self.assertEqual(report["target_words"], 2500)
        self.assertEqual(report["word_target"]["target"], 2500)
        self.assertNotIn("References", " ".join(
            line for section in report["sections"] if section["heading"] == "References"
            for line in section["lines"]))
        self.assertGreater(report["words"], 0)

    def test_one_pass_adds_whole_sections_when_short(self):
        report = completion.draft(_completion_result(), "apa", "draft", "mid", target_words=2500)
        optional = [section["heading"] for section in report["sections"] if section.get("length_optional")]
        self.assertTrue(optional, "a short body gains analytical sections")
        self.assertTrue(report["word_target"]["met"] or report["length_adjustment"],
                        "the pass runs and the result is reported")
        headings = [section["heading"] for section in report["sections"]]
        self.assertEqual(len(headings), len(set(headings)), "the pass adds no duplicate heading")
        self.assertLess(headings.index("Conclusion"), headings.index("References"),
                        "the conclusion stays before the reference list")
        for section in report["sections"]:
            if section.get("length_optional"):
                self.assertTrue(section.get("lines"), "an added section carries prose, not a heading alone")

    def test_a_target_the_record_cannot_support_is_reported_not_padded(self):
        report = completion.draft(_completion_result(), "apa", "draft", "mid", target_words=5000)
        self.assertFalse(report["word_target"]["met"])
        self.assertIn("strived for, not guaranteed", report["word_target"]["note"])
        self.assertIsNotNone(report["length_adjustment"])
        # The pass is bounded: it added the sections the record supports and
        # stopped, rather than repeating prose to reach 5,000.
        self.assertLess(report["words"], 5000)

    def test_a_legacy_call_is_unchanged(self):
        report = completion.draft(_completion_result(), "apa", "draft", "mid")
        self.assertIsNone(report["length_adjustment"])
        self.assertEqual(report["word_target"]["target"], 1300)


if __name__ == "__main__":
    unittest.main()
