"""A slide deck as a real .pptx, written by hand (product layer, standard library only).

A deck is not a paper in landscape.  It is a **sequence of claims**, each slide
arguing one sentence, with a figure when the figure is the argument.  So the
unit here is a slide with a claim, not a section with paragraphs.

    slide = {"layout": "title" | "claim" | "figure" | "section",
             "claim": "Revenue grew on renewals",     # the sentence the slide argues
             "bullets": ["...", "..."],               # optional support
             "figure": "fig_ab12cd34ef56",            # a figure id, never a copy
             "note": "Source: stored artifacts",      # optional
             "subtitle": "..."}                       # title slide only

Two rules are enforced in code:

* **every content slide carries a claim** - a slide with no claim is a bullet
  list, and a bullet list is a document;
* **a slide names its figure by id** - the deck resolves it from the registry,
  so the deck and the paper cannot show two different numbers for one chart.

The package is the minimum PowerPoint needs, in the order the schema requires:
presentation, master, one blank layout, one theme, then the slides and their
media.  A missing picture is not fatal: the slide prints the figure's stored
values instead, so a deck never ships a broken image.
"""

import base64
import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from hashlib import sha256
from xml.sax.saxutils import escape

from . import docx, theme

DECK_FORMAT = "bp-deck/1"
LAYOUTS = ("title", "claim", "figure", "section", "table")

#: 16:9, in EMU.
SLIDE_W, SLIDE_H = 12192000, 6858000
MARGIN = 838200
CONTENT_W = SLIDE_W - 2 * MARGIN
HEAD_Y, HEAD_H = 500000, 1000000
RULE_Y = 1560000
BODY_Y = 1800000
BODY_H = SLIDE_H - BODY_Y - 500000

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')


class DeckError(ValueError):
    """The deck cannot be built as declared."""


def slide(layout, claim=None, bullets=None, figure=None, note=None, subtitle=None,
          notes=None, transition="fade", table=None):
    """One slide.  `claim` is required for every layout except the title slide."""
    if layout not in LAYOUTS:
        raise DeckError("slide layout must be one of: " + ", ".join(LAYOUTS))
    if layout != "title" and not (isinstance(claim, str) and claim.strip()):
        raise DeckError("a %s slide needs a claim: the sentence the slide argues" % layout)
    if transition not in (None, "", "none", "fade"):
        raise DeckError("transition must be 'fade' or 'none'")
    return {"layout": layout, "claim": (claim or "").strip(),
            "bullets": [str(item).strip() for item in (bullets or []) if str(item).strip()],
            "figure": figure, "note": (note or "").strip(),
            "subtitle": (subtitle or "").strip(),
            "notes": (notes or "").strip(), "transition": transition,
            "table": table}


def validate(deck, figures=None):
    """Check the deck, and that every figure it names exists."""
    if not isinstance(deck, dict):
        raise DeckError("deck must be an object")
    if deck.get("format", DECK_FORMAT) != DECK_FORMAT:
        raise DeckError("unsupported deck format %r, expected %r"
                        % (deck.get("format"), DECK_FORMAT))
    slides = deck.get("slides")
    if not isinstance(slides, list) or not slides:
        raise DeckError("a deck needs a non-empty 'slides' list")
    known = None
    if figures is not None:
        known = {figure["id"] for figure in figures}
    for index, item in enumerate(slides, 1):
        if not isinstance(item, dict):
            raise DeckError("slides[%d] must be an object" % (index - 1))
        if item.get("layout") not in LAYOUTS:
            raise DeckError("slides[%d] layout must be one of: %s"
                            % (index - 1, ", ".join(LAYOUTS)))
        if item["layout"] != "title" and not str(item.get("claim") or "").strip():
            raise DeckError("slides[%d] needs a claim" % (index - 1))
        for key in ("figure", "table"):
            identifier = item.get(key)
            if identifier and known is not None and identifier not in known:
                raise DeckError("slides[%d] names figure %r, which this case does not hold"
                                % (index - 1, identifier))
    return deck


def _ink():
    return theme.TOKENS["palette"]["ink"].lstrip("#").upper()


def _accent():
    return theme.TOKENS["palette"]["accent"].lstrip("#").upper()


def _run(text, size=1800, bold=False, colour=None):
    return ('<a:r><a:rPr lang="en-US" sz="%d" b="%d" dirty="0">'
            '<a:solidFill><a:srgbClr val="%s"/></a:solidFill>'
            '<a:latin typeface="Georgia"/></a:rPr><a:t>%s</a:t></a:r>'
            % (size, 1 if bold else 0, colour or _ink(), escape(str(text))))


