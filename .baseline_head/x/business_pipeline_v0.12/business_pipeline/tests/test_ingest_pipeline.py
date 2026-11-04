"""A dataset read from a file reaches a frozen method, and says where it came from (B-071).

`bp.ingest.to_method_inputs` turns named columns into a method request.  This file proves the
whole chain rather than the mapping alone: the same numbers a student's spreadsheet holds produce
the same figure as typing them, the specification records the input as `sourced` rather than
`user`, and the file's name and hash travel with it so the paper can be re-run from the file.

Nothing here invents data: every number is the fixture's own, and every expectation is hand
arithmetic or the method's own contract.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import ingest                                            # noqa: E402
from bp.methods import LIBRARY                                   # noqa: E402
from bp.orchestrator import Pipeline                             # noqa: E402

SCORES = b"name,score,when\nAda,10,2026-01-05\nBo,12.5,\nCy,9,2026-02-01\n"
WIDE = b"a,b\n10,14\n12,15\n11,16\n"
MIXED = b"name,score\nAda,10\nBo,twelve\n"


def session_request(mapped, objective="A dataset from my own file"):
    """The request a page would build from a mapped ingest result."""
    return {"objective": objective, "method": mapped["method"], "inputs": mapped["inputs"],
            "provenance": mapped["input_provenance"], "data_manifest": mapped["data_manifest"]}


class TheChainTest(unittest.TestCase):
    def test_a_mapped_column_produces_the_same_figure_as_typing_it(self):
        table = ingest.read_table("scores.csv", SCORES)
        mapped = ingest.to_method_inputs(table, "descriptive_stats", {"values": "score"})
        delivery = Pipeline().run(session_request(mapped), lambda spec: True)
        self.assertEqual(delivery.status, "delivered", delivery.blocked_reason)
        mean = sum(value for value in (10, 12.5, 9)) / 3.0
        self.assertIn("%.2f" % mean, delivery.report,
                      "the delivered paper must carry the same mean as hand arithmetic")
        self.assertEqual(float(LIBRARY["descriptive_stats"].impl(mapped["inputs"])["mean"]),
                         round(mean, 10))

    def test_the_specification_records_the_input_as_sourced_not_typed(self):
        table = ingest.read_table("scores.csv", SCORES)
        mapped = ingest.to_method_inputs(table, "descriptive_stats", {"values": "score"})
        spec = Pipeline().start(session_request(mapped))
        self.assertEqual(spec.inputs["values"]["provenance"], "sourced",
                         "a value read from a file must not be recorded as one the student typed")
        self.assertEqual(spec.data_manifest[0]["file"], "scores.csv")
        self.assertEqual(spec.data_manifest[0]["sha256"], table["sha256"])

    def test_two_columns_reach_a_column_map_method(self):
        table = ingest.read_table("wide.csv", WIDE)
        mapped = ingest.to_method_inputs(table, "welch_t", {"groups": {"a": "a", "b": "b"}})
        self.assertEqual(mapped["inputs"]["groups"], {"a": ["10", "12", "11"], "b": ["14", "15", "16"]})
        delivery = Pipeline().run(session_request(mapped), lambda spec: True)
        self.assertEqual(delivery.status, "delivered", delivery.blocked_reason)
        self.assertEqual(sorted(mapped["data_manifest"][0]["columns"]), ["a", "b"])

    def test_the_manifest_names_only_the_columns_that_were_used(self):
        table = ingest.read_table("scores.csv", SCORES)
        mapped = ingest.to_method_inputs(table, "descriptive_stats", {"values": "score"})
        self.assertEqual(mapped["data_manifest"][0]["columns"], ["score"])
        self.assertNotIn("name", mapped["data_manifest"][0]["columns"])

    def test_a_date_column_keeps_its_own_type(self):
        table = ingest.read_table("scores.csv", SCORES)
        kinds = {column["name"]: column["type"] for column in table["columns"]}
        self.assertEqual(kinds["when"], "date")
        self.assertEqual(kinds["score"], "number")

    def test_mapping_does_not_upgrade_the_data(self):
        table = ingest.read_table("scores.csv", SCORES)
        mapped = ingest.to_method_inputs(table, "descriptive_stats", {"values": "score"})
        self.assertEqual(mapped["provenance"]["kind"], "sourced")
        self.assertIn("does not verify", mapped["provenance"]["note"])
        self.assertIn("does not verify", mapped["data_manifest"][0]["note"])


class MappingRefusalsTest(unittest.TestCase):
    def setUp(self):
        self.scores = ingest.read_table("scores.csv", SCORES)

    def test_an_unknown_method_is_refused_with_the_reason(self):
        with self.assertRaises(ingest.IngestError) as caught:
            ingest.to_method_inputs(self.scores, "no_such_method", {"values": "score"})
        self.assertIn("unknown method", str(caught.exception))

    def test_an_unknown_column_is_refused_and_the_columns_are_named(self):
        with self.assertRaises(ingest.IngestError) as caught:
            ingest.to_method_inputs(self.scores, "descriptive_stats", {"values": "nope"})
        message = str(caught.exception)
        self.assertIn("unknown column", message)
        self.assertIn("score", message)

    def test_a_scalar_input_cannot_come_from_a_column(self):
        with self.assertRaises(ingest.IngestError) as caught:
            ingest.to_method_inputs(self.scores, "wacc", {"equity_value": "score"})
        self.assertIn("cannot be mapped from a column", str(caught.exception))

    def test_a_mixed_column_cannot_feed_a_value_list(self):
        mixed = ingest.read_table("mixed.csv", MIXED)
        with self.assertRaises(ingest.IngestError):
            ingest.to_method_inputs(mixed, "descriptive_stats", {"values": "score"})

    def test_an_empty_mapping_is_refused(self):
        with self.assertRaises(ingest.IngestError) as caught:
            ingest.to_method_inputs(self.scores, "descriptive_stats", {})
        self.assertIn("map must be an object", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

