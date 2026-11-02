"""Structured-file ingestion (gap map P0; B-065). Standard library only.

What it does: reads CSV/TSV and XLSX (XLSX is a zip of XML parts, so `zipfile` + `xml.etree` suffice) into a
typed table — column names, inferred types, missing counts — with a table-level provenance pointer back to the
file, its SHA-256 and the sheet. It does NOT read PDFs, scans or SPSS files: no OCR and no PDF text extraction
is implemented, so those are REFUSED with an explicit message instead of pretending the data was read.

Declared conventions: the first non-empty row is the header; header names must be non-empty and unique after
trimming; a column mixing numbers and text is typed `mixed` (never silently coerced); a missing cell is an
empty or whitespace-only value; formula cells use the cached value stored in the file (a formula with no cached
value is a missing cell); XLSX date cells use the workbook date system with the standard 1900 leap-year
adjustment.

XLSX sheet selection (B-076): the default is the first sheet; `sheet=<name>` (exact, case-sensitive) or
`sheet=<n>` (1-based) selects another, and an unknown sheet is refused with the available names listed. Merged
cells are REFUSED by default because expanding an anchor value across its range, or dropping the blanks,
would fabricate or lose data; the caller may declare `merged="top_left"` to expand each range from its anchor
cell, and that declared expansion is recorded on the table and in its provenance note. Caps: 1000 data rows
and 50 columns, refused beyond that rather than truncated.
"""
import base64, csv, hashlib, io, json, re, zipfile
from datetime import date, timedelta
from decimal import Decimal as D, InvalidOperation
from xml.etree import ElementTree as ET

MAX_ROWS = 1000
MAX_COLS = 50
MERGED_POLICIES = ("refuse", "top_left")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RANGE = re.compile(r"([A-Z]+)(\d+):([A-Z]+)(\d+)")
_REF = re.compile(r"([A-Z]+)(\d+)")

class IngestError(ValueError):
    """The file cannot be ingested as a structured table (unsupported type, malformed, or over the caps)."""

def sha(raw): return hashlib.sha256(raw).hexdigest()

def sniff(filename, raw):
    name = (filename or "").lower()
    if raw[:2] == b"PK" and name.endswith((".xlsx", ".xlsm")): return "xlsx"
    if raw[:4] == b"%PDF" or name.endswith(".pdf"): return "pdf"
    if name.endswith(".sav"): return "spss"
    if name.endswith((".csv", ".tsv", ".txt")): return "csv"
    return "unsupported"

def _decode(raw):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: continue
    raise IngestError("the file is not text in UTF-8, CP1252 or Latin-1")

def _is_missing(x): return x is None or (isinstance(x, str) and not x.strip())

def _check_header(header):
    names = [h.strip() for h in header]
    if not any(names): raise IngestError("the header row is empty")
    if len(names) > MAX_COLS: raise IngestError(f"too many columns ({len(names)}); the cap is {MAX_COLS}")
    if any(not n for n in names): raise IngestError("every column needs a header; a blank header is refused")
    low = [n.lower() for n in names]
    dup = sorted({n for n in low if low.count(n) > 1})
    if dup: raise IngestError("duplicate column names after trimming: " + ", ".join(dup))
    return names

def _number(tok):
    try: D(tok.strip()); return True
    except (InvalidOperation, ValueError, AttributeError): return False

def _infer(values):
    present = [v for v in values if not _is_missing(v)]
    if not present: return "text"
    nums = [v for v in present if _number(v)]
    dates = [v for v in present if _ISO.match(str(v).strip())]
    if len(nums) == len(present): return "number"
    if len(dates) == len(present): return "date"
    if nums and len(nums) < len(present): return "mixed"
    return "text"

def _table(header, rows, meta):
    names = _check_header(header)
    if len(rows) > MAX_ROWS: raise IngestError(f"too many data rows ({len(rows)}); the cap is {MAX_ROWS}")
    notes = meta.pop("provenance_notes", [])
    cols = []
    for j, name in enumerate(names):
        values = [r[j] if j < len(r) else "" for r in rows]
        present = [v for v in values if not _is_missing(v)]
        cols.append({"name": name, "type": _infer(values), "n_missing": len(values) - len(present),
                     "n_present": len(present), "sample": present[:5]})
    note = "Every value is taken from the named file at that locator; nothing is imputed or retyped."
    if notes: note += " " + " ".join(notes)
    table = {**meta, "n_rows": len(rows), "n_cols": len(names), "columns": cols,
             "rows": [[(v if not _is_missing(v) else None) for v in row] for row in rows],
             "provenance": {"kind": "sourced", "file": meta.get("filename"), "sha256": meta.get("sha256"),
                            "locator": "data row i, column j (1-based, header row excluded)" + (f", sheet {meta['sheet']!r}" if meta.get("sheet") else ""),
                            "note": note},
             "not_read_as": "PDF, scans, images and SPSS .sav files are not ingested; no OCR or PDF text extraction is implemented."}
    return table