def _paragraphs(items, size=1800, bold=False, bullet=False, colour=None):
    parts = []
    for text in items:
        ppr = ('<a:pPr marL="342900" indent="-285750"><a:buFont typeface="Arial"/>'
               '<a:buChar char="&#8226;"/></a:pPr>' if bullet else "")
        parts.append("<a:p>%s%s</a:p>" % (ppr, _run(text, size=size, bold=bold, colour=colour)))
    return "".join(parts)


def _textbox(shape_id, name, x, y, cx, cy, body):
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            '<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>%s</p:txBody></p:sp>'
            % (shape_id, escape(name), x, y, cx, cy, body))


def _rule(shape_id, x, y, cx, cy):
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="Rule"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            '<a:solidFill><a:srgbClr val="%s"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>'
            % (shape_id, x, y, cx, cy, _accent()))


def _picture(shape_id, rel_id, name, x, y, cx, cy):
    return ('<p:pic><p:nvPicPr><p:cNvPr id="%d" name="%s"/><p:cNvPicPr>'
            '<a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            '<p:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
            % (shape_id, escape(name), rel_id, x, y, cx, cy))


def _slide_xml(shapes, transition="fade"):
    effect = "" if transition in (None, "", "none") else "<p:transition><p:fade/></p:transition>"
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld %s><p:cSld><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            '%s</p:spTree></p:cSld>'
            '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>%s</p:sld>'
            % (NS, shapes, effect))


def _fit(picture, box_w, box_h):
    """The picture's size inside a box, preserving its aspect ratio."""
    size = docx._png_size(picture)
    if not size:
        return box_w, int(box_w * 0.42)
    width, height = size
    scale = min(box_w / float(width), box_h / float(height))
    return int(width * scale), int(height * scale)


def _table_frame(shape_id, table, x, y, cx, cy):
    """A native PowerPoint table, so the cells stay editable on the slide."""
    columns = [str(column) for column in table.get("columns") or []]
    rows = table.get("rows") or []
    if not columns:
        return ""
    column_width = cx // len(columns)
    header_height, row_height = 420000, 360000
    height = header_height + row_height * len(rows)
    height = min(height, cy)

    def cell(text, bold=False, fill=None):
        shading = ('<a:solidFill><a:srgbClr val="%s"/></a:solidFill>' % fill) if fill else ""
        return ('<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r>'
                '<a:rPr lang="en-US" sz="1400" b="%d" dirty="0">'
                '<a:solidFill><a:srgbClr val="%s"/></a:solidFill>'
                '<a:latin typeface="Georgia"/></a:rPr><a:t>%s</a:t></a:r></a:p></a:txBody>'
                '<a:tcPr marL="91440" marR="91440" marT="45720" marB="45720">%s</a:tcPr></a:tc>'
                % (1 if bold else 0, _ink(), escape(str(text)), shading))

    grid = "".join('<a:gridCol w="%d"/>' % column_width for _ in columns)
    header = "<a:tr h=\"%d\">%s</a:tr>" % (
        header_height, "".join(cell(column, bold=True, fill="E8EDF4") for column in columns))
    body = "".join("<a:tr h=\"%d\">%s</a:tr>" % (row_height, "".join(cell(value) for value in row))
                   for row in rows)
    return ('<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="%d" name="Table"/>'
            '<p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr>'
            '<p:nvPr/></p:nvGraphicFramePr>'
            '<p:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></p:xfrm>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
            '<a:tbl><a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>%s</a:tblGrid>%s%s</a:tbl>'
            '</a:graphicData></a:graphic></p:graphicFrame>'
            % (shape_id, x, y, cx, height, grid, header, body))


