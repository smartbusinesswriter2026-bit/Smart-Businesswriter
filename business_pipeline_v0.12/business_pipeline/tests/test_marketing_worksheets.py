"""The five marketing worksheets added in B-131.

These are T4 structure-and-evidence worksheets: the student supplies every item, the
system places it, reproduces it verbatim, names the gaps and derives no score,
ranking, average or verdict.  The tests exercise the shared canvas and matrix
builders through the five new kinds.
"""

import copy
import sys
import unittest

sys.path.insert(0, "src")
from bp import templates as T, registry as R  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402
from bp.product import subjects  # noqa: E402

NEW = {
    "template_customer_journey": ("MKT-04", "matrix"),
    "template_kano": ("MKT-06", "canvas"),
    "template_paid_media_plan": ("MKT-15", "canvas"),
    "template_measurement_plan": ("MKT-18", "canvas"),
}
#: A worksheet that is registered and complete but **not offered** on the page.
#: SERVQUAL used to be filed as both a canvas and a grid, so the page gave it the wrong
#: editor; the owner hid the tile until that was repaired (B-198).  The form is repaired
#: now (D-MKT-07) and the tile stays hidden until the owner unhides it, so what is
#: asserted below is the repaired single form plus the hiding: hiding it cannot hide a
#: broken registration, and the double declaration cannot come back unnoticed.
HIDDEN = {
    "template_servqual": ("MKT-07", "matrix"),
}
yes = lambda _s: True


def example(kind):
    return copy.deepcopy(T.EXAMPLES[kind])


class Registration(unittest.TestCase):
    def test_every_new_worksheet_is_t4_and_links_its_record(self):
        for kind, (rid, form) in NEW.items():
            template = T.TEMPLATES[kind]
            self.assertEqual(template["tier"], "T4", kind)
            self.assertEqual(template["registry_ids"], [rid], kind)
            self.assertEqual(R.get(rid)["template"], kind, rid)
            self.assertEqual(R.get(rid)["form"], "worksheet", rid)
            self.assertEqual(T.describe(kind)["form_kind"], form, kind)

    def test_every_new_worksheet_declares_limits_defaults_and_checks(self):
        for kind in NEW:
            described = T.describe(kind)
            self.assertTrue(described["intended_use"], kind)
            self.assertTrue(described["unsupported_use"], kind)
            self.assertTrue(described["limitations"], kind)
            self.assertTrue(described["defaults"], kind)
            self.assertEqual(len(described["planned_checks"]), 8 if kind in T.MATRIX_META else 9, kind)

    def test_the_marketing_page_offers_five_worksheets_and_no_duplicate_rows(self):
        page = subjects.detail("marketing")
        offered = [w["catalogue_id"] for w in page["worksheets"]]
        self.assertEqual(offered, ["MKT-02", "MKT-04", "MKT-06", "MKT-15", "MKT-18"])
        self.assertFalse({row["id"] for row in page["records"]} & set(offered))

    def test_a_hidden_worksheet_stays_registered_and_is_not_offered(self):
        """B-198 and D-MKT-07: one declared form, and the tile still hidden."""
        for kind, (rid, form) in HIDDEN.items():
            template = T.TEMPLATES[kind]
            self.assertEqual(template["tier"], "T4", kind)
            self.assertEqual(template["registry_ids"], [rid], kind)
            self.assertIn(kind, T.MATRIX_META, "the worksheet is a grid by declaration")
            self.assertNotIn(kind, T.CANVAS_BLOCKS,
                             "a block may declare exactly one form: the canvas entry was the "
                             "double declaration that handed the page a canvas editor (D-MKT-07)")
            self.assertEqual(T.describe(kind)["form_kind"], form,
                             "the page must be handed a grid editor; the tile is hidden by "
                             "B-198, not by a wrong form declaration")
            self.assertEqual(T.describe(kind)["blocks"], [],
                             "a declared grid exposes no canvas blocks to the page")
            self.assertNotIn(rid, [w["catalogue_id"] for w in subjects.detail("marketing")["worksheets"]],
                             "a hidden worksheet must not be offered")

    def test_every_offered_worksheet_opens_the_form_its_example_is_written_for(self):
        """The trap for the canvas/grid confusion: a grid must not open a canvas form."""
        page = subjects.detail("marketing")
        for sheet in page["worksheets"]:
            kind = sheet["template"]
            inputs = (T.EXAMPLES.get(kind) or {}).get("inputs") or {}
            shape = "canvas" if "blocks" in inputs else ("matrix" if "cells" in inputs else None)
            if shape:
                self.assertEqual(T.describe(kind)["form_kind"], shape,
                                 (sheet["catalogue_id"], sorted(inputs)))

    def test_each_worksheet_is_offered_on_the_page_that_owns_its_record(self):
        for rid in NEW.values():
            owner = [d["id"] for d in subjects.SUBJECT_DEFS if rid[0] in d["worksheets"]]
            self.assertTrue(owner, rid[0])


