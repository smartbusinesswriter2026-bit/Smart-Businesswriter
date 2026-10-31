"""Verify a DOCX that was built from a markdown master.

    python corpus-db/build/verify_manual_docx.py --source DATABASE.md --docx DATABASE.docx

The renderer is the oracle. The markdown is parsed with the renderer's own
`parse_markdown`, the expected plain text of every block is produced with the
renderer's own `inline_runs`, and those expected units are matched, in order,
against the text units actually present in the DOCX. A coverage gap therefore
means the renderer dropped something, not that the two files differ in style.

Checks, in order:
  1. the zip opens, every part is present, every XML part parses
  2. the OOXML structural non-negotiables hold
  3. content coverage - every block of the source appears, in order, with the
     text the renderer would produce
  4. no template instruction leaks into the output

Exit code 0 when every check passes, 1 otherwise.
"""

import argparse
import importlib.util
import io
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RENDERER = os.path.join(
    os.path.dirname(os.path.dirname(HERE)),
    "business_pipeline_v0.12", "business_pipeline", "scripts", "build_manual_docx.py")

REQUIRED_PARTS = [
    "[Content_Types].xml", "_rels/.rels", "word/document.xml",
    "word/_rels/document.xml.rels", "word/styles.xml", "word/settings.xml",
    "word/header1.xml", "word/footer1.xml", "docProps/core.xml",
]

BANNED = ("{{", "TODO", "Lorem ipsum", "placeholder text", "<w:", "```")


def load_renderer(path):
    spec = importlib.util.spec_from_file_location("build_manual_docx", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plain(renderer, text):
    """The text the renderer would show for a markdown inline string."""
    return "".join(run[0] for run in renderer.inline_runs(text))


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def expected_units(renderer, markdown):
    """Every text unit the renderer should have produced, in order."""
    units = []
    for block in renderer.parse_markdown(markdown):
        kind = block[0]
        if kind == "heading":
            units.append(("heading", plain(renderer, block[2])))
        elif kind == "para":
            units.append(("para", plain(renderer, block[1])))
        elif kind == "list":
            for marker, level, content in block[1]:
                units.append(("list", plain(renderer, content)))
        elif kind == "table":
            for cell in block[1]:
                units.append(("cell", plain(renderer, cell)))
            for row in block[2]:
                for cell in row:
                    units.append(("cell", plain(renderer, cell)))
        elif kind == "code":
            for line in block[1]:
                units.append(("code", line))
    return units


def actual_units(body):
    """Every text unit present in the document body, in order."""
    units = []
    for child in body:
        if child.tag == W + "p":
            text = "".join(t.text or "" for t in child.iter(W + "t"))
            if norm(text):
                units.append(norm(text))
        elif child.tag == W + "tbl":
            for row in child.findall(W + "tr"):
                for cell in row.findall(W + "tc"):
                    # a normal cell is one paragraph; a code block is one
                    # paragraph per line. Both are units in order.
                    for para in cell.findall(W + "p"):
                        text = "".join(t.text or "" for t in para.iter(W + "t"))
                        if norm(text):
                            units.append(norm(text))
    return units


def verify(source_path, docx_path, renderer_path):
    renderer = load_renderer(renderer_path)
    markdown = open(source_path, "rb").read().decode("utf-8")
    expected = expected_units(renderer, markdown)

    problems = []
    notes = []

    with zipfile.ZipFile(docx_path) as archive:
        bad = archive.testzip()
        if bad:
            problems.append("corrupt zip member: %s" % bad)
        names = archive.namelist()
        for part in REQUIRED_PARTS:
            if part not in names:
                problems.append("missing part: %s" % part)
        for part in names:
            if part.endswith(".xml") or part.endswith(".rels"):
                try:
                    ET.fromstring(archive.read(part))
                except ET.ParseError as exc:
                    problems.append("XML parse error in %s: %s" % (part, exc))
        notes.append("parts: %d, all XML well-formed" % len(names))

        root = ET.fromstring(archive.read("word/document.xml"))
        body = root.find(W + "body")
        if body is None or len(body) == 0:
            problems.append("body is empty")
        elif body[-1].tag != W + "sectPr":
            problems.append("body does not end with sectPr (ends with %s)" % body[-1].tag)

        for table in root.iter(W + "tbl"):
            children = [child.tag for child in table]
            if W + "tblPr" not in children:
                problems.append("a table has no tblPr")
            if W + "tblGrid" not in children:
                problems.append("a table has no tblGrid")
            for row in table.findall(W + "tr"):
                if not row.findall(W + "tc"):
                    problems.append("a table row has no cells")

        style_root = ET.fromstring(archive.read("word/styles.xml"))
        by_id = {style.get(W + "styleId"): style for style in style_root.iter(W + "style")}
        for level in (1, 2, 3):
            style = by_id.get("Heading%d" % level)
            if style is None:
                problems.append("Heading%d style missing" % level)
            elif style.find(".//" + W + "outlineLvl") is None:
                problems.append("Heading%d has no outlineLvl" % level)

        document = archive.read("word/document.xml").decode("utf-8")
        if 'w:fldCharType="begin"' not in document or " TOC " not in document:
            problems.append("no table-of-contents field")
        notes.append("structure: sectPr last, %d tables, Heading1-3 with outlineLvl, TOC field"
                     % len(list(root.iter(W + "tbl"))))

        actual = actual_units(body)

        cursor = 0
        missing = []
        for kind, text in expected:
            probe = norm(text)
            if not probe:
                continue
            found = -1
            for index in range(cursor, len(actual)):
                if actual[index] == probe or probe in actual[index]:
                    found = index
                    break
            if found < 0:
                missing.append((kind, probe[:90]))
            else:
                cursor = found + 1
        for kind, probe in missing[:8]:
            problems.append("missing %s unit: %r" % (kind, probe))
        notes.append("coverage: %d/%d source blocks matched, in order"
                     % (len(expected) - len(missing), len(expected)))

        flat = norm(" ".join(actual))
        for banned in BANNED:
            if banned in flat:
                problems.append("template instruction or markup leaked: %r" % banned)
        notes.append("no template instructions or raw markup in the text")

    print("DOCX  %s" % docx_path)
    print("MD    %s" % source_path)
    for note in notes:
        print("  ok   %s" % note)
    if problems:
        for problem in problems:
            print("  FAIL %s" % problem)
        return 1
    print("  ok   all checks passed")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", required=True, help="the markdown master")
    parser.add_argument("--docx", required=True, help="the built document")
    parser.add_argument("--renderer", default=DEFAULT_RENDERER,
                        help="the builder that produced the document")
    args = parser.parse_args()
    return verify(args.source, args.docx, args.renderer)


if __name__ == "__main__":
    sys.exit(main())