def _shapes_for(item, figures, media):
    """The shapes of one slide, and the media it adds."""
    layout = item["layout"]
    shapes = []
    images = []
    if layout == "title":
        shapes.append(_textbox(2, "Title", MARGIN, 2200000, CONTENT_W, 1500000,
                               _paragraphs([item["claim"] or item.get("subtitle") or "Untitled"],
                                           size=4000, bold=True)))
        if item.get("subtitle"):
            shapes.append(_textbox(3, "Subtitle", MARGIN, 3800000, CONTENT_W, 900000,
                                   _paragraphs([item["subtitle"]], size=1800)))
        return shapes, images

    shapes.append(_textbox(2, "Claim", MARGIN, HEAD_Y, CONTENT_W, HEAD_H,
                           _paragraphs([item["claim"]], size=2800, bold=True)))
    shapes.append(_rule(3, MARGIN, RULE_Y, 1200000, 36000))

    if layout == "table":
        record = (figures or {}).get(item.get("table")) if item.get("table") else None
        table = (record or {}).get("table")
        if table:
            shapes.append(_table_frame(4, table, MARGIN, BODY_Y, CONTENT_W, BODY_H))
        else:
            shapes.append(_textbox(4, "Table", MARGIN, BODY_Y, CONTENT_W, 400000,
                                   _paragraphs(["This table is not recorded in this case."],
                                               size=1400)))
        return shapes, images

    figure = (figures or {}).get(item.get("figure")) if item.get("figure") else None
    picture = (figure or {}).get("asset", {}).get("png") if figure else None
    if layout == "figure" and picture:
        width, height = _fit(picture, CONTENT_W, BODY_H - 400000)
        name = "image%d.png" % (len(media) + 1)
        media.append((name, picture))
        images.append(name)
        x = MARGIN + (CONTENT_W - width) // 2
        shapes.append(_picture(4, "rId2", "Figure", x, BODY_Y, width, height))
        if item.get("note"):
            shapes.append(_textbox(5, "Note", MARGIN, BODY_Y + height + 60000,
                                   CONTENT_W, 400000,
                                   _paragraphs([item["note"]], size=1100)))
        return shapes, images

    bullets = list(item.get("bullets") or [])
    if layout == "figure" and figure:
        # no rasterizer: the figure's stored values are the slide, never a broken image
        for label, value in figure.get("rows") or []:
            bullets.append("%s: %s" % (label, value))
    if bullets:
        shapes.append(_textbox(4, "Body", MARGIN, BODY_Y, CONTENT_W, BODY_H,
                               _paragraphs(bullets, size=1800, bullet=True)))
    if item.get("note"):
        shapes.append(_textbox(5, "Note", MARGIN, SLIDE_H - 700000, CONTENT_W, 400000,
                               _paragraphs([item["note"]], size=1100)))
    return shapes, images


# --- the package -----------------------------------------------------------

