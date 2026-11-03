"""A brief is judged against the shelf it names — never against one nobody named.

`chat.start` defaulted an unnamed shelf to "management" *in the guard* and then refused
briefs that are not management briefs.  Through the API that is the common case: the
Home composer posts `subject: "any"`, but a direct caller that omits the subject had its
brief judged as a management brief and answered "This does not look like a management or
strategy instruction" before any question was asked (D-PLAN-03).  A refusal that fires on
a brief nobody mis-shelved is the same defect as a silent substitution, in reverse.

Nothing is loosened: a brief that *does* name a shelf is still refused when it belongs to
another one, with the shelf to use instead.
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import api, chat, guard  # noqa: E402

#: A brief that names its external question but uses none of the management vocabulary.
EXTERNAL_BRIEF = ("What political, economic and social pressures affect coffee growers in "
                  "Ethiopia over the next five years?")


class UnnamedShelfTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-subject-fit-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_brief_that_names_no_shelf_is_not_refused_as_the_wrong_shelf(self):
        """The trap: this used to answer `not_supported` for a legitimate external brief."""
        code, state = api.handle("POST", "/api/cases/chat", {"brief": EXTERNAL_BRIEF})
        self.assertEqual(code, 201)
        self.assertEqual(state["stage"], "clarify")
        self.assertTrue(state["questions"])

    def test_the_same_brief_pinned_to_management_is_still_refused_with_the_shelf_to_use(self):
        code, state = api.handle("POST", "/api/cases/chat",
                                 {"brief": EXTERNAL_BRIEF, "subject": "management"})
        self.assertEqual(code, 201)
        self.assertEqual(state["stage"], "not_supported")
        self.assertIn("management or strategy", state["message"])

    def test_a_pure_computation_is_still_sent_to_the_shelf_that_runs_it(self):
        code, state = api.handle("POST", "/api/cases/chat",
                                 {"brief": "Post the journal entry and reconcile the trial balance for March."})
        self.assertEqual(code, 201)
        self.assertEqual(state["stage"], "not_supported")
        self.assertIn("Accounting", state["message"])

    def test_the_refusal_names_the_shelf_with_the_right_article(self):
        fits, message = guard.subject_fit("a coffee shop for students", "entrepreneurship")
        self.assertFalse(fits)
        self.assertIn("not look like an entrepreneurship instruction", message)
        self.assertNotIn("a entrepreneurship", message)
        fits, message = guard.subject_fit("a coffee shop for students", "management")
        self.assertFalse(fits)
        self.assertIn("a management or strategy instruction", message)

    def test_the_default_signature_still_records_a_shelf(self):
        """An unnamed shelf is recorded as management; it is only the *guard* that stays quiet."""
        state = chat.start(EXTERNAL_BRIEF)
        self.assertEqual(state["subject"], "management")
        self.assertEqual(state["stage"], "clarify")


if __name__ == "__main__":
    unittest.main()
