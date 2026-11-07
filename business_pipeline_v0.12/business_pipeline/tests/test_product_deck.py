"""A deck is a sequence of claims, and it ships as a real .pptx.

The package is checked the way PowerPoint reads it: every part declared, every
relationship resolving, every XML well-formed, and the bytes stable.  A figure
reaches a slide as a picture when a rasterizer exists, and as its stored values
when one does not - never as a broken image.
"""

import base64
import io
import os
import posixpath
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, "src")

from bp.product import deck, renderers  # noqa: E402

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

FIGURE = {"id": "fig_abc123", "caption": "Recorded results", "note": "Source: stored artifacts",
          "asset": {"png": PNG_1X1}, "rows": [("Net present value", "50.00")]}

BARE = {"id": "fig_abc123", "caption": "Recorded results", "note": "",
        "asset": {"png": None}, "rows": [("Net present value", "50.00")]}


def a_deck(**overrides):
    base = {"format": "deck-format", "title": "A deck", "slides": [
        deck.slide("title", claim="A deck", subtitle="Draft"),
        deck.slide("claim", claim="Revenue grew on renewals", bullets=["Support"]),
        deck.slide("figure", claim="Recorded results", figure="fig_abc123"),
    ]}
    base["format"] = deck.DECK_FORMAT
    base.update(overrides)
    return base


