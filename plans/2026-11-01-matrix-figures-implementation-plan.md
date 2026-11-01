# Matrix Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the framework templates that *are* a matrix or a canvas a properly drawn figure in the exported Word paper — SWOT, Ansoff, Value Chain, VRIO, McKinsey 7S, BCG, GE/McKinsey and Blue Ocean ERRC — with no cell ever left blank, the model helping the student who is unsure, and no figure content that the frozen core did not produce.

**Architecture:** A new product-layer module `src/bp/product/matrix.py` holds a pure-data **layout registry** (which cells, in which order, with which axes and spans) and a **builder** that turns a framework's blocks into a renderer-agnostic figure. `paper.section()` gains an optional `figure` slot, and `docx.academic_document_xml()` gains a table renderer that draws that figure as a native Word table with shaded header cells, column spans, vertical merges and an APA "Figure N." label. The chat path and the worksheet-completion path each supply their own cell content; neither the renderer nor the registry knows about a specific framework's content.

**Tech Stack:** Python 3.14 standard library only (no runtime third-party imports — CONTRIBUTORS.md §1 rule 8). OOXML written by hand into the `.docx` zip, exactly as `src/bp/product/docx.py` already does. Tests with `unittest`, run with `$env:PYTHONPATH="src"; python -m unittest discover -s tests` from `business_pipeline_v0.12/business_pipeline`.

## Global Constraints

- **No runtime third-party imports.** `src/` imports only the Python standard library. No Pillow, no lxml, no numpy (`CONTRIBUTORS.md` §1 rule 8).
- **The frozen core is not touched.** `src/bp/templates.py`, `src/bp/methods.py`, `tests/fixtures/frozen_contract.json` and the 12 frozen API route families are the computation owner's lane (`CONTRIBUTORS.md` §1B). Every file this plan creates or modifies is under `src/bp/product/` or `tests/` for product-lane tests. `src/bp/templates.py` is **read** for its block keys and labels, never written.
- **No invented evidence, numbers, names, sources or citations.** A figure cell may only carry text that is (a) a student input, (b) a retrieved item's own title or text, (c) the framework's own recorded background note, or (d) a model proposal the student has been shown and that passed the number/name/link guard. The builder itself never writes content.
- **A figure carries no computed business number.** A SWOT cell never shows a market-share percentage; the numbers stay in the prose, produced by the frozen core.
- **No cell is ever blank.** An empty cell renders the named gap plus the block's own probe ("What to look for: …"), in italic. This is the existing PESTEL/`_probe` precedent, not a new invention.
- **A student input stays a student input.** The model may restate the student's own words as a proposal for the student to accept; it may never assert a fact about the firm on the student's behalf.
- **Template instructions never reach the paper.** `paper.META` phrases must not appear in a figure cell; `paper.check` is extended to scan figure text, and a figure carrying one is a high-severity export blocker.
- **Determinism.** The same paper content must render byte-identical `.docx` bytes (the existing `test_the_same_title_and_sections_render_identical_bytes` guarantee).
- **Baseline.** Measured on 2026-11-01, before any change: **2488 tests, 94 failures, 85 errors** (179 problems). `docs/OPEN_ISSUES.md` records 58 — that figure is out of date. The measured list is saved at `plans/baseline-failures.txt` (87 distinct test names); compare against it, do not compare against the doc. Wave-1 templates with **pre-existing** failing tests: `template_value_chain` (block-key naming), `template_bcg`, `template_ge_mckinsey` and `template_mckinsey_7s` (the model-prompt tests), plus the catalogue and documentation-sync tests. A new failure is one that is not in that list.
- **Test command.** From `business_pipeline_v0.12/business_pipeline`:
  ```powershell
  $env:PYTHONPATH="src"
  python -m unittest discover -s tests
  ```
  Single file: `python -m unittest tests.test_matrix_figure -v`

---

## File Structure

| File | Responsibility |
|---|---|
| `src/bp/product/matrix.py` (new) | The layout registry (pure data: geometry per template), the alias map, and the builder that turns blocks into a figure. Knows nothing about Word. |
| `src/bp/product/paper.py` (modify) | `section()` gains a `figure` slot; `check()` scans figure text for template instructions; a `figure_text()` helper. |
| `src/bp/product/docx.py` (modify) | A Word-table renderer for a figure: grid, column widths, cell shading, `gridSpan`, `vMerge`, the APA figure label and the note. |
| `src/bp/product/completion.py` (modify) | The worksheet path: build cells from `blocks`, attach the figure to the framework H1 section, and extend the model-assist so an empty cell is never an empty box. |
| `src/bp/product/chat.py` (modify) | The chat path: build cells from the student's answers and the accepted evidence, attach the figure to the framework H1 section. |
| `src/bp/product/assist.py` (new) | The chat-path model assist: propose candidate statements from the student's own words and the accepted evidence, validated, for the student to accept or edit. |
| `src/bp/product/api.py` (modify) | One additive product route for the chat assist: `POST /api/cases/{id}/assist`. |
| `web/index.html` (modify) | The minimal affordance: show the model's proposals in the chat, and the accept/dismiss control. |
| `tests/test_matrix_figure.py` (new) | The renderer and the builder: geometry, spans, shading, figure numbering, never-blank, no-template-text, determinism. |
| `tests/test_matrix_completion.py` (new) | The worksheet path: each wave-1 template produces a figure; the cells carry the item identities; an empty cell carries the gap and the probe. |
| `tests/test_matrix_chat.py` (new) | The chat path: SWOT, Ansoff, Value Chain and VRIO carry a figure; the external cells carry the source title and the citation; the internal cells carry the student's own words. |
| `tests/test_matrix_assist.py` (new) | The model assist: a proposal that invents a number, a name, a link or a citation is refused; a legitimate proposal is kept; nothing reaches the paper unconfirmed. |