def read_csv(raw, filename):
    text = _decode(raw)
    if not text.strip(): raise IngestError("the file is empty")
    try: delim = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
    except csv.Error: delim = ","
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(not _is_missing(c) for c in r)]
    if not rows: raise IngestError("no rows found")
    return _table(rows[0], rows[1:], {"filename": filename, "kind": "csv", "sha256": sha(raw), "delimiter": delim})

def _xml(z, name):
    try: return ET.fromstring(z.read(name))
    except KeyError: return None
    except ET.ParseError as e: raise IngestError(f"malformed XLSX part {name}: {e}")

def _shared_strings(z):
    root = _xml(z, "xl/sharedStrings.xml")
    if root is None: return []
    out = []
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    for si in root.findall(ns + "si"):
        out.append("".join(t.text or "" for t in si.iter(ns + "t")))
    return out

def _date_styles(z):
    """Indices of cellXfs entries that render as dates, plus the workbook date system."""
    root = _xml(z, "xl/styles.xml")
    if root is None: return set(), False
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    custom = {}
    nf = root.find(ns + "numFmts")
    if nf is not None:
        for f in nf.findall(ns + "numFmt"):
            custom[f.get("numFmtId")] = (f.get("formatCode") or "")
    builtin_date = {str(i) for i in list(range(14, 23)) + [45, 46, 47]}
    xfs = root.find(ns + "cellXfs")
    styles = set()
    if xfs is not None:
        for idx, xf in enumerate(xfs.findall(ns + "xf")):
            nid = xf.get("numFmtId") or "0"
            code = custom.get(nid, "")
            if nid in builtin_date or (code and re.search(r"[dmyhs]", code, re.I) and not re.search(r"#|0\.0", code)):
                styles.add(idx)
    return styles, False

def _serial_to_date(serial, date1904=False):
    n = float(D(str(serial)))
    if date1904: return (date(1904, 1, 1) + timedelta(days=int(n))).isoformat()
    base = date(1899, 12, 30)
    days = int(n)
    if days < 61: days -= 1          # the 1900 leap-year bug: serial 60 is a non-existent 29 February
    return (base + timedelta(days=days)).isoformat()

def _col_number(letters):
    col = 0
    for ch in letters: col = col * 26 + (ord(ch) - 64)
    return col - 1

def _ref_name(r, c):
    letters, n = "", c + 1
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return "%s%d" % (letters, r)

_RELID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

def _sheet_entries(wb, ns):
    sheets = wb.find(ns + "sheets")
    if sheets is None or not list(sheets): raise IngestError("the workbook has no sheets")
    return [((s.get("name") or "sheet%d" % (i + 1)), s.get(_RELID)) for i, s in enumerate(list(sheets))]

def _pick_sheet(entries, sheet):
    names = [n for n, _ in entries]
    if sheet is None: return 0
    if isinstance(sheet, bool): raise IngestError("sheet must be a sheet name or a 1-based sheet number, not a boolean")
    if isinstance(sheet, int):
        if 1 <= sheet <= len(entries): return sheet - 1
        raise IngestError("sheet number %d is out of range; the workbook has %d sheet(s): %s" % (sheet, len(entries), ", ".join(names)))
    if isinstance(sheet, str):
        if sheet in names: return names.index(sheet)
        raise IngestError("unknown sheet %r; the workbook has: %s" % (sheet, ", ".join(repr(n) for n in names)))
    raise IngestError("sheet must be a sheet name or a 1-based sheet number")

def _rels(z):
    rels = _xml(z, "xl/_rels/workbook.xml.rels")
    if rels is None: return {}
    rns = rels.tag.split("}")[0] + "}" if rels.tag.startswith("{") else ""
    return {rel.get("Id"): rel.get("Target") for rel in rels.findall(rns + "Relationship")}