THEME_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="BP">
<a:themeElements>
<a:clrScheme name="BP">
<a:dk1><a:srgbClr val="1B1B1B"/></a:dk1><a:lt1><a:srgbClr val="FDFDFB"/></a:lt1>
<a:dk2><a:srgbClr val="555550"/></a:dk2><a:lt2><a:srgbClr val="E6E6E1"/></a:lt2>
<a:accent1><a:srgbClr val="4E79A7"/></a:accent1><a:accent2><a:srgbClr val="F28E2B"/></a:accent2>
<a:accent3><a:srgbClr val="E15759"/></a:accent3><a:accent4><a:srgbClr val="76B7B2"/></a:accent4>
<a:accent5><a:srgbClr val="59A14F"/></a:accent5><a:accent6><a:srgbClr val="EDC948"/></a:accent6>
<a:hlink><a:srgbClr val="4E79A7"/></a:hlink><a:folHlink><a:srgbClr val="B07AA1"/></a:folHlink>
</a:clrScheme>
<a:fontScheme name="BP">
<a:majorFont><a:latin typeface="Georgia"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
<a:minorFont><a:latin typeface="Georgia"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
</a:fontScheme>
<a:fmtScheme name="BP">
<a:fillStyleLst>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
</a:fillStyleLst>
<a:lnStyleLst>
<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
<a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
<a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
</a:lnStyleLst>
<a:effectStyleLst>
<a:effectStyle><a:effectLst/></a:effectStyle>
<a:effectStyle><a:effectLst/></a:effectStyle>
<a:effectStyle><a:effectLst/></a:effectStyle>
</a:effectStyleLst>
<a:bgFillStyleLst>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
</a:bgFillStyleLst>
</a:fmtScheme>
</a:themeElements>
</a:theme>"""

SPTREE = ('<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/>'
          '</p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
          '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree>')

MASTER_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<p:sldMaster %s><p:cSld>%s</p:cSld>'
              '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
              'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
              'accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
              '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
              '</p:sldMaster>' % (NS, SPTREE))

LAYOUT_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<p:sldLayout %s type="blank" preserve="1"><p:cSld name="Blank">%s</p:cSld>'
              '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
              % (NS, SPTREE))

PRESENTATION_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation %s>
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
%s<p:sldIdLst>%s</p:sldIdLst>
<p:sldSz cx="%d" cy="%d"/><p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""


def _content_types(count, images, notes=0):
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
    ]
    overrides.extend(
        '<Override PartName="/ppt/slides/slide%d.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' % index
        for index in range(1, count + 1))
    if notes:
        overrides.append(
            '<Override PartName="/ppt/notesMasters/notesMaster1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml"/>')
        overrides.extend(
            '<Override PartName="/ppt/notesSlides/notesSlide%d.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>' % index
            for index in range(1, notes + 1))
    png = '<Default Extension="png" ContentType="image/png"/>' if images else ""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>' + png
            + "".join(overrides) + "</Types>")


def _root_rels():
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="ppt/presentation.xml"/></Relationships>')


def _presentation_rels(count, notes=False):
    parts = ['<Relationship Id="rId1" '
             'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
             'Target="slideMasters/slideMaster1.xml"/>']
    parts.extend(
        '<Relationship Id="rId%d" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        'Target="slides/slide%d.xml"/>' % (index + 1, index)
        for index in range(1, count + 1))
    if notes:
        parts.append('<Relationship Id="rId%d" '
                     'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" '
                     'Target="notesMasters/notesMaster1.xml"/>' % (count + 2))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(parts) + "</Relationships>")


def _master_rels():
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
            'Target="../slideLayouts/slideLayout1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
            'Target="../theme/theme1.xml"/></Relationships>')


def _layout_rels():
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
            'Target="../slideMasters/slideMaster1.xml"/></Relationships>')


def _slide_rels(images, notes_order=None):
    parts = ['<Relationship Id="rId1" '
             'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
             'Target="../slideLayouts/slideLayout1.xml"/>']
    parts.extend(
        '<Relationship Id="rId%d" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        'Target="../media/%s"/>' % (index + 2, name)
        for index, name in enumerate(images))
    if notes_order:
        parts.append('<Relationship Id="rId%d" '
                     'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" '
                     'Target="../notesSlides/notesSlide%d.xml"/>' % (len(images) + 2, notes_order))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(parts) + "</Relationships>")


NOTES_MASTER_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<p:notesMaster %s><p:cSld><p:spTree>'
                    '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
                    '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
                    '</p:spTree></p:cSld>'
                    '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
                    'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
                    'accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
                    '</p:notesMaster>' % NS)


def _notes_master_rels():
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
            'Target="../theme/theme1.xml"/></Relationships>')


def _notes_slide_xml(text):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:notes %s><p:cSld><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Notes"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="685800" y="1143000"/>'
            '<a:ext cx="5486400" cy="4114800"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            '<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>%s</p:txBody></p:sp>'
            '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>'
            % (NS, _paragraphs([line for line in str(text).splitlines() if line.strip()], size=1400)))


def _notes_slide_rels(slide_index):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" '
            'Target="../notesMasters/notesMaster1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            'Target="../slides/slide%d.xml"/></Relationships>' % slide_index)


def render(deck, figures=None):
    """The whole deck as .pptx bytes, deterministic for the same input."""
    figures = figures or {}
    validate(deck, list(figures.values()) if isinstance(figures, dict) else figures)
    slides = deck["slides"]
    media = []
    bodies, rels = [], []
    notes_bodies, notes_links = [], []
    for index, item in enumerate(slides, start=1):
        shapes, images = _shapes_for(item, figures, media)
        note = str(item.get("notes") or "").strip()
        notes_order = None
        if note:
            notes_order = len(notes_bodies) + 1
            notes_bodies.append(_notes_slide_xml(note))
            notes_links.append(index)
        bodies.append(_slide_xml("".join(shapes), item.get("transition")))
        rels.append(_slide_rels(images, notes_order))

    ids = "".join('<p:sldId id="%d" r:id="rId%d"/>' % (256 + index, index + 2)
                  for index in range(len(slides)))
    notes_master = ('<p:notesMasterIdLst><p:notesMasterId r:id="rId%d"/></p:notesMasterIdLst>'
                    % (len(slides) + 2) if notes_bodies else "")
    parts = [
        ("[Content_Types].xml", _content_types(len(slides), media, len(notes_bodies))),
        ("_rels/.rels", _root_rels()),
        ("ppt/presentation.xml",
         PRESENTATION_XML % (NS, notes_master, ids, SLIDE_W, SLIDE_H)),
        ("ppt/_rels/presentation.xml.rels",
         _presentation_rels(len(slides), bool(notes_bodies))),
        ("ppt/slideMasters/slideMaster1.xml", MASTER_XML),
        ("ppt/slideMasters/_rels/slideMaster1.xml.rels", _master_rels()),
        ("ppt/slideLayouts/slideLayout1.xml", LAYOUT_XML),
        ("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _layout_rels()),
        ("ppt/theme/theme1.xml", THEME_XML),
    ]
    for index, body in enumerate(bodies, 1):
        parts.append(("ppt/slides/slide%d.xml" % index, body))
        parts.append(("ppt/slides/_rels/slide%d.xml.rels" % index, rels[index - 1]))
    if notes_bodies:
        parts.append(("ppt/notesMasters/notesMaster1.xml", NOTES_MASTER_XML))
        parts.append(("ppt/notesMasters/_rels/notesMaster1.xml.rels", _notes_master_rels()))
        for index, body in enumerate(notes_bodies, 1):
            parts.append(("ppt/notesSlides/notesSlide%d.xml" % index, body))
            parts.append(("ppt/notesSlides/_rels/notesSlide%d.xml.rels" % index,
                          _notes_slide_rels(notes_links[index - 1])))
    parts.extend(("ppt/media/" + name, data) for name, data in media)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts:
            archive.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), data)
    return buf.getvalue()


def render_file(built, figures, path):
    """Write the deck and return its path, SHA-256 and size."""
    data = render(built, figures)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as stream:
        stream.write(data)
    return {"path": path, "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def from_sections(sections, title, figures=None):
    """A starter deck from a paper's sections: one claim slide per heading.

    This is deliberately thin.  It gives an owner a deck to edit, and it never
    invents a claim: a heading with no first sentence becomes a section slide.
    """
    slides = [slide("title", claim=title, subtitle="Draft deck")]
    for item in sections or []:
        if not isinstance(item, dict):
            continue
        heading = str(item.get("heading") or "").strip()
        if not heading:
            continue
        first = next((str(line).strip() for line in item.get("lines") or []
                      if str(line).strip()), "")
        figure = item.get("figure")
        if figure and figure.get("id"):
            if figure.get("kind") == "table":
                slides.append(slide("table", claim=heading, table=figure["id"],
                                    note=str(figure.get("note") or "")))
            else:
                slides.append(slide("figure", claim=heading, figure=figure["id"],
                                    note=str(figure.get("note") or "")))
        elif first:
            slides.append(slide("claim", claim=heading, bullets=[first]))
        else:
            slides.append(slide("section", claim=heading))
    return {"format": DECK_FORMAT, "title": title, "slides": slides}

#: The pitch order: a deck argues one case, in this sequence.
PITCH_ROLES = (
    ("problem", ("introduction", "problem", "context", "background", "brief")),
    ("evidence", ("analysis", "evidence", "findings", "research", "market", "industry")),
    ("position", ("discussion", "integration", "position", "strategy", "framework")),
    ("financials", ("financial", "computation", "break-even", "break even", "feasibility",
                    "cost", "npv", "valuation", "budget")),
    ("risks", ("limitation", "risk", "assumption", "honesty", "uncertainty")),
    ("ask", ("implication", "recommendation", "conclusion", "decision", "ask", "next step")),
)


def _first_sentence(text):
    """The sentence a slide argues: the paper's own first sentence, never a rewrite."""
    text = str(text or "").strip()
    if not text:
        return ""
    import re
    match = re.search(r"[.!?](\s|$)", text)
    return text[:match.end()].strip() if match else text


