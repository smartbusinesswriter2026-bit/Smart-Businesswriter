"""Build the Word copy of the conductor manual.

`docs/CONDUCTOR_MANUAL.md` is the master. This script renders it to
`docs/CONDUCTOR_MANUAL.docx` so the manual can be read, annotated and
re-circulated as a Word document, and so it can be rebuilt whenever the
master changes:

    python scripts/build_manual_docx.py

Stdlib only, deterministic output (fixed zip timestamps), and no change to the
paper renderer: `bp.product.docx` formats student papers, this formats a
reference document.

Typography is seeded from the product's own house style in
`bp/product/docx.py` - Times New Roman, the `F1F4F8` table header fill, the
`BFC8D6` table borders, Letter page and 1 inch margins - so a manual page and
a sample paper page read as one family. What is added on top is what a
reference document needs and a paper does not: real heading styles with
outline levels (so the Word navigation pane works), a table of contents field,
a running header and a footer with page numbers.

The markdown subset this reads is the subset the manual actually uses:
ATX headings, paragraphs, ordered and unordered lists with continuation lines
and one level of nesting, pipe tables, fenced code blocks, and inline bold,
italic and code spans.
"""

import argparse
import datetime
import hashlib
import os
import re
import zipfile
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "docs", "CONDUCTOR_MANUAL.md")
TARGET = os.path.join(ROOT, "docs", "CONDUCTOR_MANUAL.docx")

# House metrics, from bp/product/docx.py.
SERIF = "Times New Roman"
MONO = "Consolas"
BODY_SIZE = 22          # 11 pt
TABLE_SIZE = 19         # 9.5 pt
CODE_SIZE = 18          # 9 pt
HEADING_SIZE = 24       # 12 pt
LINE = 264              # 1.1 line spacing
TABLE_FILL = "F1F4F8"
TABLE_BORDER = "BFC8D6"
CODE_FILL = "F4F4F4"
INLINE_FILL = "F2F2F2"
GREY = "5A6472"
PAGE_W, PAGE_H = 12240, 15840
MARGIN = 1440
CONTENT_W = PAGE_W - 2 * MARGIN   # 9360 twips

# Table text metrics, used by `_column_widths` to decide how wide a column
# has to be. Twips per character, at the table's own sizes: Times New Roman
# at 9.5 pt is about half an em per character, Consolas at 9 pt is 0.55 em.
# A little air is added so a word that just fits is not broken by rounding.
SERIF_CHAR = 100
SERIF_BOLD_CHAR = 104
MONO_CHAR = 104
CELL_MARGIN = 216        # 108 left + 108 right
MIN_COLUMN = 900         # a column is never a sliver


# --------------------------------------------------------------------------
# Markdown parsing
# --------------------------------------------------------------------------

LIST_MARKER = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
# A code span, a bold run, or an italic run. The italic rule follows the
# usual convention: the opening `*` must be followed by a non-space and the
# closing `*` must be preceded by a non-space, so `*why*` is emphasis when it
# stands on its own but `2 * 3 * 4` is arithmetic.
INLINE_TOKEN = re.compile(
    r"(`[^`]+`|\*\*[^*]+\*\*|(?<!\*)\*(?=\S)([^*\n]+?)(?<=\S)\*(?!\*))")


