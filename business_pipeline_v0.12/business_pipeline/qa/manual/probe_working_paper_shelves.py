"""The working paper's workbook, rendered from a real run, for every tile of three shelves.

The Finance working paper was built for the Finance tiles.  This probe is the same measurement
for the three shelves the owner named next - **Operations management**, **Supply chain &
logistics** and **Marketing & customers** - and it answers four questions per tile:

(a) the tile runs at all: preset -> `Session` -> the delivered record;
(b) the record becomes a working paper: cover, summary, inputs, working, results, checks, notes,
    record - each of them only when the record can fill it;
(c) the workbook opens: it is a real OOXML package, written by the shipped export route
    (`deliverables.write_export`, the same call the download button makes);
(d) the export is stable: two exports of the same record are byte-identical.

Nothing here is computed for the probe: every figure in every workbook comes from the frozen
core's own record.  The probe only runs the engine and looks at what came back.

Usage:
    $env:PYTHONPATH="src"; python qa/manual/probe_working_paper_shelves.py
    $env:PYTHONPATH="src"; python qa/manual/probe_working_paper_shelves.py --shelf operations

It writes one workbook per tile to `qa/evidence/<shelf>/workpapers/` and one inventory per shelf
to `qa/evidence/<shelf>/working-paper-sheets.json`.  It exits non-zero when a tile is not
delivered, or when a delivered tile renders no Results sheet.
"""

import argparse
import hashlib
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import server                                     # noqa: E402
from bp.product import deliverables, spreadsheets, subjects  # noqa: E402
from bp.session import Session                           # noqa: E402

#: The shelves the owner named after the Finance working paper.
SHELVES = ("operations", "supply-chain", "marketing")

#: The deliverable the download button asks for, and the format it asks in.
DELIVERABLE = "workpapers"
FORMAT = "xlsx"

#: The sheets the working paper is made of, in the order the standard puts them in.  A sheet the
#: record cannot fill is dropped rather than shown empty.
PAPER_ORDER = ("Cover", "Summary", "Inputs", "Working", "Results", "Checks", "Notes", "Record")


def evidence_dir(shelf):
    """Where this shelf's evidence lives."""
    return os.path.join(ROOT, "qa", "evidence", shelf)


def sheet_names(path):
    """The sheets a workbook carries, in the order the workbook lists them."""
    with zipfile.ZipFile(path) as archive:
        workbook = archive.read("xl/workbook.xml").decode("utf-8")
    names = []
    for chunk in workbook.split("<sheet ")[1:]:
        name = chunk.split('name="', 1)[1].split('"', 1)[0]
        names.append(name)
    return names


def run_tile(tool):
    """The delivered record for one tile: preset -> Session -> delivery."""
    preset = server.PRESETS.get(tool.get("preset") or "") or {}
    request = {"objective": preset.get("objective") or ("%s working paper probe" % tool["key"]),
               "method": tool["method"],
               "inputs": dict(preset.get("inputs") or {})}
    session = Session(request)
    session.confirm(True)
    if session.pause:                    # the second checkpoint: the account mapping
        session.confirm(True)
    return session, session.delivery


def bundle_for(session, delivery, title):
    """The case bundle the product stores for a delivered record."""
    appendix = delivery.appendix
    reperform = appendix.get("reperform") or {}
    return {
        "format": "bp-case/1",
        "id": session.id,
        "title": title,
        "method": (appendix.get("method") or {}).get("id") or "",
        "tier": delivery.tier,
        "spec_hash": appendix.get("spec_hash") or "",
        "outputs_hash": reperform.get("outputs_hash") or "",
        "session": session.to_dict(),
        "delivery": {"report": delivery.report, "appendix": appendix},
        "reperform": reperform,
    }


def sha256(path):
    """The file's own hash: a fact about the file, never a cell inside it."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(shelf):
    """Every tile of one shelf: the run, the workbook, and what the workbook carries."""
    detail = subjects.detail(shelf)
    folder = os.path.join(evidence_dir(shelf), "workpapers")
    os.makedirs(folder, exist_ok=True)
    inventory = []
    print("\n%s" % shelf.upper())
    print("  %-16s %-26s %-9s %s" % ("tile", "method", "status", "sheets"))
    for tool in detail["tools"]:
        session, delivery = run_tile(tool)
        if delivery is None or delivery.status != "delivered":
            reason = (delivery.blocked_reason if delivery else "no delivery")
            print("  %-16s %-26s %-9s %s" % (tool["key"], tool["method"], "BLOCKED", reason))
            inventory.append({"key": tool["key"], "method": tool["method"], "status": "blocked",
                              "reason": reason, "sheets": []})
            continue
        preset = server.PRESETS.get(tool.get("preset") or "") or {}
        title = preset.get("objective") or ("%s working paper" % tool["key"])
        bundle = bundle_for(session, delivery, title)
        path = os.path.join(folder, "%s.xlsx" % tool["key"])
        deliverables.write_export(bundle, DELIVERABLE, FORMAT, path)
        sheets = sheet_names(path)
        again = os.path.join(folder, "%s.repeat.xlsx" % tool["key"])
        deliverables.write_export(bundle, DELIVERABLE, FORMAT, again)
        stable = sha256(path) == sha256(again)
        os.remove(again)
        print("  %-16s %-26s %-9s %s%s"
              % (tool["key"], tool["method"], "delivered", ", ".join(sheets),
                 "" if stable else "   BYTES DIFFER"))
        inventory.append({"key": tool["key"], "method": tool["method"], "status": "delivered",
                          "sheets": sheets, "stable": stable, "sha256": sha256(path)})
    with open(os.path.join(evidence_dir(shelf), "working-paper-sheets.json"), "w",
              encoding="utf-8") as stream:
        json.dump({"shelf": shelf, "standard": list(PAPER_ORDER), "tiles": inventory},
                  stream, indent=2, sort_keys=True)
        stream.write("\n")
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shelf", action="append", choices=list(SHELVES),
                        help="probe one shelf only (repeatable)")
    arguments = parser.parse_args()
    shelves = arguments.shelf or list(SHELVES)

    failures = []
    for shelf in shelves:
        for row in probe(shelf):
            if row["status"] != "delivered":
                failures.append("%s/%s: %s" % (shelf, row["key"], row.get("reason")))
            elif "Results" not in row["sheets"]:
                failures.append("%s/%s: the workbook carries no Results sheet" % (shelf, row["key"]))
            elif not row.get("stable"):
                failures.append("%s/%s: two exports of the same record differ" % (shelf, row["key"]))

    print("\n%s" % ("=" * 70))
    if failures:
        print("FAILURES (%d)" % len(failures))
        for line in failures:
            print("  !! %s" % line)
        return 1
    print("every tile of %s delivered, rendered and byte-stable" % ", ".join(shelves))
    return 0


if __name__ == "__main__":
    sys.exit(main())