**Interfaces between tasks** (each task's implementer sees only their own task, so these are the names they code against):

- `matrix.LAYOUTS: dict[str, dict]` — template id → layout spec.
- `matrix.ALIASES: dict[str, dict]` — template id → `{alias_key: block_key}`.
- `matrix.layout_for(template: str) -> dict | None`
- `matrix.build(template: str, cells: dict[str, dict], caption: str | None = None) -> dict | None`
  - `cells` maps a block key → `{"label": str, "bullets": list[str], "gap": str | None}`.
  - Returns a figure dict (shape below) or `None` when the template has no layout.
- `paper.section(heading, level, lines=None, figure=None) -> dict`
- `paper.figure_text(figure: dict | None) -> str` — every string in the figure, joined, for the template-text scan.
- `docx._figure_xml(figure: dict, number: int) -> str` — the Word XML for one figure.
- `docx.academic_document_xml(title, sections, style="apa", byline=()) -> str` — unchanged signature; it now renders `item["figure"]` and numbers figures in document order.

The figure dict produced by `matrix.build`:

```python
{
  "kind": "quadrant" | "chain" | "columns" | "hub",
  "caption": "SWOT matrix",
  "note": "Strengths and weaknesses are the firm's own; opportunities and threats are drawn from the cited sources.",
  "grids": [
    {
      "title": "Support activities" | None,
      "rows": [ [CELL, ...], ... ],
      "axis_x": ("Existing products", "New products") | None,
      "axis_y": ("Existing markets", "New markets") | None,
      "col_widths": [0.44, 0.44] | None,
    },
  ],
}

CELL = {
  "label": "Strengths",
  "bullets": ["Own bakery network, three outlets", "..."],
  "gap": "No strengths were supplied. What to look for: …" | None,
  "span": 1,
  "role": "body" | "hub",
  "vmerge": "restart" | "continue" | None,
}
```

---

## Task 1: The figure contract and the Word table renderer

**Files:**
- Modify: `src/bp/product/paper.py` (the `section()` factory, `check()`)
- Modify: `src/bp/product/docx.py` (a table renderer for the academic document)
- Test: `tests/test_matrix_figure.py`

**Interfaces:**
- Consumes: nothing (this task creates the contract the rest of the plan uses).
- Produces: `paper.section(heading, level, lines=None, figure=None)`, `paper.figure_text(figure)`, `docx._figure_xml(figure, number)`, and a `figure` key on every section dict.

- [ ] **Step 1: Write the failing test**

Create `tests/test_matrix_figure.py`:

```python
"""The figure slot on a paper section and the Word table that draws it."""

import io
import re
import unittest
import zipfile

from bp.product import docx, paper


def _body(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return archive.read("word/document.xml").decode("utf-8")


FIGURE = {
    "kind": "quadrant",
    "caption": "SWOT matrix",
    "note": "Strengths and weaknesses are the firm's own.",
    "grids": [{
        "title": None,
        "rows": [
            [{"label": "Strengths", "bullets": ["Own bakery network"], "gap": None},
             {"label": "Weaknesses", "bullets": [], "gap": "No weaknesses were supplied."}],
            [{"label": "Opportunities", "bullets": ["Retail growth"], "gap": None},
             {"label": "Threats", "bullets": [], "gap": "No threats were supplied."}],
        ],
        "axis_x": None,
        "axis_y": None,
        "col_widths": [0.5, 0.5],
    }],
}


class FigureSlotTest(unittest.TestCase):
    def test_a_section_carries_a_figure(self):
        item = paper.section("SWOT", paper.H1, [], figure=FIGURE)
        self.assertIs(item["figure"], FIGURE)
        self.assertEqual(item["lines"], [])

    def test_a_section_without_a_figure_has_none(self):
        self.assertIsNone(paper.section("Intro", paper.H1, ["Body."])["figure"])

    def test_figure_text_joins_every_string_in_the_figure(self):
        text = paper.figure_text(FIGURE)
        self.assertIn("Strengths", text)
        self.assertIn("Own bakery network", text)
        self.assertIn("No threats were supplied.", text)


class FigureCheckTest(unittest.TestCase):
    def test_template_text_in_a_figure_blocks_the_export(self):
        sections = [
            {"heading": "Introduction", "level": 1, "lines": ["Body."]},
            {"heading": "SWOT", "level": 1, "lines": [], "figure": dict(
                FIGURE, grids=[{"title": None, "rows": [[
                    {"label": "Strengths", "bullets": ["(your analysis)"], "gap": None},
                    {"label": "Weaknesses", "bullets": [], "gap": None}]],
                    "axis_x": None, "axis_y": None, "col_widths": [0.5, 0.5]}])},
            {"heading": "Conclusion", "level": 1, "lines": ["Done."]},
            {"heading": "References", "level": 1, "lines": ["Ref."]},
        ]
        issues = paper.check(sections, framework="swot", implications="A position.")
        self.assertTrue(any(issue["type"] == "meta_text" for issue in issues), issues)


class FigureDocxTest(unittest.TestCase):
    def setUp(self):
        self.body = _body(docx.render_academic(
            "SWOT analysis", [{"heading": "SWOT", "level": 1, "lines": [], "figure": FIGURE}],
            "apa"))

    def test_the_figure_is_a_real_word_table(self):
        self.assertIn("<w:tbl>", self.body)
        self.assertIn("<w:gridCol", self.body)

    def test_the_figure_carries_its_apa_label_and_caption(self):
        self.assertIn("Figure 1", self.body)
        self.assertIn("SWOT matrix", self.body)

    def test_a_cell_with_no_bullets_shows_its_named_gap_not_an_empty_box(self):
        self.assertIn("No threats were supplied.", self.body)

    def test_figures_are_numbered_in_document_order(self):
        body = _body(docx.render_academic("Title", [
            {"heading": "SWOT", "level": 1, "lines": [], "figure": FIGURE},
            {"heading": "Ansoff", "level": 1, "lines": [], "figure": FIGURE}], "apa"))
        self.assertIn("Figure 1", body)
        self.assertIn("Figure 2", body)

    def test_a_paper_with_no_figure_renders_no_table(self):
        body = _body(docx.render_academic("Title", [
            {"heading": "Introduction", "level": 1, "lines": ["Body."]}], "apa"))
        self.assertNotIn("<w:tbl>", body)

    def test_the_same_sections_render_identical_bytes(self):
        first = docx.render_academic("SWOT analysis", [
            {"heading": "SWOT", "level": 1, "lines": [], "figure": FIGURE}], "apa")
        second = docx.render_academic("SWOT analysis", [
            {"heading": "SWOT", "level": 1, "lines": [], "figure": FIGURE}], "apa")
        self.assertEqual(first, second)
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_figure -v
```
Expected: `TypeError: section() got an unexpected keyword argument 'figure'` (collection error is fine — it is still a failure).

- [ ] **Step 3: Add the figure slot to `paper.py`**

In `src/bp/product/paper.py`, replace the `section` factory and add the helper:

```python
def section(heading, level, lines=None, figure=None):
    return {"heading": heading, "level": level, "lines": list(lines or []),
            "figure": figure or None}


def figure_text(figure):
    """Every string a figure carries, joined, for the template-text scan."""
    if not figure:
        return ""
    parts = [str(figure.get("caption") or ""), str(figure.get("note") or "")]
    for grid in figure.get("grids") or []:
        parts.append(str(grid.get("title") or ""))
        for row in grid.get("rows") or []:
            for cell in row or []:
                parts.append(str(cell.get("label") or ""))
                parts.extend(str(bullet) for bullet in cell.get("bullets") or [])
                parts.append(str(cell.get("gap") or ""))
    return " ".join(part for part in parts if part)
```

In `check()`, extend the template-text scan. The existing code is:

```python
    texts = " ".join(" ".join(item.get("lines") or []) for item in sections).lower()
```

Replace it with:

```python
    texts = " ".join(" ".join(item.get("lines") or []) for item in sections).lower()
    texts += " " + figure_text(item.get("figure")).lower() if False else ""
```

No — write it properly, as a loop that covers every section:

```python
    texts = []
    for item in sections:
        texts.append(" ".join(item.get("lines") or []))
        texts.append(figure_text(item.get("figure")))
    texts = " ".join(texts).lower()
```

- [ ] **Step 4: Write the Word table renderer in `docx.py`**

Add to `src/bp/product/docx.py`, above `academic_document_xml`:

First, give `_academic_para` an optional shade, so a paragraph can carry a
background tint:

```python
def _academic_para(text, bold=False, align=None, size=24, after=0, indent=None,
                   hanging=None, italic=False, style=None, keep_next=False,
                   break_before=False, shade=None):
    ppr = []
    if break_before:
        ppr.append("<w:pageBreakBefore/>")
    if style:
        ppr.append('<w:pStyle w:val="%s"/>' % style)
    if align:
        ppr.append('<w:jc w:val="%s"/>' % align)
    if shade:
        ppr.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade)
    ppr.append('<w:spacing w:line="480" w:lineRule="auto" w:after="%d"/>' % after)
```

Then add the figure renderer:

```python
#: Word's text column is 9360 twips wide between the 1-inch margins.
FIGURE_WIDTH = 9360
#: The tint behind a figure's cell label.
LABEL_FILL = "E8EDF4"
#: The tint behind a cell that carries the shared core of a model.
HUB_FILL = "DCE6F1"


def _figure_cell(paragraphs, width, fill=None, span=None, vmerge=None):
    props = ['<w:tcW w:w="%d" w:type="dxa"/>' % width]
    if span and span > 1:
        props.append('<w:gridSpan w:val="%d"/>' % span)
    if vmerge == "restart":
        props.append('<w:vMerge w:val="restart"/>')
    elif vmerge == "continue":
        props.append('<w:vMerge/>')
    if fill:
        props.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % fill)
    props.append('<w:tcBorders><w:top w:val="single" w:sz="4" w:color="BFC8D6"/>'
                 '<w:left w:val="single" w:sz="4" w:color="BFC8D6"/>'
                 '<w:bottom w:val="single" w:sz="4" w:color="BFC8D6"/>'
                 '<w:right w:val="single" w:sz="4" w:color="BFC8D6"/></w:tcBorders>')
    return ("<w:tc><w:tcPr>%s</w:tcPr>%s</w:tc>" % ("".join(props), "".join(paragraphs)))


def _cell_paragraphs(cell):
    """The paragraphs of one figure cell: its label, its bullets, its gap.

    The label sits on its own tinted line, so a reader can find a cell by its
    name.  A cell with nothing in it still prints its gap, so it is never an
    empty box.
    """
    parts = []
    label = str(cell.get("label") or "")
    if label:
        parts.append(_academic_para(label, bold=True, size=19, after=30, shade=LABEL_FILL))
    for bullet in cell.get("bullets") or []:
        parts.append(_academic_para("•  " + str(bullet), size=19, after=20))
    gap = cell.get("gap")
    if gap:
        parts.append(_academic_para(str(gap), italic=True, size=17, after=20))
    if not parts:
        parts.append(_academic_para("", size=19, after=20))
    return parts


def _figure_grid_xml(grid):
    """One Word table for one grid of a figure, axes included."""
    rows = grid.get("rows") or []
    if not rows:
        return ""
    columns = max(len(row) for row in rows)
    fractions = list(grid.get("col_widths") or [])
    if len(fractions) != columns:
        fractions = [1.0 / columns] * columns
    axis_y = grid.get("axis_y")
    axis_x = grid.get("axis_x")
    # a vertical axis gets its own narrow column down the left-hand side
    if axis_y:
        fractions = [0.13] + fractions
    scale = [int(FIGURE_WIDTH * float(fraction)) for fraction in fractions]
    scale[-1] += FIGURE_WIDTH - sum(scale)
    offset = 1 if axis_y else 0
    parts = ['<w:tbl><w:tblPr><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>']
    parts.extend('<w:gridCol w:w="%d"/>' % width for width in scale)
    parts.append("</w:tblGrid>")
    for index, row in enumerate(rows):
        cells = []
        if axis_y:
            # the tuple is (bottom, top), so the first row takes the top label
            label = axis_y[1] if index == 0 else axis_y[0]
            cells.append(_figure_cell(
                [_academic_para(str(label), italic=True, size=17, align="right", after=20)],
                scale[0]))
        for column in range(columns):
            cell = row[column] if column < len(row) else {"label": "", "bullets": []}
            span = int(cell.get("span") or 1)
            width = sum(scale[offset + column:offset + column + span])
            fill = HUB_FILL if cell.get("role") == "hub" else None
            cells.append(_figure_cell(_cell_paragraphs(cell), width, fill=fill, span=span))
        parts.append("<w:tr>" + "".join(cells) + "</w:tr>")
    if axis_x:
        # the horizontal axis is a row of labels under the columns
        cells = [_figure_cell([_academic_para("", size=17, after=20)], scale[0])]
        content = scale[offset:]
        for column, width in enumerate(content):
            label = axis_x[0] if column == 0 else axis_x[1]
            cells.append(_figure_cell(
                [_academic_para(str(label), italic=True, size=17, align="center", after=20)],
                width))
        parts.append("<w:tr>" + "".join(cells) + "</w:tr>")
    parts.append("</w:tbl>")
    return "".join(parts)


def _figure_xml(figure, number):
    """The Word XML for one figure: its APA label, its grids and its note."""
    parts = [_academic_para("Figure %d. %s" % (number, figure.get("caption") or ""),
                             bold=False, size=22, after=60, keep_next=True)]
    for grid in figure.get("grids") or []:
        if grid.get("title"):
            parts.append(_academic_para(str(grid["title"]), bold=True, size=20,
                                        after=40, keep_next=True))
        parts.append(_figure_grid_xml(grid))
    if figure.get("note"):
        parts.append(_academic_para("Note. " + str(figure["note"]), italic=True,
                                    size=18, after=120))
    return "".join(parts)
```

Then, in `academic_document_xml`, add a figure counter and render the figure after the heading and before the lines:

```python
    figure_number = 0
    for item in sections:
        ...
        if level >= 3:
            ...
        figure = item.get("figure") if isinstance(item, dict) else None
        if figure:
            figure_number += 1
            parts.append(_figure_xml(figure, figure_number))
        for line in lines:
            ...
```

Place the figure block **after** the heading paragraph and **before** the `for line in lines:` loop.

- [ ] **Step 5: Run the test to verify it passes**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_figure -v
```
Expected: all tests PASS.

- [ ] **Step 6: Check the existing academic-document tests still pass**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_academic_docx tests.test_chat tests.test_completion -v
```
Expected: PASS, no failures. (`test_the_same_title_and_sections_render_identical_bytes` proves determinism was not broken.)

- [ ] **Step 7: Commit**

```powershell
git add src/bp/product/paper.py src/bp/product/docx.py tests/test_matrix_figure.py
git commit -m "feature: a figure slot on a paper section and the Word table that draws it"
```

---

## Task 2: The layout registry and the figure builder

**Files:**
- Create: `src/bp/product/matrix.py`
- Test: `tests/test_matrix_figure.py` (extend)

**Interfaces:**
- Consumes: `paper.figure_text` (not needed here), the block keys and labels from `framework_profiles` and from the chat's framework definitions.
- Produces: `matrix.LAYOUTS`, `matrix.ALIASES`, `matrix.layout_for(template)`, `matrix.build(template, cells, caption=None)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix_figure.py`:

```python
class LayoutRegistryTest(unittest.TestCase):
    def test_every_wave_one_template_has_a_layout(self):
        for template in ("template_swot", "template_ansoff", "template_value_chain",
                         "template_vrio", "template_mckinsey_7s", "template_bcg",
                         "template_ge_mckinsey", "template_blue_ocean_errc"):
            self.assertIsNotNone(matrix.layout_for(template), template)

    def test_a_template_without_a_layout_returns_none(self):
        self.assertIsNone(matrix.layout_for("template_pestel"))

    def test_the_swot_layout_is_a_two_by_two_with_no_axes(self):
        figure = matrix.build("template_swot", {})
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 2)
        self.assertIsNone(figure["grids"][0]["axis_x"])
        self.assertIsNone(figure["grids"][0]["axis_y"])

    def test_the_ansoff_layout_carries_both_axes_in_the_canonical_order(self):
        figure = matrix.build("template_ansoff", {})
        grid = figure["grids"][0]
        self.assertEqual(grid["axis_x"], ("Existing products", "New products"))
        self.assertEqual(grid["axis_y"], ("Existing markets", "New markets"))
        self.assertEqual(grid["rows"][0][0]["label"], "Market development")
        self.assertEqual(grid["rows"][1][0]["label"], "Market penetration")

    def test_the_value_chain_layout_has_a_support_row_and_a_primary_row(self):
        figure = matrix.build("template_value_chain", {})
        grids = figure["grids"]
        self.assertEqual(len(grids), 2)
        self.assertEqual(grids[0]["title"], "Support activities")
        self.assertEqual(grids[1]["title"], "Primary activities")
        self.assertEqual(len(grids[0]["rows"][0]), 4)
        self.assertEqual(len(grids[1]["rows"][0]), 5)

    def test_the_mckinsey_layout_puts_shared_values_between_the_other_six(self):
        figure = matrix.build("template_mckinsey_7s", {})
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][0]["role"], "hub")
        self.assertEqual(rows[1][0]["span"], 3)

    def test_the_ge_mckinsey_layout_is_a_three_by_three(self):
        figure = matrix.build("template_ge_mckinsey", {})
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(len(row) == 3 for row in rows))

    def test_a_cell_with_no_content_shows_its_gap_and_is_never_blank(self):
        cells = {"S": {"label": "Strengths", "bullets": [], "gap": "No strengths were supplied."}}
        figure = matrix.build("template_swot", cells)
        cell = figure["grids"][0]["rows"][0][0]
        self.assertEqual(cell["gap"], "No strengths were supplied.")
        self.assertEqual(cell["bullets"], [])

    def test_the_alias_map_lets_the_chat_keys_find_the_profile_keys(self):
        cells = {"strengths": {"label": "Strengths", "bullets": ["Own network"], "gap": None}}
        figure = matrix.build("template_swot", cells)
        self.assertEqual(figure["grids"][0]["rows"][0][0]["bullets"], ["Own network"])

    def test_a_template_without_a_layout_builds_none(self):
        self.assertIsNone(matrix.build("template_pestel", {}))
```

Add the import at the top of the test file:

```python
from bp.product import docx, matrix, paper
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_figure -v
```
Expected: `ModuleNotFoundError: No module named 'bp.product.matrix'`.

- [ ] **Step 3: Create `src/bp/product/matrix.py`**

```python
"""Matrix and canvas figures for the paper (product layer).

A framework that *is* a grid — SWOT, Ansoff, BCG, GE/McKinsey, Blue Ocean's
four actions, VRIO, McKinsey's seven S, Porter's value chain — should reach the
paper as a grid, not as four paragraphs in a row.  This module holds the geometry
of those grids as data and turns a framework's blocks into a figure.

Two rules govern everything here:

- the geometry is data, not code, so adding a framework never means editing the
  renderer (the conductor manual's rule for the writer and the renderer);
- the builder writes no content.  It places what the caller gives it and never
  a character of its own, so a cell can carry only the student's words, a
  retrieved item's own identity, the framework's recorded background, or a model
  proposal the student has already been shown.
"""

#: Geometry per template.  ``rows`` lists block keys in reading order; a cell
#: may span columns with ``span`` and may be a shared core with ``role``.
LAYOUTS = {
    "template_swot": {
        "kind": "quadrant",
        "caption": "SWOT matrix",
        "note": "Strengths and weaknesses are the firm's own; opportunities and "
                "threats are drawn from the cited sources.",
        "grids": [{"rows": [["S", "W"], ["O", "T"]], "col_widths": [0.5, 0.5]}],
    },
    "template_ansoff": {
        "kind": "quadrant",
        "caption": "Ansoff growth matrix",
        "note": "Each cell holds the evidence for one growth option.",
        "grids": [{"rows": [["market_development", "diversification"],
                            ["market_penetration", "product_development"]],
                   "axis_x": ("Existing products", "New products"),
                   "axis_y": ("Existing markets", "New markets"),
                   "col_widths": [0.5, 0.5]}],
    },
    "template_value_chain": {
        "kind": "chain",
        "caption": "Porter's value chain",
        "note": "Support activities enable the primary activities that deliver "
                "the margin.",
        "grids": [
            {"title": "Support activities",
             "rows": [["firm_infrastructure", "human_resource_management",
                       "technology_development", "procurement"]]},
            {"title": "Primary activities",
             "rows": [["inbound_logistics", "operations", "outbound_logistics",
                       "marketing_and_sales", "service"]]},
        ],
    },
    "template_vrio": {
        "kind": "columns",
        "caption": "VRIO analysis",
        "note": "The resource is judged against each of the four questions in turn.",
        "grids": [{"rows": [["valuable", "rare", "costly_to_imitate", "organized"]],
                   "col_widths": [0.25, 0.25, 0.25, 0.25]}],
    },
    "template_mckinsey_7s": {
        "kind": "hub",
        "caption": "McKinsey 7S alignment",
        "note": "Shared values hold the other six elements together.",
        "grids": [{"rows": [["strategy", "structure", "systems"],
                            [{"key": "shared_values", "span": 3, "role": "hub"}],
                            ["staff", "skills", "style"]],
                   "col_widths": [0.3333, 0.3333, 0.3334]}],
    },
    "template_bcg": {
        "kind": "quadrant",
        "caption": "BCG growth-share matrix",
        "note": "Each cell holds the evidence for one portfolio position.",
        "grids": [{"rows": [["stars", "question_marks"], ["cash_cows", "dogs"]],
                   "axis_x": ("Strong market share", "Low market share"),
                   "axis_y": ("Low industry growth", "High industry growth"),
                   "col_widths": [0.5, 0.5]}],
    },
    "template_ge_mckinsey": {
        "kind": "quadrant",
        "caption": "GE/McKinsey matrix",
        "note": "Each cell holds the evidence for one strategic position.",
        "grids": [{"rows": [["high_high", "high_medium", "high_low"],
                            ["medium_high", "medium_medium", "medium_low"],
                            ["low_high", "low_medium", "low_low"]],
                   "axis_x": ("Low competitive strength", "High competitive strength"),
                   "axis_y": ("Low business attractiveness", "High business attractiveness"),
                   "col_widths": [0.3333, 0.3333, 0.3334]}],
    },
    "template_blue_ocean_errc": {
        "kind": "columns",
        "caption": "Blue Ocean four actions (ERRC)",
        "note": "Eliminate, reduce, raise and create are read from left to right.",
        "grids": [{"rows": [["eliminate", "reduce", "raise", "create"]],
                   "col_widths": [0.25, 0.25, 0.25, 0.25]}],
    },
}

#: The chat names the same cells with its own words.  Both names find the cell.
ALIASES = {
    "template_swot": {"strengths": "S", "weaknesses": "W",
                      "opportunities": "O", "threats": "T"},
    "template_ansoff": {"market_penetration": "market_penetration",
                        "market_development": "market_development",
                        "product_development": "product_development",
                        "diversification": "diversification"},
    "template_vrio": {"valuable": "valuable", "rare": "rare",
                      "costly": "costly_to_imitate", "costly_to_imitate": "costly_to_imitate",
                      "organized": "organized", "organised": "organized"},
}

def layout_for(template):
    """The layout of a template, or None when the template has no grid."""
    return LAYOUTS.get(str(template or ""))


def _key_for(template, key):
    aliases = ALIASES.get(str(template or ""), {})
    return aliases.get(key, key)


def build(template, cells, caption=None):
    """The figure for a template, or None when the template has no grid.

    `cells` maps a block key to ``{"label", "bullets", "gap"}``.  A cell the
    caller did not supply is drawn with its own label and no content, which the
    renderer shows as the framework's own gap — never as an empty box.
    """
    layout = layout_for(template)
    if not layout:
        return None
    grids = []
    for grid in layout.get("grids") or []:
        rows = []
        for row in grid.get("rows") or []:
            built = []
            for entry in row:
                if isinstance(entry, dict):
                    key = entry.get("key")
                    span = int(entry.get("span") or 1)
                    role = entry.get("role") or "body"
                else:
                    key = entry
                    span = 1
                    role = "body"
                source = cells.get(key) or cells.get(_key_for(template, key)) or {}
                built.append({
                    "label": str(source.get("label") or key),
                    "bullets": [str(bullet) for bullet in source.get("bullets") or []],
                    "gap": source.get("gap"),
                    "span": span,
                    "role": role,
                    "vmerge": None,
                })
            rows.append(built)
        grids.append({
            "title": grid.get("title"),
            "rows": rows,
            "axis_x": grid.get("axis_x"),
            "axis_y": grid.get("axis_y"),
            "col_widths": grid.get("col_widths"),
        })
    return {"kind": layout.get("kind"),
            "caption": caption or layout.get("caption"),
            "note": layout.get("note"),
            "grids": grids}
```

**Note on `span`:** a layout entry may be a plain block key or a dict that also
declares `span` (how many columns the cell covers) and `role` (`hub` for a shared
core). The McKinsey hub row is the only one that spans. The value-chain grids have
four and five columns respectively, so they are separate tables — no span is needed
there.

- [ ] **Step 4: Run the test to verify it passes**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_figure -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/bp/product/matrix.py tests/test_matrix_figure.py
git commit -m "feature: the layout registry and the figure builder for the matrix frameworks"
```

---

## Task 3: The worksheet path — a figure in every framework paper

**Files:**
- Modify: `src/bp/product/completion.py` (the `_sections` function)
- Test: `tests/test_matrix_completion.py`

**Interfaces:**
- Consumes: `matrix.build(template, cells)`, `paper.section(..., figure=...)`.
- Produces: every completion draft for a wave-1 template carries a figure on its framework H1 section.

- [ ] **Step 1: Write the failing test**

Create `tests/test_matrix_completion.py`:

```python
"""The matrix frameworks reach the paper as a grid, not as a list of paragraphs."""

import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import completion, matrix  # noqa: E402

BRIEF = ("A grocery retailer is reviewing growth options before deciding whether "
         "to open a new store format or launch a private-label range.")
INDUSTRY = "grocery retail"


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": "Grocery retail " + query[:70],
        "abstract": "Evidence on the growth option named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Marketing", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def complete(template, **kwargs):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, kwargs.pop("instruction", BRIEF),
                                   industry=kwargs.pop("industry", INDUSTRY), **kwargs)


