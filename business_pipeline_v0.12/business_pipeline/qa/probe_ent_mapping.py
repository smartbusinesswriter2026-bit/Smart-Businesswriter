"""A plan block's columns through the core's own mapper (D-ENT-02 evidence).

The business plan's blocks mix **list** inputs (revenue by period, operating costs) with
**declared drivers** (the gross margin, the opening cash).  A student's spreadsheet holds
the lists.  Before the fix the mapper refused that mapping outright — "missing required
input 'gross_margin_rate'" — so the shape the product itself asks for could not be
proposed.  Nothing here runs a method: a mapping is a proposal.

Usage:  python qa/probe_ent_mapping.py
Writes: qa/baseline/ent_mapping.txt
"""
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parent
sys.path.insert(0, str(APP / "src"))

os.environ["BP_INTAKE_DIR"] = tempfile.mkdtemp(prefix="bp-ent-map-")

from bp import ingest                        # noqa: E402
from bp.product import intake                # noqa: E402

OUT = APP / "qa" / "baseline"

CSV = (b"month,revenue,operating_costs,depreciation\n"
       b"1,1200000,300000,90000\n2,1500000,320000,90000\n3,1800000,340000,90000\n")

CASES = (
    ("proforma (lists from the file, drivers typed)",
     "proforma_statements", {"revenue": "revenue", "operating_costs": "operating_costs",
                             "depreciation": "depreciation"}),
    ("sensitivity (changes from the file, base typed)",
     "sensitivity_table", {"price_changes": "revenue", "volume_changes": "revenue"}),
    ("breakeven (every input is a scalar)",
     "breakeven", {"fixed": "revenue"}),
    ("frommarket (every input is a scalar)",
     "sales_from_market", {"market_size": "revenue"}),
    ("descriptive (a single list, unmapped extras named)",
     "descriptive_stats", {"values": "revenue"}),
)


def main():
    record = intake.save("plan.csv", CSV)
    intake.attach_table(record["id"], ingest.read_table("plan.csv", CSV))
    lines = ["entrepreneurship — a plan block's columns through bp.ingest.to_method_inputs",
             "(python qa/probe_ent_mapping.py)", ""]
    for label, method, columns in CASES:
        try:
            mapped = intake.mapped_request(record["id"], method, columns)
            lines.append("%-48s PROPOSED  inputs=%s  not_mapped=%s"
                         % (label, sorted(mapped["inputs"]), mapped["not_mapped"]))
            lines.append("%-48s           still to type: %d of %d declared inputs"
                         % ("", len(mapped["not_mapped"]), len(mapped["not_mapped"])
                            + len(mapped["inputs"])))
            lines.append("%-48s           nothing computed: %s"
                         % ("", not any(key in mapped for key in ("report", "delivery", "result"))))
        except intake.IntakeError as error:
            lines.append("%-48s REFUSED   %s" % (label, str(error)[:160]))
    text = "\n".join(lines) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ent_mapping.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