def _merge_cells(ws, wns):
    mc = ws.find(wns + "mergeCells")
    if mc is None: return []
    out = []
    for m in list(mc):
        ref = (m.get("ref") or "").strip()
        mm = _RANGE.fullmatch(ref)
        if not mm: raise IngestError("malformed merged-cell range %r" % ref)
        c1, r1, c2, r2 = _col_number(mm.group(1)), int(mm.group(2)), _col_number(mm.group(3)), int(mm.group(4))
        if c1 > c2: c1, c2 = c2, c1
        if r1 > r2: r1, r2 = r2, r1
        out.append((r1, c1, r2, c2, ref))
    return out

def _expand_merges(grid, ranges):
    """Apply the declared merged='top_left' policy: repeat the anchor value across each range, and refuse an
    overlap with another value (a nested/overlapping merge is a malformed workbook, not a convention)."""
    expanded = []
    for r1, c1, r2, c2, ref in ranges:
        anchor = grid.get((r1, c1))
        if _is_missing(anchor): continue
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if (r, c) == (r1, c1): continue
                if not _is_missing(grid.get((r, c))):
                    raise IngestError("merged range %r overlaps a cell that already has a value (%s); overlapping or nested merges are malformed" % (ref, _ref_name(r, c)))
                grid[(r, c)] = anchor
        expanded.append(ref)
    return expanded

def read_xlsx(raw, filename, sheet=None, merged="refuse"):
    if merged not in MERGED_POLICIES:
        raise IngestError("merged must be one of: " + ", ".join(MERGED_POLICIES))
    try: z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile: raise IngestError("the XLSX file is not a readable zip archive")
    sh = _shared_strings(z)
    styles, date1904 = _date_styles(z)
    wb = _xml(z, "xl/workbook.xml")
    if wb is None: raise IngestError("the XLSX file has no workbook part")
    ns = wb.tag.split("}")[0] + "}" if wb.tag.startswith("{") else ""
    entries = _sheet_entries(wb, ns)
    index = _pick_sheet(entries, sheet)
    sheet_name, rid = entries[index]
    target = _rels(z).get(rid)
    if not target and index == 0: target = "worksheets/sheet1.xml"
    if not target: raise IngestError("the selected sheet %r has no worksheet part in the workbook" % sheet_name)
    target = target.lstrip("/")
    part = target if target.startswith("xl/") else "xl/" + target
    ws = _xml(z, part)
    if ws is None: raise IngestError("the sheet part %r (sheet %r) is missing" % (part, sheet_name))
    wns = ws.tag.split("}")[0] + "}" if ws.tag.startswith("{") else ""
    grid = {}
    for row in ws.iter(wns + "row"):
        for c in row.findall(wns + "c"):
            ref = c.get("r") or ""
            m = _REF.fullmatch(ref)
            if not m: continue
            col = _col_number(m.group(1))
            r_i = int(m.group(2))
            t = c.get("t"); v = c.find(wns + "v"); is_ = c.find(wns + "is")
            if t == "inlineStr" and is_ is not None: val = "".join(x.text or "" for x in is_.iter(wns + "t"))
            elif v is None: continue
            elif t == "s":
                try: val = sh[int(v.text)]
                except (ValueError, IndexError): raise IngestError(f"shared string reference out of range at {ref}")
            elif t == "b": val = "TRUE" if v.text == "1" else "FALSE"
            elif t in ("str", "e"): val = v.text or ""
            else:
                s = c.get("s")
                try: style = int(s) if s is not None else None
                except ValueError: style = None
                val = _serial_to_date(v.text, date1904) if style in styles else (v.text or "")
            grid[(r_i, col)] = val
    ranges = _merge_cells(ws, wns)
    if ranges and merged == "refuse":
        shown = ", ".join(ref for _, _, _, _, ref in ranges[:5])
        more = "" if len(ranges) <= 5 else " and %d more" % (len(ranges) - 5)
        raise IngestError("the sheet %r has %d merged cell range(s) (%s%s); merged cells are refused by default because expanding the anchor value across a range, or dropping the blanks, would fabricate or lose data. Unmerge and re-export, or declare merged='top_left' to accept the expansion" % (sheet_name, len(ranges), shown, more))
    expanded = _expand_merges(grid, ranges) if ranges else []
    if not grid: raise IngestError("the sheet %r is empty" % sheet_name)
    max_row = max(r for r, _ in grid)
    max_col = max(c for _, c in grid)
    if max_row - 1 > MAX_ROWS: raise IngestError(f"too many data rows ({max_row - 1}); the cap is {MAX_ROWS}")
    if max_col + 1 > MAX_COLS: raise IngestError(f"too many columns ({max_col + 1}); the cap is {MAX_COLS}")
    rows = [[grid.get((r, c), "") for c in range(max_col + 1)] for r in range(1, max_row + 1)]
    header = rows[0]
    meta = {"filename": filename, "kind": "xlsx", "sha256": sha(raw), "sheet": sheet_name,
            "sheets": [n for n, _ in entries], "sheet_index": index + 1, "merged_policy": merged}
    if expanded:
        meta["merged_cells"] = expanded
        meta["provenance_notes"] = ["%d merged cell range(s) (%s) were expanded from their anchor cell under the declared merged='top_left' policy; the anchor value was repeated across each range." % (len(expanded), ", ".join(expanded))]
    return _table(header, rows[1:], meta)