def figure_of(report):
    for section in report["sections"]:
        if section.get("figure"):
            return section["figure"]
    return None


class MatrixCompletionTest(unittest.TestCase):
    def test_ansoff_reaches_the_paper_as_a_two_by_two(self):
        report = completion.draft(complete("template_ansoff"))
        figure = figure_of(report)
        self.assertIsNotNone(figure)
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 2)

    def test_the_framework_heading_carries_the_figure(self):
        report = completion.draft(complete("template_ansoff"))
        headings = [section["heading"] for section in report["sections"] if section.get("figure")]
        self.assertTrue(headings)
        self.assertIn("Ansoff", headings[0])

    def test_a_sourced_cell_carries_the_source_identity_not_a_blank(self):
        report = completion.draft(complete("template_ansoff"))
        figure = figure_of(report)
        cell = figure["grids"][0]["rows"][0][0]
        self.assertTrue(cell["bullets"] or cell["gap"])
        self.assertTrue(cell["label"])

    def test_an_empty_cell_shows_the_named_gap_and_the_probe(self):
        result = complete("template_ansoff")
        for block in result["blocks"]:
            block["items"] = []
            block["gap"] = "No evidence was found for this cell."
        report = completion.draft(result)
        figure = figure_of(report)
        for row in figure["grids"][0]["rows"]:
            for cell in row:
                self.assertTrue(cell["gap"], cell["label"])
                self.assertNotEqual(cell["bullets"], [])

    def test_the_value_chain_keeps_the_support_row_above_the_primary_row(self):
        report = completion.draft(complete("template_value_chain"))
        figure = figure_of(report)
        titles = [grid["title"] for grid in figure["grids"]]
        self.assertEqual(titles, ["Support activities", "Primary activities"])

    def test_the_ge_mckinsey_paper_carries_a_three_by_three(self):
        report = completion.draft(complete("template_ge_mckinsey"))
        figure = figure_of(report)
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(len(row) == 3 for row in rows))

    def test_a_framework_without_a_grid_carries_no_figure(self):
        report = completion.draft(complete("template_pestel"))
        self.assertIsNone(figure_of(report))

    def test_the_word_paper_contains_the_table(self):
        result = complete("template_ansoff")
        data = completion.draft_bytes(result)
        self.assertIn(b"<w:tbl>", data)

    def test_the_existing_paper_checks_still_pass(self):
        report = completion.draft(complete("template_ansoff"))
        self.assertEqual(completion.missing(report.get("blocks") and report or report), [])
