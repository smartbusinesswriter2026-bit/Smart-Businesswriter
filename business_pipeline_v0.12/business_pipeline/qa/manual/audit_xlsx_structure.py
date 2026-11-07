"""Structural audit of the .xlsx workbooks against the OOXML rules Excel enforces.

Reads the workbooks the product actually renders (the statements tile from the frozen fixture
record, and the Finance working paper from a real delivered case), checks every part against
the OPC and SpreadsheetML rules, and prints the differences against an openpyxl reference
workbook.

Usage:
    $env:PYTHONPATH="src"; python qa/manual/audit_xlsx_structure.py

This is a QA probe.  It may use openpyxl; the product layer may not.
"""
import io
import json
import os
import sys
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import spreadsheets as sheet_writer  # noqa: E402
from bp.product import xlsx as xlsx_export  # noqa: E402

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

#: CT_Worksheet's element sequence (ECMA-376 Part 1, 18.3.1.99).
WORKSHEET_ORDER = [
    "sheetPr", "dimension", "sheetViews", "sheetFormatPr", "cols", "sheetData",
    "sheetCalcPr", "sheetProtection", "protectedRanges", "scenarios", "autoFilter",
    "sortState", "dataConsolidate", "customSheetViews", "mergeCells", "phoneticPr",
    "conditionalFormatting", "dataValidations", "hyperlinks", "printOptions",
    "pageMargins", "pageSetup", "headerFooter", "rowBreaks", "colBreaks",
    "customProperties", "cellWatches", "ignoredErrors", "smartTags", "drawing",
]

#: CT_Stylesheet's element sequence.  `numFmts` must come before `fonts`: a stylesheet that
#: puts it later is the "Excel found a problem with some content" failure.
STYLES_ORDER = [
    "numFmts", "fonts", "fills", "borders", "cellStyleXfs", "cellXfs",
    "cellStyles", "dxfs", "tableStyles", "colors", "extLst",
]

problems = []

#: When true the audit keeps its findings but stops narrating them.
QUIET = False


def say(message=""):
    """Print, unless the audit is running quietly."""
    if not QUIET:
        sys.stdout.write(message + "\n")


def flag(message):
    problems.append(message)
    say("  !! " + message)


