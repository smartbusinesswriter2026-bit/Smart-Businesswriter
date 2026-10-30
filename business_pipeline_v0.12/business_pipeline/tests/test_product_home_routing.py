import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from bp.product import chat, guard


class HomeRoutingTest(unittest.TestCase):
    def test_open_marketing_not_refused(self):
        st = chat.start("Evaluate the effectiveness of the brand new digital advertising campaign for urban millennials.", "any")
        self.assertNotEqual(st.get("stage"), "not_supported")
        self.assertEqual((st.get("subject_detected") or {}).get("id"), "marketing")

    def test_open_operations_capacity(self):
        st = chat.start("Assess whether the current production line capacity can meet the declared demand of 4,000 units per month.", "any")
        caps = [r["key"] for r in (st.get("selection") or {}).get("selected") or []]
        self.assertIn("capacity_analysis", caps)

    def test_open_finance_npv(self):
        st = chat.start("Determine the net present value of the declared cash flows of 1500000, 2000000, 2200000, 2400000 and 2500000 pesos at a 9 percent discount rate.", "any")
        caps = [r["key"] for r in (st.get("selection") or {}).get("selected") or []]
        self.assertIn("npv", caps)

    def test_open_economics_not_refused(self):
        st = chat.start("Analyse the effect of a new VAT policy on consumer demand and prices.", "any")
        self.assertNotEqual(st.get("stage"), "not_supported")

    def test_open_people_project_research_not_refused(self):
        for brief in [
            "Analyze employee turnover and its effect on organization productivity.",
            "Evaluate the schedule risk and probability of meeting the target completion date for the construction project.",
            "Test whether the observed relationship between advertising spend and revenue is significant across 24 observations.",
        ]:
            st = chat.start(brief, "any")
            self.assertNotEqual(st.get("stage"), "not_supported")

    def test_open_pure_accounting_refused(self):
        st = chat.start("Prepare the journal entries and the trial balance for the month from the declared transactions.", "any")
        self.assertEqual(st.get("stage"), "not_supported")
        self.assertIn("Accounting", st.get("message", ""))

    def test_shelf_mode_control(self):
        st = chat.start("Evaluate the effectiveness of the brand new digital advertising campaign for urban millennials.", "management")
        self.assertEqual(st.get("stage"), "not_supported")
        self.assertIn("does not look like a management or strategy instruction", st.get("message", ""))

    def test_no_subject_defaults_management(self):
        st = chat.start("Evaluate the effectiveness of the brand new digital advertising campaign for urban millennials.")
        self.assertEqual(st.get("subject"), "management")

    def test_detection_determinism(self):
        brief = "Analyze employee turnover and its effect on organization productivity."
        a = chat.start(brief, "any").get("subject_detected")
        b = chat.start(brief, "any").get("subject_detected")
        self.assertEqual(a, b)

    def test_detected_subject_not_in_paper_text(self):
        st = chat.start("Analyze employee turnover and its effect on organization productivity.", "any")
        # no paper drafted here; just ensure detected label not in brief-derived decision? smoke check
        self.assertNotIn("People & organisation", st.get("brief", ""))


if __name__ == "__main__":
    unittest.main()