```

**Note:** the last test may need the real `missing()` signature — `completion.missing(result)`
takes the *completion result*, not the draft. Replace it with:

```python
    def test_an_empty_cell_does_not_block_the_paper(self):
        result = complete("template_ansoff")
        result["blocks"] = [block for block in result["blocks"]
                            if block["key"] != "diversification"]
        result["blocks"].append({"key": "diversification", "label": "Diversification",
                                 "items": [], "gap": "No evidence."})
        self.assertEqual(completion.missing(result), [])
```

and drop the `test_the_existing_paper_checks_still_pass` case above.

- [ ] **Step 2: Run the test to verify it fails**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_completion -v
```
Expected: FAIL — `figure_of(report)` returns `None`, so `test_ansoff_reaches_the_paper_as_a_two_by_two` fails.

- [ ] **Step 3: Build the cells and attach the figure in `completion.py`**

Add a helper near `_sections`:

```python
def _figure_cells(blocks):
    """One cell per block: the block's own items, never a blank.

    A cell carries the *identity* of each item — the source's title for a
    retrieved item, the student's own sentence for their own — so the grid
    reads as a summary and the prose below carries the full evidence.
    """
    cells = {}
    for block in blocks or []:
        bullets = []
        for item in block.get("items") or []:
            text = str(item.get("title") or item.get("text") or "").strip()
            if not text:
                continue
            citation = str(item.get("citation") or "").strip()
            if citation:
                text = text + " " + citation
            bullets.append(text)
        cells[block.get("key")] = {
            "label": block.get("label") or block.get("key"),
            "bullets": bullets,
            "gap": block.get("gap") or None,
        }
    return cells
```

And in `_sections`, attach the figure to the framework section:

