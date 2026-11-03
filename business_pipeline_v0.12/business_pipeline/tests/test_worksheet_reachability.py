"""A worksheet that no shelf offers is invisible, and nothing used to say so.

`subjects.WORKSHEETS` holds every T4 worksheet the product can complete, but a student
reaches one only through a shelf's `worksheets` list.  Measured in session 7: 76
worksheet entries, 58 reachable, **18 built and offered nowhere** — 16 marketing rows
that a page badges "Worksheet" in a card that cannot be opened, plus STR-19 and CHG-15
which appear on no page at all (D-PLAN-02).  MKT-07 is deliberate: B-198 hid its tile
until its block form is repaired.

Which shelf should own each one is a curriculum decision, not a code decision, so this
test is a **shrinking ledger**: it pins the measured set.  Wiring one of them fails this
test until the list is updated (the ledger cannot quietly go stale), and a *new*
worksheet that no shelf offers fails it immediately.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import subjects  # noqa: E402

#: Built, complete, and offered by no shelf page today.  Remove an id here when its
#: shelf lists it; never add one without a ledger row in qa/QA_DEFECTS.md.
KNOWN_UNSERVED = {
    "CHG-15",  # change and organisation review - no shelf lists it, no tile shows it
    "MKT-01", "MKT-03", "MKT-05", "MKT-07", "MKT-08", "MKT-09", "MKT-10", "MKT-11",
    "MKT-12", "MKT-13", "MKT-14", "MKT-16", "MKT-17", "MKT-19", "MKT-20", "MKT-21",
    "STR-19",  # strategic positioning - no shelf lists it, no tile shows it
}

#: Hidden by the owner's instruction (B-198) until the SERVQUAL block form is repaired.
HIDDEN_BY_OWNER = {"MKT-07"}


def served():
    """Every worksheet id the shelves actually offer, in the order they declare them."""
    out = set()
    for definition in subjects.SUBJECT_DEFS:
        out.update(definition.get("worksheets") or [])
    return out


class WorksheetReachabilityTest(unittest.TestCase):
    def test_the_ledger_is_exactly_the_worksheets_no_shelf_offers(self):
        unserved = set(subjects.WORKSHEETS) - served()
        self.assertEqual(unserved, KNOWN_UNSERVED,
                         "the unserved set moved: wire the worksheet, or ledger it")

    def test_every_worksheet_entry_still_exists_as_a_template(self):
        """The other half of the trap: a shelf may not list a worksheet that is not built."""
        for definition in subjects.SUBJECT_DEFS:
            for catalogue_id in definition.get("worksheets") or []:
                self.assertIn(catalogue_id, subjects.WORKSHEETS,
                              "%s lists %s but no worksheet is built for it"
                              % (definition["id"], catalogue_id))

    def test_the_hidden_one_stays_named_and_never_slips_out_of_the_ledger(self):
        self.assertTrue(HIDDEN_BY_OWNER <= KNOWN_UNSERVED)
        self.assertNotIn("MKT-07", served())


if __name__ == "__main__":
    unittest.main()