def read_table(filename, raw, sheet=None, merged="refuse"):
    kind = sniff(filename, raw)
    if kind == "csv":
        if sheet is not None: raise IngestError("sheet selection applies to XLSX workbooks only")
        if merged != "refuse": raise IngestError("the merged-cell policy applies to XLSX workbooks only")
        return read_csv(raw, filename)
    if kind == "xlsx": return read_xlsx(raw, filename, sheet=sheet, merged=merged)
    if kind == "pdf": raise IngestError("PDF ingestion is not implemented: no PDF text extraction or OCR exists, and reading a scan as data would be invention. Convert the source to CSV/XLSX, or paste the values with their source.")
    if kind == "spss": raise IngestError("SPSS .sav ingestion is not implemented; export the file to CSV/XLSX first.")
    raise IngestError("unsupported file type: supply a .csv/.tsv or .xlsx file (PDF, scans and .sav are refused)")

_NUMBERISH = ("number",)

def to_method_inputs(table, method_id, mapping):
    """Map named table columns into a method's declared inputs (B-071). Pure computation, no semantics invented:
    only the mapping the caller supplies is used, and only list-shaped inputs are accepted (a scalar such as a
    discount rate cannot come from a column).

    Supported shapes: a `value_list`/`code_list` input maps from one column name (missing cells become null);
    a `column_map` input (groups, predictors, pairs) maps from an object of output-name -> column name.
    A mapping that leaves a required input out is a **partial proposal**: the input is named in
    `not_mapped` and the student supplies it, because a plan block mixes list inputs (revenue by period)
    with declared drivers (the gross margin).  What a mapping gets wrong is still refused — a scalar that
    a column cannot feed, an unknown column, a column that mixes numbers and text, a value that fails its
    own rule — never what it leaves to the student.  Nothing here runs the method.
    The returned request carries a provenance note naming the file and hash. Mapping does not upgrade the data:
    the pipeline still treats it as owner-supplied and the note says so.
    """
    from . import methods as methodlib
    m = methodlib.LIBRARY.get(method_id)
    if m is None: raise IngestError(f"unknown method {method_id!r}; GET /api/methods lists the available ids")
    if not isinstance(mapping, dict) or not mapping: raise IngestError("map must be an object of method-input name -> column name")
    cols = {c["name"]: c for c in table["columns"]}
    rows = table["rows"]
    def column(name):
        if not isinstance(name, str) or name not in cols: raise IngestError(f"unknown column {name!r}; the file has: " + ", ".join(cols))
        idx = [c["name"] for c in table["columns"]].index(name)
        return [r[idx] if idx < len(r) else None for r in rows]
    out = {}
    for key, spec in m.input_schema.items():
        if key not in mapping: continue
        t = spec["type"]; target = mapping[key]
        if t in ("value_list", "code_list"):
            if not isinstance(target, str): raise IngestError(f"'{key}' takes one column name")
            vals = column(target)
            if t == "value_list" and spec.get("min_items", 0) and cols[target]["type"] == "mixed":
                raise IngestError(f"column {target!r} mixes numbers and text; it cannot feed '{key}' without a declared conversion")
            out[key] = vals
        elif t == "column_map":
            if not isinstance(target, dict) or not target: raise IngestError(f"'{key}' takes an object of name -> column name")
            out[key] = {name: column(c) for name, c in target.items()}
        else:
            raise IngestError(f"'{key}' has type {t!r}, which cannot be mapped from a column; provide it directly in the request")
    errs = methodlib.validate_inputs(m, out)
    # A mapping that names no input this method declares is a mistake, not a proposal.
    if not out:
        raise IngestError("the mapping names no input of " + method_id + ": it maps "
                          + ", ".join(sorted(str(name) for name in mapping))
                          + " and the method takes " + ", ".join(sorted(m.input_schema)))
    # An input the student did not map is not a mapping error.  The proposal names
    # every input still to be supplied in `not_mapped`, and the form still asks for
    # it — which is exactly the shape a plan block has: its lists come from the
    # file and its drivers are typed.  A value the mapping *did* supply and that
    # fails its own rule is still refused, in the core's own words.
    missing = [e for e in errs if e.startswith("missing required input '")]
    errs = [e for e in errs if e not in missing]
    if errs: raise IngestError("the mapped columns do not form a valid request for " + method_id + ": " + "; ".join(errs))
    prof = m.profile(out) if not missing else []
    if prof: raise IngestError("the mapped columns fail the method's pre-checks: " + "; ".join(prof))
    # Which columns actually fed the request, so the session can carry the file and its hash
    # as a manifest entry and each mapped input can say where it came from (B-071).
    used = set()
    for key, target in mapping.items():
        if key not in out:
            continue
        if isinstance(target, str):
            used.add(target)
        else:
            used.update(str(name) for name in target.values())
    return {"method": method_id, "inputs": out,
            "provenance": {"kind": "sourced", "file": table.get("filename"), "sha256": table.get("sha256"),
                           "locator": table.get("provenance", {}).get("locator"),
                           "note": "Values were read from the named file; the pipeline records them as owner-supplied. The file hash identifies the source, it does not verify the data."},
            "input_provenance": {k: "sourced" for k in out},
            "data_manifest": [{"kind": "file", "file": table.get("filename"),
                               "sha256": table.get("sha256"), "columns": sorted(used),
                               "note": "Read from the named file; the hash identifies the source, it does not verify the data."}],
            "not_mapped": sorted(k for k in m.input_schema if k not in out)}