```python
    sections = [paper.section("Introduction", 1, list(data["introduction"])),
                paper.section(outline.get("context") or "Case and context", 2, list(data["context"])),
                paper.section(outline.get("framework") or profile["label"], 1, [data["lead"]])]
```

becomes:

```python
    figure = matrix.build(result.get("template"), _figure_cells(blocks),
                          caption=profile.get("label"))
    sections = [paper.section("Introduction", 1, list(data["introduction"])),
                paper.section(outline.get("context") or "Case and context", 2, list(data["context"])),
                paper.section(outline.get("framework") or profile["label"], 1, [data["lead"]],
                              figure=figure)]
```

Add the import at the top of `completion.py`:

```python
from . import framework_profiles, matrix
```

(adjust to the existing import style in that file — check whether it already imports
`framework_profiles`; add `matrix` alongside it.)

- [ ] **Step 4: Run the test to verify it passes**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_completion -v
```
Expected: all PASS.

- [ ] **Step 5: Run the framework-completion suite for regressions**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_ansoff_completion tests.test_bcg_completion tests.test_ge_mckinsey_completion tests.test_errc_completion -v
```
Expected: no **new** failures. Compare against the baseline recorded in Task 0.

- [ ] **Step 6: Commit**

```powershell
git add src/bp/product/completion.py tests/test_matrix_completion.py
git commit -m "feature: the matrix frameworks reach the Word paper as a grid"
```

---

## Task 4: The chat path — a figure in the student's own paper

**Files:**
- Modify: `src/bp/product/chat.py` (the `draft` function)
- Test: `tests/test_matrix_chat.py`

**Interfaces:**
- Consumes: `matrix.build(template, cells)`, `paper.section(..., figure=...)`.
- Produces: a chat draft for SWOT, Ansoff, Value Chain and VRIO carries a figure.

- [ ] **Step 1: Write the failing test**

Create `tests/test_matrix_chat.py`. Model the test on `tests/test_chat.py`'s existing
fixture for a chat state. Open `tests/test_chat.py`, copy the helper that builds a
state at the `evidence` stage, and add:

```python
class MatrixChatTest(unittest.TestCase):
    def test_a_swot_paper_carries_a_two_by_two_figure(self):
        state = swot_state()
        draft = chat.draft(state)
        figure = None
        for section in draft["outline"]:
            if section.get("figure"):
                figure = section["figure"]
        self.assertIsNotNone(figure)
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 2)

    def test_the_strengths_cell_carries_the_students_own_words(self):
        state = swot_state()
        draft = chat.draft(state)
        figure = [s["figure"] for s in draft["outline"] if s.get("figure")][0]
        cell = figure["grids"][0]["rows"][0][0]
        self.assertEqual(cell["label"], "Strengths")
        self.assertTrue(cell["bullets"])
        self.assertIn("repeat customers", " ".join(cell["bullets"]).lower())

    def test_the_opportunities_cell_carries_the_source_title_and_citation(self):
        state = swot_state()
        draft = chat.draft(state)
        figure = [s["figure"] for s in draft["outline"] if s.get("figure")][0]
        cell = figure["grids"][0]["rows"][1][0]
        self.assertEqual(cell["label"], "Opportunities")
        self.assertTrue(cell["bullets"])
        self.assertTrue(any("(" in bullet for bullet in cell["bullets"]))

    def test_an_ansoff_paper_carries_the_axes(self):
        state = ansoff_state()
        draft = chat.draft(state)
        figure = [s["figure"] for s in draft["outline"] if s.get("figure")][0]
        self.assertEqual(figure["grids"][0]["axis_x"], ("Existing products", "New products"))
        self.assertEqual(figure["grids"][0]["axis_y"], ("Existing markets", "New markets"))

    def test_a_vrio_paper_carries_four_columns(self):
        state = vrio_state()
        draft = chat.draft(state)
        figure = [s["figure"] for s in draft["outline"] if s.get("figure")][0]
        self.assertEqual(len(figure["grids"][0]["rows"][0]), 4)

    def test_a_value_chain_paper_carries_the_two_rows(self):
        state = value_chain_state()
        draft = chat.draft(state)
        figure = [s["figure"] for s in draft["outline"] if s.get("figure")][0]
        self.assertEqual(len(figure["grids"]), 2)

    def test_the_word_paper_contains_the_table(self):
        state = swot_state()
        data = chat.docx_bytes(state)
        self.assertIn(b"<w:tbl>", data)
```

**Note:** the helper names (`swot_state`, `ansoff_state`, `vrio_state`, `value_chain_state`)
must be written against the real `tests/test_chat.py` fixture. Open that file first and
reuse its state builder rather than inventing one; the chat's evidence stage needs
`state["evidence"]`, `state["sources"]` and `state["answers"]`.

- [ ] **Step 2: Run the test to verify it fails**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_chat -v
```
Expected: FAIL — no figure is attached.

- [ ] **Step 3: Build the cells and attach the figure in `chat.py`**

Add a helper next to `_internal_lines`:

```python
def _figure_cells(answers, evidence, by_id, style, framework):
    """One cell per framework cell: the student's own words and the sources.

    An internal cell carries the student's own list entries.  An external cell
    carries the source's title and its citation — the identity of the evidence,
    not its prose, which the section below already quotes in full.
    """
    cells = {}
    if framework in ("swot", "pestel_swot"):
        for key, label in (("strengths", "Strengths"), ("weaknesses", "Weaknesses")):
            cells[key] = {"label": label, "bullets": list(answers.get(key) or []),
                          "gap": None if (answers.get(key) or []) else
                          "No " + label.lower() + " were supplied; this is a gap, not a finding."}
        for key, label, dimension in (("opportunities", "Opportunities", "opportunities"),
                                       ("threats", "Threats", "threats")):
            bullets = []
            for item in evidence:
                if item.get("dimension") != dimension:
                    continue
                source = by_id.get(item.get("source_id"), {})
                title = _clean(source.get("title"), 160) or _clean(item.get("quote"), 160)
                if title:
                    bullets.append(title + " " + _in_text(source, style) + ".")
            cells[key] = {"label": label, "bullets": bullets,
                          "gap": None if bullets else
                          "The retrieved evidence did not cover this quadrant; this is a gap, "
                          "not a finding."}
    if framework == "ansoff":
        for dimension in ANSOFF_DIMENSIONS:
            key, label = dimension[0], dimension[1]
            bullets = []
            for item in evidence:
                if item.get("dimension") != key:
                    continue
                source = by_id.get(item.get("source_id"), {})
                title = _clean(source.get("title"), 160) or _clean(item.get("quote"), 160)
                if title:
                    bullets.append(title + " " + _in_text(source, style) + ".")
            cells[key] = {"label": label, "bullets": bullets,
                          "gap": None if bullets else
                          "The retrieved evidence did not cover this option; this is a gap, "
                          "not a finding."}
    if framework == "value_chain":
        for dimension in VALUE_DIMENSIONS:
            key, label = dimension[0], dimension[1]
            bullets = []
            for item in evidence:
                if item.get("dimension") != key:
                    continue
                source = by_id.get(item.get("source_id"), {})
                title = _clean(source.get("title"), 160) or _clean(item.get("quote"), 160)
                if title:
                    bullets.append(title + " " + _in_text(source, style) + ".")
            cells[key] = {"label": label, "bullets": bullets,
                          "gap": None if bullets else
                          "The retrieved evidence did not cover this activity; this is a gap, "
                          "not a finding."}
    if framework == "vrio":
        for key, label, noun in (("valuable", "Valuable", "value judgments"),
                                 ("rare", "Rare", "rarity judgments"),
                                 ("costly", "Costly to imitate", "imitation-cost judgments"),
                                 ("organized", "Organised to capture value", "organisational judgments")):
            items = answers.get(key) or []
            cells[key] = {"label": label, "bullets": list(items),
                          "gap": None if items else
                          "No " + noun + " were supplied; this is a gap, not a finding."}
    return cells
```

Then, in `draft()`, attach the figure to each framework's H1 section. The SWOT block:

```python
    if framework in ("swot", "pestel_swot"):
        sections.append(paper.section("SWOT", paper.H1))
```

becomes:

```python
    figure_cells = _figure_cells(answers, evidence, by_id, style, framework)
    if framework in ("swot", "pestel_swot"):
        sections.append(paper.section("SWOT", paper.H1,
                                      figure=matrix.build("template_swot", figure_cells,
                                                          caption="SWOT matrix")))
```

and similarly for `value_chain` (`matrix.build("template_value_chain", ...)`),
`ansoff` (`matrix.build("template_ansoff", ...)`) and `vrio`
(`matrix.build("template_vrio", ...)`).

Add the import: `from . import matrix` alongside the other product imports in `chat.py`.

**Careful:** the chat's SWOT ordering must match the layout. The layout is
`[["S","W"],["O","T"]]` — Strengths top-left, Weaknesses top-right, Opportunities
bottom-left, Threats bottom-right. That is the conventional SWOT reading. The
canonical image in `Matrix templates/swot.jpg` puts Strengths top-left, Weaknesses
top-right, Opportunities bottom-left, Threats bottom-right. ✓

- [ ] **Step 4: Run the test to verify it passes**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_chat -v
```
Expected: all PASS.