class ExampleRuns(unittest.TestCase):
    def test_every_example_passes_its_own_checks(self):
        for kind in NEW:
            out = T.run_template(kind, example(kind)["inputs"])
            failed = [name for name, ok in out["results"] if not ok]
            self.assertEqual(failed, [], kind)
            self.assertEqual([n for n, _ in out["results"]], list(T.TEMPLATES[kind]["test_names"]), kind)

    def test_the_listing_reproduces_a_supplied_line_verbatim(self):
        for kind in NEW:
            out = T.run_template(kind, example(kind)["inputs"])
            first = T.EXAMPLES[kind]["inputs"]
            if kind in T.CANVAS_BLOCKS:
                text = next(item["text"] for items in first["blocks"].values() for item in items)
            else:
                text = first["cells"][0]["text"]
            self.assertIn(text, out["listing"], kind)

    def test_the_gaps_are_counted_not_filled(self):
        kano = T.run_template("template_kano", example("template_kano")["inputs"])
        self.assertEqual(kano["counts"]["n_blocks_empty"], 2)
        journey = T.run_template("template_customer_journey", example("template_customer_journey")["inputs"])
        self.assertGreater(journey["counts"]["n_empty_cells"], 0)

    def test_no_new_worksheet_can_return_a_score_or_verdict(self):
        for kind in NEW:
            out = T.run_template(kind, example(kind)["inputs"])
            for forbidden in ("score", "overall", "ranking", "probability", "verdict", "recommend"):
                self.assertNotIn(forbidden, out["analysis"], (kind, forbidden))

    def test_each_worksheet_delivers_through_the_pipeline(self):
        for kind in NEW:
            body = example(kind)
            delivery = Pipeline().run({**body, "objective": body["objective"]}, yes)
            self.assertEqual(delivery.status, "delivered", kind)
            self.assertTrue(delivery.report.strip(), kind)
            self.assertNotIn("{{", delivery.report, kind)


class Refusals(unittest.TestCase):
    def build(self, kind, inputs):
        return T.TEMPLATES[kind]["build"](inputs)

    def test_an_item_without_text_is_refused(self):
        body = example("template_kano")["inputs"]
        body["blocks"]["must_be"] = [{"provenance": "user"}]
        with self.assertRaises(ValueError):
            self.build("template_kano", body)

    def test_sourced_evidence_without_a_source_is_refused(self):
        body = example("template_measurement_plan")["inputs"]
        body["blocks"]["metrics"] = [{"text": "Meals per day", "provenance": "sourced"}]
        with self.assertRaises(ValueError):
            self.build("template_measurement_plan", body)

    def test_an_unknown_block_is_refused(self):
        body = example("template_paid_media_plan")["inputs"]
        body["blocks"]["invented_block"] = [{"text": "x", "provenance": "user"}]
        with self.assertRaises(ValueError):
            self.build("template_paid_media_plan", body)

    def test_a_cell_that_cites_an_unknown_row_is_refused(self):
        body = example("template_customer_journey")["inputs"]
        body["cells"].append({"row": "T99", "column": "S1", "text": "x", "provenance": "user"})
        with self.assertRaises(ValueError):
            self.build("template_customer_journey", body)

    def test_too_few_journey_touchpoints_are_refused(self):
        body = example("template_customer_journey")["inputs"]
        body["rows"] = body["rows"][:2]
        with self.assertRaises(ValueError):
            self.build("template_customer_journey", body)


if __name__ == "__main__":
    unittest.main()