def split_row(line):
    """Split a pipe table row into its cells."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip() for cell in text.split("|")]


def inline_runs(text):
    """Split a line into (text, bold, italic, code) runs."""
    runs = []
    position = 0
    for match in INLINE_TOKEN.finditer(text):
        if match.start() > position:
            runs.append((text[position:match.start()], False, False, False))
        token = match.group(0)
        if token.startswith("`"):
            runs.append((token[1:-1], False, False, True))
        elif token.startswith("**"):
            runs.append((token[2:-2], True, False, False))
        else:
            runs.append((token[1:-1], False, True, False))
        position = match.end()
    if position < len(text):
        runs.append((text[position:], False, False, False))
    return [run for run in runs if run[0]]


def parse_markdown(text):
    """Return the document as a list of blocks."""
    lines = text.split("\n")
    blocks = []
    index = 0
    total = len(lines)
    while index < total:
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if stripped.startswith("```"):
            index += 1
            body = []
            while index < total and not lines[index].strip().startswith("```"):
                body.append(lines[index].rstrip())
                index += 1
            index += 1
            blocks.append(("code", body))
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            blocks.append(("heading", len(heading.group(1)), heading.group(2).strip()))
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < total and TABLE_RULE.match(lines[index + 1]):
            header = split_row(lines[index])
            index += 2
            rows = []
            while index < total and lines[index].strip().startswith("|"):
                rows.append(split_row(lines[index]))
                index += 1
            blocks.append(("table", header, rows))
            continue

        if LIST_MARKER.match(line):
            items = []
            while index < total:
                match = LIST_MARKER.match(lines[index])
                if match:
                    indent = len(match.group(1))
                    marker = match.group(2)
                    level = 1 if indent < 2 else 2
                    content = match.group(3).strip()
                    index += 1
                    while index < total and lines[index].strip():
                        following = lines[index]
                        if LIST_MARKER.match(following):
                            break
                        continuation = re.match(r"^\s{2,}(\S.*)$", following)
                        if not continuation:
                            break
                        content += " " + continuation.group(1).strip()
                        index += 1
                    items.append([marker, level, content])
                    continue
                if items and re.match(r"^\s{2,}\S", lines[index]):
                    items[-1][2] += " " + lines[index].strip()
                    index += 1
                    continue
                break
            blocks.append(("list", items))
            continue

        paragraph = []
        while index < total and lines[index].strip():
            following = lines[index].strip()
            if LIST_MARKER.match(lines[index]) or following.startswith("|") \
                    or following.startswith("```"):
                break
            paragraph.append(following)
            index += 1
        if paragraph:
            blocks.append(("para", " ".join(paragraph)))
        else:
            index += 1
    return blocks


# --------------------------------------------------------------------------
# WordprocessingML
# --------------------------------------------------------------------------

def run_xml(text, bold=False, italic=False, code=False, color=None, size=None):
    """A run. Font and size come from the paragraph style, so only the inline
    differences are carried here and a style change still reaches every run."""
    properties = []
    if code:
        properties.append('<w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>' % (MONO, MONO, MONO))
        properties.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % INLINE_FILL)
    if bold:
        properties.append("<w:b/>")
    if italic:
        properties.append("<w:i/>")
    if color:
        properties.append('<w:color w:val="%s"/>' % color)
    if size:
        properties.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size))
    rpr = ("<w:rPr>%s</w:rPr>" % "".join(properties)) if properties else ""
    return ('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>'
            % (rpr, escape(text)))


def runs_xml(text, bold=False, italic=False):
    parts = []
    for chunk, is_bold, is_italic, is_code in inline_runs(text):
        parts.append(run_xml(chunk, bold=bold or is_bold, italic=italic or is_italic,
                             code=is_code))
    return "".join(parts)


def para_xml(runs, style=None, left=None, hanging=None, after=None, before=None,
             line=None, align=None, keep_next=False, shade=None):
    """A paragraph. The style carries the intent; direct properties appear only
    where the style cannot."""
    properties = []
    if style:
        properties.append('<w:pStyle w:val="%s"/>' % style)
    if keep_next:
        properties.append("<w:keepNext/>")
    if shade:
        properties.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade)
    if before is not None or after is not None or line is not None:
        bits = []
        if before is not None:
            bits.append('w:before="%d"' % before)
        if after is not None:
            bits.append('w:after="%d"' % after)
        if line is not None:
            bits.append('w:line="%d" w:lineRule="auto"' % line)
        properties.append("<w:spacing %s/>" % " ".join(bits))
    if left is not None and hanging is not None:
        properties.append('<w:ind w:left="%d" w:hanging="%d"/>' % (left, hanging))
    elif left is not None:
        properties.append('<w:ind w:left="%d"/>' % left)
    if align:
        properties.append('<w:jc w:val="%s"/>' % align)
    return ('<w:p><w:pPr>%s</w:pPr>%s</w:p>'
            % ("".join(properties), runs or run_xml("")))


def heading_xml(level, text):
    """A real heading style, so the navigation pane and the contents field work."""
    return ('<w:p><w:pPr><w:pStyle w:val="Heading%d"/></w:pPr>%s</w:p>'
            % (level, runs_xml(text)))


def cell_xml(text, width, header=False):
    shade = ('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % TABLE_FILL) if header else ""
    body = ('<w:p><w:pPr><w:pStyle w:val="%s"/></w:pPr>%s</w:p>'
            % ("TableHead" if header else "TableText", runs_xml(text)))
    return ('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>'
            '<w:tcBorders><w:top w:val="single" w:sz="4" w:color="%s"/>'
            '<w:left w:val="single" w:sz="4" w:color="%s"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="%s"/>'
            '<w:right w:val="single" w:sz="4" w:color="%s"/></w:tcBorders>%s'
            '<w:vAlign w:val="top"/></w:tcPr>%s</w:tc>'
            % (width, TABLE_BORDER, TABLE_BORDER, TABLE_BORDER, TABLE_BORDER, shade, body))


def _words_with_font(text):
    """(length, width-per-character) for every word in a cell.

    The width is carried per character so that an inline code span is
    measured in the monospace font it is actually set in, and the prose around
    it in the serif font. Measuring the whole cell in one font would
    under-count a cell that mixes the two.
    """
    words = []
    for chunk, is_bold, is_italic, is_code in inline_runs(text):
        if is_code:
            per_char = MONO_CHAR
        elif is_bold:
            per_char = SERIF_BOLD_CHAR
        else:
            per_char = SERIF_CHAR
        for word in chunk.split():
            words.append((len(word), per_char))
    return words


def _column_widths(header, rows):
    """Column widths that fit the content.

    Two rules, in order:

    1. A column is never so narrow that one of its own words has to be broken
       across two lines. A broken word is a defect the reader sees:
       `sources.py:4` on one line and `96` on the next is no longer a file
       reference. So every column is first given the width its longest single
       word needs.
    2. What is left of the page is shared out in proportion to how much text
       each column actually holds, so a column of prose gets more room than a
       column of one-word labels.

    When the columns cannot all have their longest word - a table with very
    long identifiers in every column - the widths are scaled down together
    and the table falls back to a proportional split.
    """
    columns = len(header) or 1
    minimum = [MIN_COLUMN] * columns
    weight = [0] * columns

    for index in range(columns):
        cells = [header[index] if index < len(header) else ""]
        cells.extend(row[index] for row in rows if index < len(row))
        for cell in cells:
            weight[index] += len(cell)
            for length, per_char in _words_with_font(cell):
                need = length * per_char + CELL_MARGIN
                if need > minimum[index]:
                    minimum[index] = need

    total = sum(minimum)
    if total <= CONTENT_W:
        spare = CONTENT_W - total
        weight_total = float(sum(weight)) or 1.0
        widths = [minimum[index] + int(spare * weight[index] / weight_total)
                  for index in range(columns)]
    else:
        # Not enough room for every longest word - a table with very long
        # identifiers in every column. Share the page out in proportion to
        # the minimum each column needs and let the longest tokens break.
        widths = [int(CONTENT_W * width / total) for width in minimum]
        deficit = CONTENT_W - sum(widths)
        order = sorted(range(columns), key=lambda index: widths[index], reverse=True)
        for index in order:
            if deficit <= 0:
                break
            take = min(deficit, widths[index] - 200)
            if take > 0:
                widths[index] += take
                deficit -= take

    # The last column absorbs the rounding, so the grid is exactly the text
    # width and Word has no reason to reflow the table.
    widths[-1] += CONTENT_W - sum(widths)
    return widths


def table_xml(header, rows):
    widths = _column_widths(header, rows)

    parts = ['<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/>'
             '<w:tblLayout w:type="fixed"/>'
             '<w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
             '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar>'
             '</w:tblPr><w:tblGrid>' % CONTENT_W]
    parts.extend('<w:gridCol w:w="%d"/>' % width for width in widths)
    parts.append("</w:tblGrid>")
    parts.append('<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>')
    parts.extend(cell_xml(header[index] if index < len(header) else "", widths[index], header=True)
                 for index in range(len(widths)))
    parts.append("</w:tr>")
    for row in rows:
        parts.append("<w:tr>")
        parts.extend(cell_xml(row[index] if index < len(row) else "", widths[index])
                     for index in range(len(widths)))
        parts.append("</w:tr>")
    parts.append("</w:tbl>")
    parts.append(para_xml("", after=120))
    return "".join(parts)


def code_xml(lines):
    """A single shaded cell, so the block reads as one box."""
    body = "".join(
        '<w:p><w:pPr><w:pStyle w:val="CodeLine"/></w:pPr>%s</w:p>' % run_xml(line or " ")
        for line in lines) or '<w:p><w:pPr><w:pStyle w:val="CodeLine"/></w:pPr>%s</w:p>' % run_xml(" ")
    return ('<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
            '<w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
            '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tblCellMar>'
            '</w:tblPr><w:tblGrid><w:gridCol w:w="%d"/></w:tblGrid>'
            '<w:tr><w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>'
            '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>'
            '<w:tcBorders><w:top w:val="single" w:sz="4" w:color="D8DCE3"/>'
            '<w:left w:val="single" w:sz="4" w:color="D8DCE3"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="D8DCE3"/>'
            '<w:right w:val="single" w:sz="4" w:color="D8DCE3"/></w:tcBorders>'
            '</w:tcPr>%s</w:tc></w:tr></w:tbl>' % (CONTENT_W, CONTENT_W, CONTENT_W,
                                                    CODE_FILL, body)
            + '<w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr></w:p>')


def list_xml(items):
    parts = []
    counter = 0
    for marker, level, content in items:
        if marker[0].isdigit():
            counter += 1
            label = "%d." % counter
        else:
            label = "\u2022" if level == 1 else "\u2013"
        parts.append('<w:p><w:pPr><w:pStyle w:val="ListIndent%d"/></w:pPr>%s</w:p>'
                     % (level, run_xml(label + "  ") + runs_xml(content)))
    return "".join(parts)


def cover_xml(title, stamp_lines, subtitle):
    parts = ['<w:p><w:pPr><w:pStyle w:val="CoverTitle"/></w:pPr>%s</w:p>' % run_xml(title)]
    parts.append('<w:p><w:pPr><w:pStyle w:val="CoverSubtitle"/></w:pPr>%s</w:p>'
                 % run_xml(subtitle))
    for line in stamp_lines:
        parts.append('<w:p><w:pPr><w:pStyle w:val="CoverStamp"/></w:pPr>%s</w:p>' % run_xml(line))
    parts.append('<w:p><w:pPr><w:pStyle w:val="CoverGap"/></w:pPr></w:p>')
    parts.append('<w:p><w:pPr><w:pStyle w:val="CoverContents"/></w:pPr>%s</w:p>'
                 % run_xml("Contents"))
    parts.append(
        '<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> TOC \\o "2-3" \\h \\z \\u </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        + run_xml("Right-click here and choose \u201cUpdate Field\u201d to build the "
                  "table of contents.", italic=True, color=GREY) +
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
    parts.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
    return "".join(parts)


def body_xml(blocks, title, stamp_lines, subtitle):
    parts = [cover_xml(title, stamp_lines, subtitle)]
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            parts.append(heading_xml(min(block[1], 3), block[2]))
        elif kind == "para":
            parts.append('<w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr>%s</w:p>'
                         % runs_xml(block[1]))
        elif kind == "list":
            parts.append(list_xml(block[1]))
        elif kind == "table":
            parts.append(table_xml(block[1], block[2]))
        elif kind == "code":
            parts.append(code_xml(block[1]))
    return "".join(parts)


DOCUMENT_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<w:body>%s"
    '<w:sectPr><w:headerReference w:type="default" r:id="rId4"/>'
    '<w:footerReference w:type="default" r:id="rId5"/>'
    '<w:pgSz w:w="%d" w:h="%d"/>'
    '<w:pgMar w:top="%d" w:right="%d" w:bottom="%d" w:left="%d" '
    'w:header="720" w:footer="720" w:gutter="0"/>'
    '<w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr>'
    "</w:body></w:document>")


def styles_xml():
    def heading(level, size, italic, align):
        return ('<w:style w:type="paragraph" w:styleId="Heading%d"><w:name w:val="heading %d"/>'
                '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
                '<w:pPr><w:keepNext/><w:spacing w:before="%d" w:after="120" w:line="%d" '
                'w:lineRule="auto"/><w:jc w:val="%s"/><w:outlineLvl w:val="%d"/></w:pPr>'
                '<w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s"/>%s<w:sz w:val="%d"/>'
                '<w:szCs w:val="%d"/></w:rPr></w:style>'
                % (level, level, 280 if level == 1 else 200, LINE, align, level - 1,
                   SERIF, SERIF, "<w:i/>" if italic else "", size, size))

    toc = "".join(
        '<w:style w:type="paragraph" w:styleId="TOC%d"><w:name w:val="toc %d"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
        '<w:pPr><w:spacing w:after="60" w:line="%d" w:lineRule="auto"/>'
        '<w:ind w:left="%d"/></w:pPr></w:style>' % (level, level, LINE, (level - 1) * 360)
        for level in (1, 2, 3))

    def named(style_id, name, paragraph_props="", run_props="", based="Normal"):
        return ('<w:style w:type="paragraph" w:styleId="%s"><w:name w:val="%s"/>'
                '<w:basedOn w:val="%s"/><w:next w:val="%s"/><w:qFormat/>'
                "<w:pPr>%s</w:pPr><w:rPr>%s</w:rPr></w:style>"
                % (style_id, name, based, based, paragraph_props, run_props))

    font = '<w:rFonts w:ascii="%s" w:hAnsi="%s"/>' % (SERIF, SERIF)
    mono = '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>' % (MONO, MONO, MONO)

    extra = "".join([
        named("BodyText", "Body Text",
              '<w:spacing w:before="0" w:after="140" w:line="%d" w:lineRule="auto"/>'
              '<w:jc w:val="left"/>' % LINE,
              font + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (BODY_SIZE, BODY_SIZE)),
        named("ListIndent1", "List Indent 1",
              '<w:spacing w:before="0" w:after="80" w:line="%d" w:lineRule="auto"/>'
              '<w:ind w:left="360" w:hanging="360"/><w:jc w:val="left"/>' % LINE,
              font + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (BODY_SIZE, BODY_SIZE)),
        named("ListIndent2", "List Indent 2",
              '<w:spacing w:before="0" w:after="80" w:line="%d" w:lineRule="auto"/>'
              '<w:ind w:left="720" w:hanging="360"/><w:jc w:val="left"/>' % LINE,
              font + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (BODY_SIZE, BODY_SIZE)),
        named("CodeLine", "Code Line",
              '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
              '<w:jc w:val="left"/>',
              mono + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (CODE_SIZE, CODE_SIZE)),
        named("TableText", "Table Text",
              '<w:spacing w:before="0" w:after="40" w:line="240" w:lineRule="auto"/>'
              '<w:jc w:val="left"/>',
              font + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (TABLE_SIZE, TABLE_SIZE)),
        named("TableHead", "Table Head",
              '<w:spacing w:before="0" w:after="40" w:line="240" w:lineRule="auto"/>'
              '<w:jc w:val="left"/>',
              font + "<w:b/>" + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>'
              % (TABLE_SIZE, TABLE_SIZE)),
        named("CoverTitle", "Cover Title",
              '<w:spacing w:before="2400" w:after="120" w:line="280" w:lineRule="auto"/>'
              '<w:jc w:val="center"/>',
              font + "<w:b/>" + '<w:sz w:val="40"/><w:szCs w:val="40"/>'),
        named("CoverSubtitle", "Cover Subtitle",
              '<w:spacing w:before="0" w:after="360" w:line="264" w:lineRule="auto"/>'
              '<w:jc w:val="center"/>',
              font + "<w:i/>" + '<w:color w:val="%s"/>' % GREY
              + '<w:sz w:val="24"/><w:szCs w:val="24"/>'),
        named("CoverStamp", "Cover Stamp",
              '<w:spacing w:before="0" w:after="40" w:line="264" w:lineRule="auto"/>'
              '<w:jc w:val="center"/>',
              font + '<w:color w:val="%s"/>' % GREY
              + '<w:sz w:val="19"/><w:szCs w:val="19"/>'),
        named("CoverGap", "Cover Gap",
              '<w:spacing w:before="0" w:after="360" w:line="264" w:lineRule="auto"/>',
              font + '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (BODY_SIZE, BODY_SIZE)),
        named("CoverContents", "Cover Contents",
              '<w:spacing w:before="0" w:after="120" w:line="264" w:lineRule="auto"/>'
              '<w:jc w:val="center"/><w:keepNext/>',
              font + "<w:b/>" + '<w:sz w:val="28"/><w:szCs w:val="28"/>'),
    ])

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:docDefaults><w:rPrDefault><w:rPr>"
            '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>'
            '<w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr></w:rPrDefault>'
            '<w:pPrDefault><w:pPr><w:spacing w:line="%d" w:lineRule="auto" w:after="0"/>'
            "</w:pPr></w:pPrDefault></w:docDefaults>"
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:name w:val="Normal"/><w:pPr><w:spacing w:line="%d" w:lineRule="auto" '
            'w:after="140"/><w:jc w:val="left"/></w:pPr>'
            "<w:rPr>%s<w:sz w:val=\"%d\"/><w:szCs w:val=\"%d\"/></w:rPr></w:style>"
            "%s%s%s%s</w:styles>"
            % (SERIF, SERIF, SERIF, BODY_SIZE, BODY_SIZE, LINE, LINE,
               font, BODY_SIZE, BODY_SIZE,
               heading(1, HEADING_SIZE, False, "center"),
               heading(2, HEADING_SIZE, False, "left") + heading(3, HEADING_SIZE, True, "left"),
               toc, extra))


SETTINGS_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:updateFields w:val="true"/>'
                '<w:defaultTabStop w:val="720"/></w:settings>')

HEADER_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
              '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
              '<w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="%d"/></w:tabs>'
              '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
              '<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="4" w:color="%s"/></w:pBdr>'
              '</w:pPr>%s</w:p>'
              "</w:hdr>"
              % (CONTENT_W, TABLE_BORDER,
                 run_xml("Conductor manual \u2014 how the chat builds a paper",
                         size=18, color=GREY)))


def header_xml(text):
    """The running header. The text is the manual's own name, so a manual that
    is not the conductor manual does not carry the conductor manual's header."""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="%d"/></w:tabs>'
            '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
            '<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="4" w:color="%s"/></w:pBdr>'
            '</w:pPr>%s</w:p>'
            "</w:hdr>"
            % (CONTENT_W, TABLE_BORDER, run_xml(text, size=18, color=GREY)))