- [ ] **Step 5: Check for regressions**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_chat tests.test_conductor_frameworks tests.test_capability_papers -v
```
Expected: no new failures.

- [ ] **Step 6: Commit**

```powershell
git add src/bp/product/chat.py tests/test_matrix_chat.py
git commit -m "feature: the chat paper carries the matrix figures for SWOT, Ansoff, Value Chain and VRIO"
```

---

## Task 5: The model helps the student who is unsure — the worksheet path

**Files:**
- Modify: `src/bp/product/completion.py` (`_suggest` and `complete`)
- Test: `tests/test_matrix_assist.py`

**Interfaces:**
- Consumes: `completion._suggest`, the profile's `assumption` mode, the block's `probe`.
- Produces: a block that would have been a gap carries a proposed line of enquiry, and the cell is never empty.

- [ ] **Step 1: Write the failing test**

Create `tests/test_matrix_assist.py`:

```python
"""The model helps a student who is unsure; it never invents the answer."""

import json
import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import completion, prose  # noqa: E402


class SuggestModeTest(unittest.TestCase):
    def test_a_probe_profile_gets_a_line_of_enquiry_not_an_assumption(self):
        profile = {"blocks": [{"key": "S", "label": "Strengths", "fill": "quote"}],
                   "voice": {"block_plural": "dimensions"},
                   "assumption": "probe"}
        blocks = [{"key": "S", "label": "Strengths", "items": []}]
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", return_value=json.dumps(
                    {"S": "Which of the three outlets serves the highest repeat demand?"})), \
                mock.patch("bp.product.prose._parse", side_effect=lambda raw: json.loads(raw)):
            out = completion._suggest(profile, ["S"], "A bakery in Intramuros with three outlets.",
                                      {"value": "bakery"}, blocks, mode="question")
        self.assertIn("S", out)
        self.assertTrue(out["S"].endswith("?"))

    def test_a_reply_with_a_number_is_refused(self):
        profile = {"blocks": [{"key": "S", "label": "Strengths", "fill": "quote"}],
                   "voice": {"block_plural": "dimensions"},
                   "assumption": "probe"}
        blocks = [{"key": "S", "label": "Strengths", "items": []}]
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", return_value=json.dumps(
                    {"S": "The bakery has 45% repeat customers."})), \
                mock.patch("bp.product.prose._parse", side_effect=lambda raw: json.loads(raw)):
            out = completion._suggest(profile, ["S"], "A bakery in Intramuros.",
                                      {"value": "bakery"}, blocks, mode="question")
        self.assertNotIn("S", out)

    def test_a_reply_with_a_link_is_refused(self):
        profile = {"blocks": [{"key": "S", "label": "Strengths", "fill": "quote"}],
                   "voice": {"block_plural": "dimensions"},
                   "assumption": "probe"}
        blocks = [{"key": "S", "label": "Strengths", "items": []}]
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", return_value=json.dumps(
                    {"S": "See https://example.com for the study."})), \
                mock.patch("bp.product.prose._parse", side_effect=lambda raw: json.loads(raw)):
            out = completion._suggest(profile, ["S"], "A bakery.", {"value": "bakery"},
                                      blocks, mode="question")
        self.assertNotIn("S", out)

    def test_a_never_answered_model_returns_nothing_and_the_cell_falls_back(self):
        profile = {"blocks": [{"key": "S", "label": "Strengths", "fill": "quote"}],
                   "voice": {"block_plural": "dimensions"},
                   "assumption": "probe"}
        blocks = [{"key": "S", "label": "Strengths", "items": []}]
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", side_effect=RuntimeError("no model")):
            out = completion._suggest(profile, ["S"], "A bakery.", {"value": "bakery"},
                                      blocks, mode="question")
        self.assertEqual(out, {})

    def test_the_case_mode_still_returns_an_assumption_not_a_question(self):
        profile = {"blocks": [{"key": "S", "label": "Strengths", "fill": "quote"}],
                   "voice": {"block_plural": "dimensions"},
                   "assumption": "case"}
        blocks = [{"key": "S", "label": "Strengths", "items": []}]
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", return_value=json.dumps(
                    {"S": "The bakery serves a dense catchment on foot."})), \
                mock.patch("bp.product.prose._parse", side_effect=lambda raw: json.loads(raw)):
            out = completion._suggest(profile, ["S"], "A bakery in Intramuros with three outlets.",
                                      {"value": "bakery"}, blocks)
        self.assertIn("S", out)
        self.assertFalse(out["S"].endswith("?"))
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_assist -v
```
Expected: FAIL — `_suggest` does not accept a `mode` keyword.

- [ ] **Step 3: Add the question mode to `_suggest`**

In `src/bp/product/completion.py`, change the signature and the prompt:

```python
def _suggest(profile, gaps, instruction, unit, blocks, mode="assumption"):
    """One proposal per gap, drawn only from the instruction and the unit.

    Two modes, two different promises:

    - ``assumption`` writes one CASE ASSUMPTION for the gap.  Only frameworks
      whose gaps can be answered analytically use this: an assumption about
      competitive dynamics is a reading of the case, while an assumption about
      a country would be an invented fact.
    - ``question`` writes a LINE OF ENQUIRY: a sharp, case-specific question
      the student can answer from their own position.  This is what a probe
      profile gets, so a student who is unsure is asked rather than left with
      an empty cell and no way forward.

    A reply that carries a number, a link, a DOI or a parenthesis is refused:
    a proposal may not introduce a fact of any kind.
    """
```

Inside the function, build the system prompt from the mode:

```python
        if mode == "question":
            system = ("You are a business case tutor. For each " + plural.rstrip("s") + ", write ONE "
                      "specific question that the student can answer from their own position, using only the "
                      "instruction and the named unit of analysis. The question must be about THIS case and "
                      "must be answerable with a fact the student already has; it must not be a statement, a "
                      "conclusion, a recommendation or a fact about the firm. Do not add a source, citation, "
                      "number, percentage, link or named fact not in the instruction. Return ONLY a JSON "
                      "object mapping the key to the question. No markdown.")
        else:
            system = ("You are a business case analyst. For each " + plural.rstrip("s") + ", write one specific CASE "
                      "ASSUMPTION, in one or two sentences, that answers the question for this case, not a statement "
                      "that the " + plural.rstrip("s") + " is relevant. Use only the instruction and the named unit of "
                      "analysis. Do not add a source, citation, number, percentage, link or named fact not in the "
                      "instruction. Return ONLY a JSON object mapping the key to the sentence. No markdown.")
```

And extend the guard so a question must end in a question mark and carry no number:

```python
        for key in gaps:
            text = _clean(data.get(key), 700)
            if not text or re.search(r"\d|https?://|doi:|\(", text, re.I):
                continue
            if mode == "question" and not text.endswith("?"):
                continue
            out[key] = text
```

- [ ] **Step 4: Fire the question mode for a probe profile's gaps**

In `complete()`, the block that currently proposes case assumptions:

```python
    gaps = [block["key"] for block in blocks if block["gap"] and not block["items"]]
    if gaps and profile.get("assumption") == "case":
        suggestions = _suggest(profile, gaps, instruction, unit, blocks)
        for block in blocks:
            if block["key"] in suggestions:
                block["items"] = block["items"] + [{"text": suggestions[block["key"]],
                                                    "provenance": "suggested", "source": ""}]
                block["gap"] = "No source was found; a case assumption is proposed for your review."
                notes.append(block["label"] + ": suggested case assumption.")
```

becomes:

```python
    gaps = [block["key"] for block in blocks if block["gap"] and not block["items"]]
    if gaps and profile.get("assumption") in ("case", "probe"):
        mode = "assumption" if profile.get("assumption") == "case" else "question"
        suggestions = _suggest(profile, gaps, instruction, unit, blocks, mode=mode)
        for block in blocks:
            if block["key"] in suggestions:
                block["items"] = block["items"] + [{"text": suggestions[block["key"]],
                                                    "provenance": "suggested", "source": ""}]
                block["gap"] = ("No source was found; a case assumption is proposed for your review."
                                if mode == "assumption" else
                                "No source was found; a line of enquiry is proposed to help you answer this.")
                notes.append(block["label"] + ": suggested " +
                            ("case assumption." if mode == "assumption" else "line of enquiry."))
```

**Important:** the probe profile's gaps currently carry the probe text
("What to look for: …"). Keep it. The suggested item is *added*, so the cell shows
both the proposal and the gap note. The cell must never be blank — and it is not.

- [ ] **Step 5: Run the test to verify it passes**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_assist -v
```
Expected: all PASS.

- [ ] **Step 6: Check the completion suite for regressions**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_completion tests.test_ansoff_completion tests.test_pestel_completion -v
```
Expected: no new failures. If the model's presence changes a test that asserted a
gap, that test's expectation is now wrong and must be updated **with the reason
recorded** — do not weaken the assertion.

- [ ] **Step 7: Commit**

```powershell
git add src/bp/product/completion.py tests/test_matrix_assist.py
git commit -m "feature: a probe cell asks the student a case-specific question instead of sitting empty"
```

---

## Task 6: The model helps the student who is unsure — the chat path

**Files:**
- Create: `src/bp/product/assist.py`
- Modify: `src/bp/product/api.py` (one additive product route)
- Modify: `src/bp/product/chat.py` (store and accept proposals)
- Modify: `web/index.html` (the minimal affordance)
- Test: `tests/test_matrix_assist.py` (extend)

**Interfaces:**
- Consumes: `prose._call`, `prose._parse`, the chat's brief, answers and accepted evidence.
- Produces: `assist.propose(state, key, label) -> dict`, `assist.accept(state, key, text) -> dict`, and `POST /api/cases/{id}/assist`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix_assist.py`:

