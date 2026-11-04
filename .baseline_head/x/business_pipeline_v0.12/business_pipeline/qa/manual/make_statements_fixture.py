"""Regenerate the frozen statements record the render lane builds against.

Run from anywhere:

    python qa/manual/make_statements_fixture.py

The record is built from the golden engagement in `tests/test_statement_plan.py` through the real
plan layer, with the model's extraction step stubbed by the declared journal.  The contract test
`tests/test_statements_render_contract.py` fails when the regenerated record differs from the
committed one, so this script is the only correct way to accept an intended pipeline change.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for path in (os.path.join(ROOT, "src"), os.path.join(ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

import product_statements_fixture as fixture  # noqa: E402

if __name__ == "__main__":
    record = fixture.write()
    rendered = [key for key in ("income_statement", "balance_sheet", "equity", "cash_flow")
                if (record.get("statements") or {}).get(key)]
    print("wrote", fixture.FIXTURE)
    print("requested:", ", ".join(record.get("requested") or []))
    print("rendered :", ", ".join(rendered))
    print("plan hash:", record.get("plan_hash"))