def decode_request(body):
    """API helper: {'filename': str, 'content_base64': str} -> (table). Validates shape and size first.
    Optional `sheet` (name or 1-based number) and `merged` ('refuse' | 'top_left') select the XLSX sheet and
    the merged-cell policy; both are refused for CSV/TSV because they would silently do nothing."""
    if not isinstance(body, dict): raise IngestError("body must be an object")
    filename, b64 = body.get("filename"), body.get("content_base64")
    if not isinstance(filename, str) or not filename.strip(): raise IngestError("filename is required")
    if not isinstance(b64, str) or not b64.strip(): raise IngestError("content_base64 is required")
    merged = body.get("merged", "refuse")
    if not isinstance(merged, str) or merged not in MERGED_POLICIES:
        raise IngestError("merged must be one of: " + ", ".join(MERGED_POLICIES))
    try: raw = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError): raise IngestError("content_base64 is not valid base64")
    if len(raw) > 5_000_000: raise IngestError("the file is over the 5 MB ingestion limit")
    return read_table(filename, raw, sheet=body.get("sheet"), merged=merged)

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("usage: python -m bp.ingest <file.csv|file.xlsx> [--sheet NAME|N] [--merged refuse|top_left]"); raise SystemExit(2)
    opts, rest = {}, []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--sheet", "--merged"):
            if i + 1 >= len(args): print("missing value for " + a); raise SystemExit(2)
            opts[a[2:]] = args[i + 1]; i += 2
        else:
            rest.append(a); i += 1
    if len(rest) != 1: print("usage: python -m bp.ingest <file.csv|file.xlsx> [--sheet NAME|N] [--merged refuse|top_left]"); raise SystemExit(2)
    p = rest[0]
    sheet = opts.get("sheet")
    if isinstance(sheet, str) and sheet.isdigit(): sheet = int(sheet)
    with open(p, "rb") as f: data = f.read()
    try:
        t = read_table(p, data, sheet=sheet, merged=opts.get("merged", "refuse"))
    except IngestError as e:
        print("error: " + str(e)); raise SystemExit(1)
    summary = {k: t[k] for k in ("filename", "kind", "sha256", "sheet", "sheets", "sheet_index", "merged_policy",
                                 "merged_cells", "n_rows", "n_cols") if k in t}
    summary["columns"] = t["columns"]; summary["provenance"] = t["provenance"]
    print(json.dumps(summary, indent=2, ensure_ascii=False))