```python
class ChatAssistTest(unittest.TestCase):
    def _state(self):
        return {
            "brief": "A bakery in Intramuros with three outlets and repeat customers.",
            "answers": {"decision": "should the bakery open a fourth outlet",
                        "strengths": []},
            "framework": "swot",
            "evidence": [],
            "sources": [],
            "profile": "academic",
            "stage": "evidence",
        }

    def test_a_proposal_uses_only_the_students_own_words(self):
        state = self._state()
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", return_value=json.dumps(
                    {"candidates": ["The bakery already serves repeat customers in Intramuros."]})), \
                mock.patch("bp.product.prose._parse", side_effect=lambda raw: json.loads(raw)):
            out = assist.propose(state, "strengths", "Strengths")
        self.assertEqual(len(out["candidates"]), 1)
        self.assertIn("repeat customers", out["candidates"][0])

    def test_a_proposal_that_invents_a_number_is_refused(self):
        state = self._state()
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", return_value=json.dumps(
                    {"candidates": ["The bakery has 92% customer retention."]})), \
                mock.patch("bp.product.prose._parse", side_effect=lambda raw: json.loads(raw)):
            out = assist.propose(state, "strengths", "Strengths")
        self.assertEqual(out["candidates"], [])

    def test_a_proposal_that_invents_a_name_is_refused(self):
        state = self._state()
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", return_value=json.dumps(
                    {"candidates": ["Almarai already dominates this district."]})), \
                mock.patch("bp.product.prose._parse", side_effect=lambda raw: json.loads(raw)):
            out = assist.propose(state, "strengths", "Strengths")
        self.assertEqual(out["candidates"], [])

    def test_a_proposal_that_adds_a_link_is_refused(self):
        state = self._state()
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call", return_value=json.dumps(
                    {"candidates": ["See https://example.com/report for the data."]})), \
                mock.patch("bp.product.prose._parse", side_effect=lambda raw: json.loads(raw)):
            out = assist.propose(state, "strengths", "Strengths")
        self.assertEqual(out["candidates"], [])

    def test_no_model_configured_returns_no_proposal_and_no_error(self):
        state = self._state()
        with mock.patch("bp.product.prose.available", return_value=False):
            out = assist.propose(state, "strengths", "Strengths")
        self.assertEqual(out["candidates"], [])

    def test_an_accepted_proposal_becomes_a_student_input(self):
        state = self._state()
        state["assist"] = {"strengths": {"candidates": ["Three outlets in Intramuros."]}}
        chat.accept_assist(state, "strengths", "Three outlets in Intramuros.")
        self.assertIn("Three outlets in Intramuros.",
                      " ".join(state["answers"]["strengths"]))

    def test_a_dismissed_proposal_is_not_added(self):
        state = self._state()
        state["assist"] = {"strengths": {"candidates": ["Three outlets in Intramuros."]}}
        chat.accept_assist(state, "strengths", None)
        self.assertEqual(state["answers"].get("strengths") or [], [])
```

Add the imports:

```python
from bp.product import assist, chat, completion, prose  # noqa: E402
```

- [ ] **Step 2: Run the test to verify it fails**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_assist -v
```
Expected: FAIL — `bp.product.assist` does not exist.

- [ ] **Step 3: Create `src/bp/product/assist.py`**

```python
"""Model-assisted cell proposals for the chat (product layer).

The student sometimes does not know what to write in a cell.  The model may
help: it reads the brief the student typed and the evidence the student
accepted, and proposes candidate statements *drawn from those words only*.

It may not answer the question.  A proposal that carries a number, a name, a
link or a citation that is not in the student's own words is refused, and the
student is left with the question instead.  Nothing a proposal says reaches the
paper until the student accepts it, and what reaches the paper is then the
student's answer, not the model's.
"""

import datetime
import json
import re

from . import prose

NUMBER = re.compile(r"\d+(?:\.\d+)?%?")
URL = re.compile(r"https?://|doi:", re.I)
PROPER = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")


def _supplied_text(state):
    """Everything the student themselves wrote, which is all the model may use."""
    answers = state.get("answers") or {}
    parts = [str(state.get("brief") or ""), str(answers.get("decision") or "")]
    for value in answers.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, str):
            parts.append(value)
    for item in state.get("evidence") or []:
        parts.append(str(item.get("quote") or ""))
    return " ".join(parts)


def _allowed_numbers(text):
    return set(NUMBER.findall(text))


