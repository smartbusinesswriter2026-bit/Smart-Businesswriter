"""Model-assisted prose is a proposal, and it may not add facts."""

import json
import os
import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import chat, prose  # noqa: E402
import tests.test_chat as helpers  # noqa: E402


PROPOSAL = {
    "introduction": "The decision under analysis is whether the chain should enter the Saudi market. "
                    "The paper argues that a cautious entry is defensible.",
    "leads": {"Political": "The political conditions set the frame for that decision.",
              "Economic": "The economic evidence explains the cost of that choice."},
    "integration": "The external evidence and the internal position point in the same direction.",
    "conclusion": "The paper therefore supports a cautious entry.",
}


class ProseTest(unittest.TestCase):
    @mock.patch("bp.product.sources.search_web", side_effect=helpers.web)
    @mock.patch("bp.product.sources.search_academic", side_effect=helpers.academic)
    def prepared(self, _academic, _web):
        state = helpers.answer_all(chat.start(helpers.BRIEF))
        state = chat.research(chat.confirm_plan(state))
        return chat.draft(state, implications="A cautious entry is defensible.", style="apa")

    @mock.patch("bp.product.prose._call", return_value=json.dumps(PROPOSAL))
    def test_a_proposal_changes_linking_prose_but_not_the_evidence(self, _call):
        state = self.prepared()
        before = {item["heading"]: list(item["lines"]) for item in state["draft"]["outline"]}
        proposal = prose.propose(state, state["draft"])
        updated = prose.apply(state["draft"], proposal)
        after = {item["heading"]: list(item["lines"]) for item in updated["outline"]}
        self.assertIn("cautious entry", after["Introduction"][0])
        self.assertTrue(after["Political"][0].startswith("The political conditions"))
        self.assertIn("The source reports a relevant change", after["Political"][0])
        self.assertEqual(before["References"], after["References"])
        self.assertIn("prose", updated)

    @mock.patch("bp.product.prose._call", return_value=json.dumps({
        "introduction": "A new claim with 99% certainty.",
        "leads": {}, "integration": "", "conclusion": "Done."}))
    def test_a_new_number_is_refused(self, _call):
        state = self.prepared()
        with self.assertRaises(prose.ProseError):
            prose.propose(state, state["draft"])

    def test_no_key_is_a_clear_refusal(self):
        with mock.patch.dict(os.environ, {"BP_OPENGO_API_KEY": ""}, clear=False):
            self.assertFalse(prose.available())


if __name__ == "__main__":
    unittest.main()