def from_paper(sections, title):
    """A pitch deck from a paper: the paper's own sentences, in a pitch order.

    The slides are the student's words, reordered.  Nothing is written for them:
    a slide's claim is the first sentence of the section, its bullets are the next
    few, and its speaker notes are the section's full text.
    """
    found = {}
    for item in sections or []:
        if not isinstance(item, dict):
            continue
        heading = str(item.get("heading") or "").strip().lower()
        for role, cues in PITCH_ROLES:
            if role in found:
                continue
            if any(cue in heading for cue in cues):
                found[role] = item
                break
    slides = [slide("title", claim=title, subtitle="Pitch deck")]
    for role, _cues in PITCH_ROLES:
        item = found.get(role)
        if not item:
            continue
        lines = [str(line).strip() for line in item.get("lines") or [] if str(line).strip()]
        claim = _first_sentence(lines[0]) if lines else role.replace("_", " ").capitalize()
        notes = " ".join(lines)
        figure = item.get("figure")
        if figure and figure.get("id"):
            layout = "table" if figure.get("kind") == "table" else "figure"
            extra = {"table": figure["id"]} if layout == "table" else {"figure": figure["id"]}
            slides.append(slide(layout, claim=claim, notes=notes, **extra))
        else:
            bullets = [_first_sentence(line) for line in lines[1:4]]
            slides.append(slide("claim", claim=claim, bullets=bullets, notes=notes))
    return {"format": DECK_FORMAT, "title": title, "slides": slides}

