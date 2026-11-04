"""Isolate the crash in the deterministic transaction path.

BP_SRC selects which tree to probe: the working tree or the HEAD baseline copy.
"""
import os
import sys
import traceback

SRC = os.environ.get("BP_SRC") or os.path.join(
    r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline", "src")
sys.path.insert(0, SRC)

from bp import statement_detect as sd  # noqa: E402

print("probing:", SRC)

NARRATIVE = ("Alder Trading opened on 1 January 2025. The owner invested 50,000 cash in the business "
             "for shares on 1 January 2025. The business purchased a delivery van for 30,000 cash on "
             "2 January 2025. It paid 6,000 cash rent on 3 March 2025. It paid 8,000 cash salaries on "
             "31 March 2025.")

found = sd.detect(NARRATIVE)
print("detections:", len(found))
for match in found:
    detector_id = getattr(match, "detector_id", None) or getattr(match, "id", None)
    print("  ", detector_id, match.slots)
    try:
        lines = sd.journalize(detector_id, match.slots)
        print("      ->", lines)
    except Exception:
        print("      -> CRASH:", type(sys.exc_info()[1]).__name__)
        traceback.print_exc(limit=1)