def local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def audit(path, label):
    """Audit one workbook and return a dict of its facts."""
    say("\n=== %s: %s ===" % (label, path))
    facts = {}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        facts["names"] = names
        say("parts (%d):" % len(names))
        for name in names:
            say("   - %s" % name)

        # -- [Content_Types].xml -------------------------------------------
        if "[Content_Types].xml" not in names:
            flag("no [Content_Types].xml")
            return facts
        ct = ET.fromstring(archive.read("[Content_Types].xml"))
        overrides = [o.get("PartName") for o in ct.findall("{%s}Override" % CT_NS)]
        counts = Counter(overrides)
        say("\n[Content_Types].xml overrides:")
        for name in overrides:
            say("   - %s%s" % (name, "   <-- DUPLICATE" if counts[name] > 1 else ""))
        for name, count in counts.items():
            if count > 1:
                flag("duplicate Override for %s (%d times)" % (name, count))
        defaults = {d.get("Extension"): d.get("ContentType") for d in ct.findall("{%s}Default" % CT_NS)}
        facts["overrides"] = overrides
        facts["defaults"] = defaults

        # every part that is not covered by a Default must have an Override
        for name in names:
            if name.endswith("/"):
                continue
            ext = name.rsplit(".", 1)[-1].lower()
            if "/" + name in overrides:
                continue
            if ext in defaults:
                continue
            flag("part %s has no content type (no Override, no Default for .%s)" % (name, ext))

        # -- package relationships ----------------------------------------
        if "_rels/.rels" not in names:
            flag("no _rels/.rels")
        else:
            rels = ET.fromstring(archive.read("_rels/.rels"))
            say("\n_rels/.rels:")
            for rel in rels:
                say("   - %s -> %s" % (rel.get("Id"), rel.get("Target")))
                if rel.get("TargetMode") == "External":
                    continue
                target = rel.get("Target").lstrip("/")
                if target not in names:
                    flag("package relationship %s points at missing part %s" % (rel.get("Id"), target))

        # -- workbook ------------------------------------------------------
        if "xl/workbook.xml" not in names:
            flag("no xl/workbook.xml")
            return facts
        wb = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet_names = []
        say("\nworkbook sheets:")
        for sheet in wb.iter("{%s}sheet" % MAIN):
            sheet_names.append(sheet.get("name"))
            say("   - %s (sheetId=%s r:id=%s)" % (sheet.get("name"), sheet.get("sheetId"), sheet.get("r:id")))
        facts["sheets"] = sheet_names
        for name, count in Counter(sheet_names).items():
            if count > 1:
                flag("duplicate sheet name %r (%d times)" % (name, count))
        for name in sheet_names:
            if len(name) > 31:
                flag("sheet name %r is longer than 31 characters" % name)
            for bad in '[]:*?/\\':
                if bad in name:
                    flag("sheet name %r carries the illegal character %r" % (name, bad))

        # -- workbook relationships ---------------------------------------
        rels_path = "xl/_rels/workbook.xml.rels"
        if rels_path not in names:
            flag("no %s" % rels_path)
            return facts
        wrels = ET.fromstring(archive.read(rels_path))
        by_id = {}
        say("\nxl/_rels/workbook.xml.rels:")
        for rel in wrels:
            by_id[rel.get("Id")] = rel
            say("   - %s [%s] -> %s" % (rel.get("Id"), rel.get("Type").rsplit("/", 1)[-1], rel.get("Target")))
            target = rel.get("Target").lstrip("/")
            if target not in names and "xl/" + target not in names:
                flag("workbook relationship %s points at missing part %s" % (rel.get("Id"), target))
        rel_types = Counter(rel.get("Type").rsplit("/", 1)[-1] for rel in wrels)
        for kind in ("worksheet", "styles"):
            if rel_types.get(kind, 0) == 0:
                flag("no %s relationship in %s" % (kind, rels_path))
        for sheet in wb.iter("{%s}sheet" % MAIN):
            rid = sheet.get("{%s}id" % "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
            if rid not in by_id:
                flag("sheet %r uses %s which has no relationship" % (sheet.get("name"), rid))

        # -- styles.xml ----------------------------------------------------
        if "xl/styles.xml" in names:
            styles = ET.fromstring(archive.read("xl/styles.xml"))
            order = [local(child.tag) for child in styles]
            say("\nxl/styles.xml children: %s" % order)
            positions = []
            for child in order:
                if child not in STYLES_ORDER:
                    flag("xl/styles.xml: unknown child <%s>" % child)
                    continue
                positions.append((STYLES_ORDER.index(child), child))
            for i in range(1, len(positions)):
                if positions[i][0] < positions[i - 1][0]:
                    flag("xl/styles.xml: <%s> must come before <%s> (CT_Stylesheet order)"
                         % (positions[i][1], positions[i - 1][1]))
            xfs = styles.find("{%s}cellXfs" % MAIN)
            if xfs is None or xfs.find("{%s}xf" % MAIN) is None:
                flag("xl/styles.xml: cellXfs has no default xf")

        # -- worksheets ----------------------------------------------------
        for name in sorted(n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml")):
            root = ET.fromstring(archive.read(name))
            order = [local(child.tag) for child in root]
            say("\n%s children: %s" % (name, order))
            positions = []
            for child in order:
                if child not in WORKSHEET_ORDER:
                    flag("%s: unknown child <%s>" % (name, child))
                    continue
                positions.append((WORKSHEET_ORDER.index(child), child))
            for i in range(1, len(positions)):
                if positions[i][0] < positions[i - 1][0]:
                    flag("%s: <%s> must come before <%s> (CT_Worksheet order)"
                         % (name, positions[i][1], positions[i - 1][1]))
            rows = root.findall("{%s}sheetData/{%s}row" % (MAIN, MAIN))
            for row in rows:
                for cell in row.findall("{%s}c" % MAIN):
                    ref = cell.get("r") or ""
                    if not ref:
                        flag("%s: a cell has no r attribute" % name)
    return facts


def openpyxl_reference(path):
    """A reference workbook openpyxl writes, for comparison."""
    import openpyxl
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Income Statement"
    sheet["A1"] = "Income Statement"
    sheet["A5"] = "Sales Revenue"
    sheet["B5"] = 200000
    sheet["B5"].number_format = "#,##0.00"
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    with open(path, "wb") as stream:
        stream.write(buffer.getvalue())
    return path


def main():
    fixture = os.path.join(ROOT, "tests", "fixtures", "statements-record.json")
    with open(fixture, encoding="utf-8") as stream:
        record = json.load(stream)

    out_dir = os.path.join(HERE, "out")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    ours = os.path.join(out_dir, "statements-probe.xlsx")
    data = xlsx_export.render_bytes(record)
    with open(ours, "wb") as stream:
        stream.write(data)
    say("rendered %d bytes -> %s" % (len(data), ours))

    reference = openpyxl_reference(os.path.join(out_dir, "openpyxl-reference.xlsx"))

    our_facts = audit(ours, "OURS")
    ref_facts = audit(reference, "OPENPYXL REFERENCE")

    say("\n=== part-name comparison ===")
    say("only in ours : %s" % sorted(set(our_facts["names"]) - set(ref_facts["names"])))
    say("only in ref  : %s" % sorted(set(ref_facts["names"]) - set(our_facts["names"])))

    say("\n=== verdict ===")
    if problems:
        say("%d problem(s) found:" % len(problems))
        for problem in problems:
            say("   - %s" % problem)
        return 1
    say("no structural problem found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