HTML_TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>
@page { size: 1280px 720px; margin: 0; }
html,body{margin:0;padding:0;background:#fdfdfb}
.slide{width:1280px;height:720px;box-sizing:border-box;padding:64px 72px;
       page-break-after:always;position:relative;background:#fdfdfb;font-family:Georgia,'Times New Roman',serif;color:#1b1b1b}
.slide:last-child{page-break-after:auto}
h2{font-size:34px;line-height:1.25;margin:0 0 24px;max-width:1040px}
.subtitle{font-size:20px;color:#555550}
ul{margin:0 0 0 24px;font-size:20px;line-height:1.45}
li{margin:6px 0}
img{max-width:100%%;max-height:430px;display:block;margin:0 auto}
table{border-collapse:collapse;width:100%%;font-size:16px}
th{background:#E8EDF4;border:1px solid #BFC8D6;padding:8px;text-align:left}
td{border:1px solid #BFC8D6;padding:8px;vertical-align:top}
.title h2{font-size:46px;margin-top:190px}
</style></head><body>%s</body></html>"""


def _html_table(table):
    columns = table.get("columns") or []
    rows = table.get("rows") or []
    if not columns:
        return ""
    head = "".join("<th>%s</th>" % escape(str(column)) for column in columns)
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % escape(str(cell)) for cell in row)
                   for row in rows)
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (head, body)


def html_document(built, figures=None):
    """The deck as print pages: one 16:9 page per slide, notes omitted."""
    figures = figures or {}
    pages = []
    for item in built.get("slides") or []:
        layout = item.get("layout")
        claim = escape(str(item.get("claim") or ""))
        body = ""
        if layout == "title":
            body = '<div class="subtitle">%s</div>' % escape(str(item.get("subtitle") or ""))
        elif layout == "table":
            record = figures.get(item.get("table")) or {}
            body = _html_table(record.get("table") or {})
        elif layout == "figure":
            record = figures.get(item.get("figure")) or {}
            png = (record.get("asset") or {}).get("png")
            if png:
                body = '<img src="data:image/png;base64,%s">' % base64.b64encode(png).decode("ascii")
            elif record.get("rows"):
                body = "<ul>" + "".join("<li>%s: %s</li>" % (escape(str(a)), escape(str(b)))
                                        for a, b in record["rows"]) + "</ul>"
        else:
            bullets = item.get("bullets") or []
            if bullets:
                body = "<ul>" + "".join("<li>%s</li>" % escape(str(b)) for b in bullets) + "</ul>"
        pages.append('<section class="slide %s"><h2>%s</h2>%s</section>' % (layout, claim, body))
    return HTML_TEMPLATE % "".join(pages)


def pdf_bytes(built, figures=None):
    """The deck as a PDF, printed by the headless Chrome kaleido carries.

    Returns None when no Chrome is installed, so the caller can say so instead of
    shipping an empty file.
    """
    from . import renderers

    chrome = renderers.chrome()
    if not chrome:
        return None
    markup = html_document(built, figures)
    directory = tempfile.mkdtemp(prefix="bp-deck-pdf-")
    page = os.path.join(directory, "deck.html")
    target = os.path.join(directory, "deck.pdf")
    profile = os.path.join(directory, "profile")
    try:
        with open(page, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(markup)
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
             "--no-default-browser-check", "--disable-extensions",
             "--disable-background-networking", "--disable-sync", "--disable-dev-shm-usage",
             "--no-pdf-header-footer", "--user-data-dir=" + profile,
             "--print-to-pdf=" + target, "file:///" + page.replace("\\", "/")],
            timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(target):
            with open(target, "rb") as stream:
                return stream.read()
        return None
    except Exception:
        return None
    finally:
        shutil.rmtree(directory, ignore_errors=True)
