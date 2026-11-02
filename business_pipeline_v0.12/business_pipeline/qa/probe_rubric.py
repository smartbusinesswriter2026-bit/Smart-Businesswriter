"""Probe the rubric reader with realistic documents (QA tool, not part of the suite)."""
import json
import sys

sys.path.insert(0, "src")

from bp.product import rubric

TABLE = """
BA 101 - Group Business Report (30% of the course grade)

| Criterion | Weight | Descriptor |
|---|---|---|
| Situation analysis | 30% | Applies two frameworks to the case and shows the working |
| Financial analysis | 40% | Must include: a break-even calculation; three ratios computed from the case |
| Recommendations | 30% | Recommended actions follow from the analysis |

Required sections: Introduction, Situation analysis, Financial analysis, Recommendations, Conclusion

Word count: 2,500 words (+/- 10%)
Referencing: APA 7th edition
"""

LIST = """
Assessment criteria
1. Problem definition - 20% - states the decision to be made
2. Evidence - 40% - should include three sources from 2020 or later
3. Analysis - 30% - applies the value chain
4. Writing - 10% - clear structure
"""

NO_WEIGHTS = """
The report is marked on:
- Clarity of the problem statement
- Use of course frameworks
- Quality of the recommendation
"""

NOT_A_RUBRIC = """
Please read the attached case and write a short report about the company's
competitive position in its market.
"""

BARE_NUMBERS = """
| Assessment item | Marks |
| --- | --- |
| Research | 25 |
| Analysis | 45 |
| Presentation | 30 |
"""

PAGES = """
Style notes for the assignment.
The report must not exceed 8 pages and should use Harvard referencing.
| Criterion | % |
| --- | --- |
| Structure | 50 |
| Content | 50 |
"""


def show(name, text):
    parsed = rubric.parse(text)
    print("=" * 70)
    print(name, "->", json.dumps(rubric.summary(parsed), ensure_ascii=False))
    for criterion in parsed["criteria"]:
        print("   -", json.dumps({k: criterion[k] for k in
                                  ("name", "weight", "weight_text", "descriptor",
                                   "required_elements")}, ensure_ascii=False))
    print("   sections :", parsed["sections"])
    print("   words    :", parsed["word_budget"])
    print("   style    :", parsed["citation_style"], "| total:", parsed["total_weight"])
    print("   problems :")
    for problem in parsed["problems"]:
        print("      *", problem)
    print("   ok:", parsed["ok"], "| confirm:", parsed["confirm_required"])


for label, payload in (("TABLE", TABLE), ("LIST", LIST), ("NO_WEIGHTS", NO_WEIGHTS),
                       ("NOT_A_RUBRIC", NOT_A_RUBRIC), ("BARE_NUMBERS", BARE_NUMBERS),
                       ("PAGES", PAGES)):
    show(label, payload)