def _allowed_names(text):
    return {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z\-']{2,}", text)}


def _problems(candidate, supplied):
    """Why a candidate may not be offered to the student."""
    text = str(candidate or "").strip()
    if not text:
        return ["empty"]
    if len(text) > 300:
        return ["too long"]
    if URL.search(text):
        return ["link"]
    if not set(NUMBER.findall(text)) <= _allowed_numbers(supplied):
        return ["number"]
    allowed = _allowed_names(supplied)
    for name in set(PROPER.findall(text)):
        if name.lower() not in allowed:
            return ["name " + name]
    return []


def propose(state, key, label):
    """Propose candidate statements for one cell, drawn from the student's words."""
    empty = {"key": key, "label": label, "candidates": [], "model": None,
             "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if not prose.available():
        return empty
    supplied = _supplied_text(state)
    system = ("You are helping a student fill one cell of a business analysis. Propose up to three short "
              "candidate statements for the cell. Use ONLY words the student has already supplied: restate "
              "their own facts, do not add a fact, a number, a name, a statistic, a source or a conclusion. "
              "Each candidate must be a plain statement the student could have written themselves. "
              "Return ONLY a JSON object: {\"candidates\": [\"...\", \"...\"]}. No markdown.")
    user = json.dumps({"cell": label, "supplied": supplied[:4000]}, ensure_ascii=False)
    try:
        raw = prose._call([{"role": "system", "content": system},
                           {"role": "user", "content": user}])
        data = prose._parse(raw)
    except Exception:
        return empty
    candidates = []
    for candidate in (data.get("candidates") or [])[:5]:
        text = str(candidate or "").strip()
        if _problems(text, supplied):
            continue
        candidates.append(text)
    empty["candidates"] = candidates
    empty["model"] = prose.model_id()
    return empty
```

- [ ] **Step 4: Accept a proposal in `chat.py`**

Add to `src/bp/product/chat.py`:

```python
def accept_assist(state, key, text):
    """The student's answer to a cell, entered from a model proposal or typed.

    What is stored is the student's answer.  The model's wording is never
    stored in place of it: an empty `text` dismisses the proposal and changes
    nothing.
    """
    answers = state.setdefault("answers", {})
    items = list(answers.get(key) or [])
    text = str(text or "").strip()
    if text:
        items.append(text)
        answers[key] = items
    proposals = state.get("assist") or {}
    if key in proposals:
        proposals[key] = dict(proposals[key], accepted=text or None)
        state["assist"] = proposals
    return state
```

- [ ] **Step 5: Add the route in `api.py`**

Find the product route family for cases (the block that handles `segments == ["cases", ...]`)
and add a new branch:

```python
    if segments == ["cases", case_id, "assist"]:
        if verb != "POST":
            return 405, {"error": "method %s is not allowed on the cell assistant" % verb}
        state = _case(case_id)
        if not state:
            return 404, {"error": "case not found"}
        body = _body()
        key = str(body.get("key") or "").strip()
        label = str(body.get("label") or key).strip()
        if not key:
            return 400, {"error": "a cell key is required"}
        proposal = assist.propose(state, key, label)
        state.setdefault("assist", {})[key] = proposal
        _save(case_id, state)
        return 200, {"assist": proposal}
```

Use the exact helpers the surrounding case routes use for loading and saving a
case — read the neighbouring branches in `api.py` and match their names.

Add `from . import assist` to the imports.

- [ ] **Step 6: Add the minimal web affordance**

In `web/index.html`, find where the chat asks the student for "Strengths" and
"Weaknesses" (the answers panel). Under the input, add a small button:

```html
<button type="button" class="linkish" data-assist="strengths">Help me name a strength</button>
```

and a handler that posts to the new route and lists the proposals for the
student to click, which fills the input with the chosen candidate:

```javascript
async function askAssist(caseId, key, label, inputEl) {
  const r = await post("/api/cases/" + caseId + "/assist", { key: key, label: label });
  const list = (r && r.assist && r.assist.candidates) || [];
  if (!list.length) {
    inputEl.placeholder = "No proposal was available; answer in your own words.";
    return;
  }
  const box = document.createElement("div");
  box.className = "assist-list";
  list.forEach(function (candidate) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "assist-item";
    button.textContent = candidate;
    button.addEventListener("click", function () { inputEl.value = candidate; });
    box.appendChild(button);
  });
  inputEl.parentElement.appendChild(box);
}
```

Match the file's existing styling conventions (`linkish`, `assist-list`, `assist-item`
must be added to the stylesheet block, following the neighbouring small-button
styles). The style must not change any other panel.

- [ ] **Step 7: Run the test to verify it passes**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_assist -v
```
Expected: all PASS.

- [ ] **Step 8: Check for regressions**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_chat tests.test_cache_headers -v
```
Expected: no new failures.

- [ ] **Step 9: Commit**

```powershell
git add src/bp/product/assist.py src/bp/product/chat.py src/bp/product/api.py web/index.html tests/test_matrix_assist.py
git commit -m "feature: the chat offers the student a case-specific proposal when a cell is blank"
```

---

## Task 7: The samples, the export gate and the record

**Files:**
- Modify: `src/bp/product/completion.py`, `src/bp/product/chat.py` (the export gate)
- Modify: `samples/*.docx` (regenerate the wave-1 samples)
- Modify: `docs/CHANGELOG.md`, `docs/WORKLOG.md`, `docs/DECISIONS.md`, `docs/KNOWN_LIMITATIONS.md`
- Test: `tests/test_matrix_figure.py` (extend)

**Interfaces:**
- Consumes: everything above.
- Produces: a paper whose figure carries template text cannot be exported; the samples show the figures; the record explains the convention.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix_figure.py`:

```python
class ExportGateTest(unittest.TestCase):
    def test_a_paper_whose_figure_carries_template_text_cannot_be_exported(self):
        sections = [
            {"heading": "Introduction", "level": 1, "lines": ["Body."]},
            {"heading": "SWOT", "level": 1, "lines": [], "figure": dict(
                FIGURE, grids=[{"title": None, "rows": [[
                    {"label": "Strengths", "bullets": ["not supplied yet"], "gap": None},
                    {"label": "Weaknesses", "bullets": [], "gap": None}]],
                    "axis_x": None, "axis_y": None, "col_widths": [0.5, 0.5]}])},
            {"heading": "Conclusion", "level": 1, "lines": ["Done."]},
            {"heading": "References", "level": 1, "lines": ["Ref."]},
        ]
        issues = paper.check(sections, framework="swot", implications="A position.")
        self.assertTrue(any(issue["type"] == "meta_text" for issue in issues), issues)
```

- [ ] **Step 2: Run it**

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.test_matrix_figure -v
```
Expected: PASS (Task 1 already made this work). If it fails, the Task 1 step that
extends `check()` was not applied — fix it there, not here.

- [ ] **Step 3: Regenerate the samples**

Find how the samples are produced (look for the script that writes
`samples/value-chain-sample-apa7.docx` — search the repo for "value-chain-sample"):

```powershell
Select-String -Path "src\bp\**\*.py","scripts\*.py" -Pattern "value-chain-sample"
```

Regenerate every wave-1 sample with the same command that produced it, so the
committed samples match the current renderer. Check each regenerated file in
Word or a reader to confirm the table renders and the caption reads correctly.

- [ ] **Step 4: Write the record**

`docs/CHANGELOG.md` — one entry under the current heading:

```
- Matrix frameworks now reach the Word paper as a grid: SWOT, Ansoff, Porter's value chain, VRIO,
  McKinsey 7S, BCG, GE/McKinsey and Blue Ocean's four actions carry a figure with the canonical
  cells, axes and order. A cell is never blank: it shows the item identities the student supplied
  or the sources accepted, and where there is nothing it shows the named gap and the probe.
```

`docs/WORKLOG.md` — one entry, tagged `[design]` if it touches the owner's lanes:

```
- [design] Matrix figures in the paper. New: src/bp/product/matrix.py (the layout registry and the
  builder), src/bp/product/assist.py (the chat's cell proposals). Changed: paper.py (the figure
  slot), docx.py (the Word table renderer), completion.py and chat.py (the figure and the
  proposals), api.py (POST /api/cases/{id}/assist), web/index.html (the proposal affordance).
  The frozen core was not touched. No number, claim wording or test was weakened.
```

`docs/DECISIONS.md` — a new B-decision recording the convention:

```
### B-176 — A framework that is a grid reaches the paper as a grid

The decision. The matrix frameworks (SWOT, Ansoff, value chain, VRIO, McKinsey 7S, BCG,
GE/McKinsey, Blue Ocean ERRС) carry a figure in the Word paper, drawn from a layout registry
in the product layer. The renderer draws tables and nothing else; it never names a framework.

Why. The shapes in `Matrix templates/` are the frameworks themselves: a SWOT that arrives as
four paragraphs under four headings has lost the argument the matrix makes. A student who
pastes the figure from a slide deck gets a picture the paper cannot check; a student who
draws it themselves gets four headings in a row. The paper should carry the grid.

The rules. The layout is data, so a new framework never means editing the renderer. The figure
carries no computed number: the percentages stay in the prose, computed by the frozen core. A
cell carries the identity of an item — the student's own sentence, the source's title with its
citation — and the prose below carries the full evidence. A cell is never blank: it shows the
named gap and the probe. The model may restate the student's own words as a proposal the
student accepts, and may not assert a fact about the firm; a proposal carrying a number, a name,
a link or a citation is refused.

What this does not do. The figure is a Word table, not a slide: it carries the structure and
the academic styling, not the colour, the icons or the decoration of the template images.
```

`docs/KNOWN_LIMITATIONS.md` — one limitation:

```
- The matrix figures are Word tables, not pictures. They carry the framework's structure, cells
  and axes in academic styling; they do not reproduce the colour, icons or decoration of the
  slide templates in `Matrix templates/`, and a framework whose layout is genuinely radial
  (the McKinsey hexagon) is drawn as its hub band between its two rows of elements.
```

- [ ] **Step 5: Run the whole suite and compare with the baseline**

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests 2>&1 | Select-Object -Last 30
```
Expected: the same **94 failures and 85 errors** as the measured baseline, and **no new** one.

Compare mechanically rather than by eye:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v 2>&1 |
  Out-File -FilePath "plans\_after_full.txt" -Encoding utf8
Get-Content "plans\_after_full.txt" |
  Where-Object { $_ -match '^(FAIL|ERROR):' } |
  ForEach-Object { ($_ -replace ' \([^)]+\)$','').Trim() } |
  Sort-Object -Unique |
  Set-Content -FilePath "plans\_after_failures.txt" -Encoding utf8
Compare-Object (Get-Content "plans\baseline-failures.txt") (Get-Content "plans\_after_failures.txt")
```

Expected: `Compare-Object` reports no line with a `=>` side marker — nothing new
failing. A `<=` marker means a pre-existing failure is now fixed (good, but say so
in the report). If there is a new failure, fix it before committing.

- [ ] **Step 6: Commit**

```powershell
git add src/bp/product/completion.py src/bp/product/chat.py tests/test_matrix_figure.py samples docs
git commit -m "docs: the matrix figures, the samples that show them and the record of the convention"
```

---

## Self-Review

**1. Spec coverage.**

| Requirement from the discussion | Task |
|---|---|
| Word output (not the web) | Tasks 1, 3, 4, 7 |
| Structure-faithful, professionally drawn | Task 2 (the layout registry), Task 1 (the table renderer) |
| Wave 1: SWOT, Ansoff, Value Chain, VRIO, McKinsey 7S, BCG, GE/McKinsey, Blue Ocean ERRC | Task 2 (all eight layouts), Task 3 (worksheet path), Task 4 (chat path: SWOT, Ansoff, Value Chain, VRIO) |
| The figure sits under the H1 framework heading, in addition to the H2 prose | Tasks 3 and 4 |
| Cells carry labels plus short bullets; the full evidence stays in the H2 | Task 3 (`_figure_cells`), Task 4 (`_figure_cells`) |
| Never blank — the model helps a student who is unsure | Task 5 (worksheet), Task 6 (chat) |
| The model may not invent | Task 5 (the number/link/DOI guard), Task 6 (`assist._problems`) |
| The figure carries no computed number | Task 2 (cells carry titles and the student's words, never a computed figure) |
| No template instructions in the paper | Task 1 (`paper.check` scans figure text), Task 7 (the export gate) |

**2. Placeholder scan.** No "TBD", no "implement later", no "similar to Task N". Every
code step carries the actual code. Two places need the implementer to read the file first
and match an existing pattern — `src/bp/product/api.py`'s case-loading helpers and
`tests/test_chat.py`'s state fixture — and both say so explicitly and say what to match.

**3. Type consistency.** `matrix.build(template, cells, caption=None) -> dict | None` is
used identically in Tasks 3 and 4. `paper.section(heading, level, lines=None, figure=None)`
is used identically in Tasks 1, 3 and 4. `docx._figure_xml(figure, number)` is defined in
Task 1 and called only there. The cell keys — `{"label", "bullets", "gap"}` — are the same
in Tasks 2, 3, 4 and 5. `assist.propose(state, key, label) -> dict` is defined in Task 6
and called only there.

**Known gap, stated rather than hidden:** the McKinsey 7S hexagon and the Blue Ocean
four-action grid are the two layouts that a table renders less faithfully than the slide
image. Task 2 draws 7S as its hub band between two rows of elements, and ERRС as four
columns. Both keep every cell and its canonical name. This is recorded in
`docs/KNOWN_LIMITATIONS.md` in Task 7.