def footer_xml(stamp):
    field = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
             '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
             '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
             + run_xml("1", size=18, color=GREY) +
             '<w:r><w:fldChar w:fldCharType="end"/></w:r>')
    total = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
             '<w:r><w:instrText xml:space="preserve"> NUMPAGES </w:instrText></w:r>'
             '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
             + run_xml("1", size=18, color=GREY) +
             '<w:r><w:fldChar w:fldCharType="end"/></w:r>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="%d"/></w:tabs>'
            '<w:spacing w:before="80" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
            "%s"
            '<w:r><w:tab/></w:r>'
            "%s"
            '<w:r><w:t xml:space="preserve"> of </w:t></w:r>%s'
            "</w:p></w:ftr>"
            % (CONTENT_W, run_xml(stamp, size=18, color=GREY), field, total))


CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
    '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
    '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    "</Types>")

ROOT_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    "</Relationships>")

DOCUMENT_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
    '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
    '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
    "</Relationships>")

CORE_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<dc:title>%s</dc:title><dc:creator>Smart Business Writer</dc:creator>"
    "<cp:lastModifiedBy>scripts/build_manual_docx.py</cp:lastModifiedBy>"
    '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
    '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>'
    "</cp:coreProperties>")


def build(source=SOURCE, target=TARGET, header=None, subtitle=None):
    raw = open(source, "rb").read()
    text = raw.decode("utf-8")
    source_sha = hashlib.sha256(raw).hexdigest()
    blocks = parse_markdown(text)

    title = "Conductor manual"
    for block in blocks:
        if block[0] == "heading" and block[1] == 1:
            title = block[2]
            break

    running_header = header or "Conductor manual \u2014 how the chat builds a paper"
    cover_subtitle = subtitle or "Smart Business Writer \u2014 operating manual for the chat"

    now = datetime.datetime.now(datetime.timezone.utc)

    def _label(path):
        """A readable path for the footer: repo-relative when it is in the repo."""
        try:
            relative = os.path.relpath(path, ROOT).replace("\\", "/")
        except ValueError:                      # a different drive
            relative = ""
        if not relative or relative.startswith(".."):
            return os.path.abspath(path).replace("\\", "/")
        return relative

    source_label = _label(source)
    target_label = _label(target)
    stamp = "%s \u00b7 sha256 %s" % (source_label, source_sha[:12])
    rebuild = "python scripts/build_manual_docx.py"
    if (os.path.abspath(source), os.path.abspath(target)) != (os.path.abspath(SOURCE), os.path.abspath(TARGET)):
        rebuild += " --source %s --target %s" % (source_label, target_label)
    if header:
        rebuild += " --header \"%s\"" % header
    if subtitle:
        rebuild += " --subtitle \"%s\"" % subtitle
    stamp_lines = [
        "Built from %s (sha256 %s)" % (source_label, source_sha[:12]),
        "%d blocks \u00b7 %d headings \u00b7 %d tables"
        % (len(blocks),
           sum(1 for b in blocks if b[0] == "heading"),
           sum(1 for b in blocks if b[0] == "table")),
        "Rebuild with: %s" % rebuild,
        "Generated %s" % now.strftime("%d %B %Y, %H:%M UTC"),
    ]

    body = body_xml(blocks, title, stamp_lines, cover_subtitle)
    document = DOCUMENT_XML % (body, PAGE_W, PAGE_H, MARGIN, MARGIN, MARGIN, MARGIN)
    created = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    parts = (
        ("[Content_Types].xml", CONTENT_TYPES_XML),
        ("_rels/.rels", ROOT_RELS_XML),
        ("word/document.xml", document),
        ("word/_rels/document.xml.rels", DOCUMENT_RELS_XML),
        ("word/styles.xml", styles_xml()),
        ("word/settings.xml", SETTINGS_XML),
        ("word/header1.xml", header_xml(running_header)),
        ("word/footer1.xml", footer_xml(stamp)),
        ("docProps/core.xml", CORE_XML % (escape(title), created, created)),
    )

    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in parts:
            archive.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), payload)

    data = open(target, "rb").read()
    return {
        "source": source,
        "target": target,
        "source_sha256": source_sha,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "blocks": len(blocks),
        "headings": sum(1 for b in blocks if b[0] == "heading"),
        "tables": sum(1 for b in blocks if b[0] == "table"),
        "lists": sum(1 for b in blocks if b[0] == "list"),
        "code_blocks": sum(1 for b in blocks if b[0] == "code"),
        "paragraphs": sum(1 for b in blocks if b[0] == "para"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--target", default=TARGET)
    parser.add_argument("--header", default=None,
                        help="the running header; defaults to the conductor manual's")
    parser.add_argument("--subtitle", default=None,
                        help="the cover subtitle; defaults to the conductor manual's")
    args = parser.parse_args()
    report = build(args.source, args.target, args.header, args.subtitle)
    for key in ("target", "bytes", "sha256", "source_sha256", "blocks", "headings",
                "tables", "lists", "code_blocks", "paragraphs"):
        print("%-14s %s" % (key, report[key]))


if __name__ == "__main__":
    main()