def parts(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


class GrammarTest(unittest.TestCase):

    def test_a_content_slide_needs_a_claim(self):
        with self.assertRaises(deck.DeckError):
            deck.slide("claim", bullets=["No claim here"])

    def test_a_title_slide_may_stand_without_a_claim(self):
        item = deck.slide("title", subtitle="Draft")
        self.assertEqual(item["layout"], "title")

    def test_an_unknown_layout_is_refused(self):
        with self.assertRaises(deck.DeckError):
            deck.slide("poster", claim="A claim")

    def test_a_deck_must_name_a_figure_it_holds(self):
        bad = a_deck()
        bad["slides"][2]["figure"] = "fig_missing"
        with self.assertRaises(deck.DeckError):
            deck.validate(bad, [FIGURE])


class PackageTest(unittest.TestCase):

    def test_the_deck_is_a_pptx_with_every_required_part(self):
        data = deck.render(a_deck(), {"fig_abc123": FIGURE})
        names = parts(data)
        for name in ("[Content_Types].xml", "_rels/.rels",
                     "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels",
                     "ppt/slideMasters/slideMaster1.xml",
                     "ppt/slideLayouts/slideLayout1.xml",
                     "ppt/theme/theme1.xml",
                     "ppt/slides/slide1.xml", "ppt/slides/slide2.xml",
                     "ppt/slides/slide3.xml"):
            self.assertIn(name, names)

    def test_every_xml_part_is_well_formed(self):
        data = deck.render(a_deck(), {"fig_abc123": FIGURE})
        for name, body in parts(data).items():
            if name.endswith(".xml") or name.endswith(".rels"):
                ET.fromstring(body)

    def test_every_relationship_resolves_to_a_part(self):
        data = deck.render(a_deck(), {"fig_abc123": FIGURE})
        names = set(parts(data))
        for name, body in parts(data).items():
            if not name.endswith(".rels"):
                continue
            base = posixpath.dirname(posixpath.dirname(name))
            root = ET.fromstring(body)
            for relationship in root:
                target = relationship.get("Target")
                resolved = posixpath.normpath(posixpath.join(base, target))
                self.assertIn(resolved, names, "%s -> %s" % (name, target))

    def test_every_part_is_declared_in_the_content_types(self):
        data = deck.render(a_deck(), {"fig_abc123": FIGURE})
        declared = parts(data)["[Content_Types].xml"].decode()
        for name in parts(data):
            if name == "[Content_Types].xml" or name.endswith(".rels"):
                continue
            if name.endswith(".png"):
                self.assertIn('Extension="png"', declared)
            else:
                self.assertIn("/" + name, declared)

    def test_the_bytes_are_stable(self):
        one = deck.render(a_deck(), {"fig_abc123": FIGURE})
        two = deck.render(a_deck(), {"fig_abc123": FIGURE})
        self.assertEqual(one, two)

    def test_a_figure_reaches_the_slide_as_a_picture(self):
        data = deck.render(a_deck(), {"fig_abc123": FIGURE})
        names = parts(data)
        self.assertIn("ppt/media/image1.png", names)
        slide = names["ppt/slides/slide3.xml"]
        self.assertIn(b"<p:pic>", slide)
        self.assertIn(b'r:embed="rId2"', slide)
        rels = names["ppt/slides/_rels/slide3.xml.rels"]
        self.assertIn(b"../media/image1.png", rels)

    def test_without_a_rasterizer_the_figure_prints_its_stored_values(self):
        data = deck.render(a_deck(), {"fig_abc123": BARE})
        names = parts(data)
        self.assertNotIn("ppt/media/image1.png", names)
        slide = names["ppt/slides/slide3.xml"]
        self.assertNotIn(b"<p:pic>", slide)
        self.assertIn(b"50.00", slide)


class FromSectionsTest(unittest.TestCase):

    def test_a_heading_with_no_sentence_becomes_a_section_slide(self):
        sections = [{"heading": "Method", "level": 1, "lines": []}]
        built = deck.from_sections(sections, "A paper")
        self.assertEqual(built["slides"][1]["layout"], "section")

    def test_a_heading_with_a_sentence_becomes_a_claim_slide(self):
        sections = [{"heading": "Results", "level": 1, "lines": ["Revenue grew."]}]
        built = deck.from_sections(sections, "A paper")
        self.assertEqual(built["slides"][1]["layout"], "claim")
        self.assertEqual(built["slides"][1]["bullets"], ["Revenue grew."])

    def test_a_section_carrying_a_figure_becomes_a_figure_slide(self):
        sections = [{"heading": "Results", "level": 1, "lines": [],
                     "figure": {"id": "fig_abc123", "note": "Source: stored artifacts"}}]
        built = deck.from_sections(sections, "A paper")
        self.assertEqual(built["slides"][1]["layout"], "figure")
        self.assertEqual(built["slides"][1]["figure"], "fig_abc123")


class NotesTest(unittest.TestCase):

    def _with_note(self):
        built = a_deck()
        built["slides"][1]["notes"] = "Say this aloud."
        return built

    def test_a_note_becomes_a_notes_slide(self):
        names = parts(deck.render(self._with_note(), {"fig_abc123": FIGURE}))
        self.assertIn("ppt/notesSlides/notesSlide1.xml", names)
        self.assertIn("ppt/notesMasters/notesMaster1.xml", names)
        self.assertIn(b"Say this aloud.", names["ppt/notesSlides/notesSlide1.xml"])
        self.assertIn(b"notesSlide1.xml", names["ppt/slides/_rels/slide2.xml.rels"])

    def test_every_notes_relationship_resolves(self):
        names = parts(deck.render(self._with_note(), {"fig_abc123": FIGURE}))
        for name, body in names.items():
            if not name.endswith(".rels"):
                continue
            base = posixpath.dirname(posixpath.dirname(name))
            for relationship in ET.fromstring(body):
                resolved = posixpath.normpath(posixpath.join(base, relationship.get("Target")))
                self.assertIn(resolved, names, "%s -> %s" % (name, relationship.get("Target")))

    def test_a_deck_without_notes_carries_no_notes_parts(self):
        names = parts(deck.render(a_deck(), {"fig_abc123": FIGURE}))
        self.assertFalse([name for name in names if "notes" in name])

    def test_a_slide_fades_by_default_and_can_opt_out(self):
        self.assertIn(b"<p:transition><p:fade/></p:transition>",
                      parts(deck.render(a_deck(), {"fig_abc123": FIGURE}))["ppt/slides/slide2.xml"])
        built = a_deck()
        built["slides"][1]["transition"] = "none"
        self.assertNotIn(b"<p:transition>",
                         parts(deck.render(built, {"fig_abc123": FIGURE}))["ppt/slides/slide2.xml"])

    def test_an_unknown_transition_is_refused(self):
        with self.assertRaises(deck.DeckError):
            deck.slide("claim", claim="A claim", transition="wipe")


class DeliverableTest(unittest.TestCase):

    def test_the_presentation_profile_writes_a_real_pptx(self):
        import shutil
        import tempfile
        from bp.product import deliverables
        import product_fixtures

        root = tempfile.mkdtemp()
        try:
            path = os.path.join(root, "deck.pptx")
            result = deliverables.write_export(
                product_fixtures.make_bundle(), "presentation", "pptx", path)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(result["format"], "pptx")
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
            self.assertIn("ppt/presentation.xml", names)
            self.assertIn("ppt/slides/slide1.xml", names)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_presentation_is_charged_at_its_declared_price(self):
        from bp.product import credits
        self.assertEqual(credits.PRICE_TABLE["pptx"], 3)


if __name__ == "__main__":
    unittest.main()

class PitchTest(unittest.TestCase):
    """A pitch deck is the paper's own sentences, reordered, with notes."""

    SECTIONS = [
        {"heading": "Introduction", "level": 1,
         "lines": ["The Saudi grocery market is crowded. A second branch must earn its place."]},
        {"heading": "Market Analysis", "level": 1,
         "lines": ["Demand is growing in the eastern district.", "Two rivals opened nearby."]},
        {"heading": "Financial Feasibility", "level": 1,
         "lines": ["The branch breaks even in the second year."],
         "figure": {"id": "fig_abc123", "kind": "chart", "caption": "Break-even",
                    "asset": {"png": PNG_1X1}, "rows": [("Break-even", "100")]}},
        {"heading": "Limitations", "level": 1,
         "lines": ["The estimate assumes a constant price."]},
        {"heading": "Conclusion", "level": 1,
         "lines": ["We recommend proceeding with the branch."]},
    ]

    def test_the_pitch_follows_the_pitch_order(self):
        built = deck.from_paper(self.SECTIONS, "A second branch")
        self.assertEqual(built["slides"][0]["layout"], "title")
        self.assertEqual([slide["claim"] for slide in built["slides"][1:]],
                         ["The Saudi grocery market is crowded.",
                          "Demand is growing in the eastern district.",
                          "The branch breaks even in the second year.",
                          "The estimate assumes a constant price.",
                          "We recommend proceeding with the branch."])

    def test_speaker_notes_are_the_section_text(self):
        built = deck.from_paper(self.SECTIONS, "A second branch")
        self.assertIn("A second branch must earn its place.", built["slides"][1]["notes"])
        self.assertIn("Two rivals opened nearby.", built["slides"][2]["notes"])

    def test_a_section_with_a_figure_becomes_a_figure_slide(self):
        built = deck.from_paper(self.SECTIONS, "A second branch")
        figure_slides = [slide for slide in built["slides"] if slide["layout"] == "figure"]
        self.assertEqual(len(figure_slides), 1)
        self.assertEqual(figure_slides[0]["figure"], "fig_abc123")

    def test_a_pitch_reaches_powerpoint_with_notes(self):
        built = deck.from_paper(self.SECTIONS, "A second branch")
        data = deck.render(built, {"fig_abc123": self.SECTIONS[2]["figure"]})
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
        self.assertTrue([name for name in names if name.startswith("ppt/notesSlides/")], names)
        self.assertIn("ppt/media/image1.png", names)

class PdfTest(unittest.TestCase):
    """The deck prints as a PDF through the Chrome kaleido carries."""

    @unittest.skipUnless(renderers.chrome(), "no Chrome on this machine")
    def test_the_pitch_prints_as_a_pdf(self):
        built = deck.from_paper(PitchTest.SECTIONS, "A second branch")
        data = deck.pdf_bytes(built, {"fig_abc123": PitchTest.SECTIONS[2]["figure"]})
        self.assertIsNotNone(data)
        self.assertTrue(data.startswith(b"%PDF-"))

    def test_the_html_pages_carry_every_slide_and_no_notes(self):
        built = deck.from_paper(PitchTest.SECTIONS, "A second branch")
        markup = deck.html_document(built, {"fig_abc123": PitchTest.SECTIONS[2]["figure"]})
        self.assertEqual(markup.count('class="slide'), len(built["slides"]))
        self.assertIn("The Saudi grocery market is crowded.", markup)
        self.assertNotIn("Speaker notes", markup)  # the PDF is for the audience, not the presenter
