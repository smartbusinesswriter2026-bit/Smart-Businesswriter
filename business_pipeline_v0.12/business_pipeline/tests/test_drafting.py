"""Drafting arranges retrieved sources; it never invents one."""

import unittest

import sys
sys.path.insert(0, "src")

from bp.product import api, drafting  # noqa: E402


def source(title, abstract, doi=None, authors="Ada Lovelace", year=2024, venue="Journal", url=None):
    return {"title": title, "abstract": abstract, "doi": doi, "authors": authors,
            "year": year, "venue": venue, "url": url}


class PlacementTest(unittest.TestCase):
    def test_swot_places_evidence_in_the_matching_quadrant(self):
        result = drafting.draft("template_swot", [
            source("Strong brand loyalty", "Loyal customers and efficient operations support the brand.", "10.1/s"),
            source("New competitors", "Competition and a price war threaten market share.", "10.1/t"),
            source("Growing demand", "A new market offers an opportunity for expansion.", "10.1/o"),
        ])
        by_dim = {(item["dimension"], item["text"].split(" — ")[0]) for item in result["inputs"]["evidence"]}
        self.assertIn(("S", "Strong brand loyalty"), by_dim)
        self.assertIn(("T", "New competitors"), by_dim)
        self.assertIn(("O", "Growing demand"), by_dim)
        self.assertTrue(all(item["provenance"] == "sourced" for item in result["inputs"]["evidence"]))
        self.assertTrue(all(item["source"] for item in result["inputs"]["evidence"]))
        self.assertEqual(result["n_items"], 3)

    def test_five_forces_places_by_force(self):
        result = drafting.draft("template_five_forces", [
            source("Rivalry intensifies", "Competitors fight for market share.", "10.1/r"),
            source("Suppliers hold power", "Supplier bargaining power raises input costs.", "10.1/s"),
        ])
        forces = {item["force"] for item in result["inputs"]["evidence"]}
        self.assertTrue({"rivalry", "suppliers"} <= forces)
        self.assertEqual(result["inputs"]["ratings"], {})

    def test_pestel_and_canvas_use_named_blocks(self):
        pestel = drafting.draft("template_pestel", [
            source("Inflation rises", "Interest rates and inflation affect demand.", "10.1/e")])
        self.assertTrue(pestel["inputs"]["blocks"]["economic"])
        canvas = drafting.draft("template_business_model_canvas", [
            source("Subscription revenue", "A subscription price supports recurring revenue.", "10.1/b")])
        self.assertTrue(canvas["inputs"]["blocks"]["revenue_streams"])

    def test_an_unmatched_source_is_reported_not_forced(self):
        result = drafting.draft("template_swot", [
            source("Medieval poetry", "A study of verse and metre.", "10.1/x")])
        self.assertEqual(result["n_items"], 0)
        self.assertEqual(len(result["unmatched"]), 1)
        self.assertIn("no dimension", result["unmatched"][0]["reason"])

    def test_duplicates_and_block_caps_are_respected(self):
        same = [source("Competition and market share", "Competitors and a price war.", "10.1/dup") for _ in range(2)]
        many = [source("Competition number %d" % n, "Competitors and a price war.", "10.1/%d" % n) for n in range(8)]
        result = drafting.draft("template_five_forces", same + many)
        rivalry = result["inputs"]["evidence"]
        self.assertEqual(len({item["source"] for item in rivalry}), len(rivalry))
        self.assertLessEqual(len(rivalry), drafting.MAX_PER_BLOCK)

    def test_drafting_is_refused_for_an_uncovered_worksheet(self):
        with self.assertRaises(ValueError):
            drafting.draft("template_vrio", [source("A resource", "A valuable resource.", "10.1/v")])
        with self.assertRaises(ValueError):
            drafting.draft("template_swot", [])

    def test_every_drafted_item_is_a_source_title_and_a_citation(self):
        result = drafting.draft("template_swot", [
            source("Strong brand", "Loyal customers and a strong brand. A second sentence.", "10.1/a",
                   authors="Grace Hopper", year=2023, venue="Journal of Strategy")])
        item = result["inputs"]["evidence"][0]
        self.assertTrue(item["text"].startswith("Strong brand — "))
        self.assertIn("Grace Hopper", item["source"])
        self.assertIn("2023", item["source"])
        self.assertIn("10.1/a", item["source"])
        self.assertIn("no fact or number was invented", result["note"])


class DraftRouteTest(unittest.TestCase):
    def test_the_draft_route_returns_inputs_and_validates(self):
        body = {"template": "template_swot", "sources": [
            source("Strong brand", "Loyal customers and a strong brand.", "10.1/route")]}
        status, payload = api.handle("POST", "/api/cases/worksheets/draft", body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["template"], "template_swot")
        self.assertEqual(payload["n_items"], 1)
        self.assertEqual(api.handle("POST", "/api/cases/worksheets/draft",
                                    {"template": "template_vrio", "sources": body["sources"]})[0], 422)
        self.assertEqual(api.handle("GET", "/api/cases/worksheets/draft")[0], 405)


if __name__ == "__main__":
    unittest.main()
