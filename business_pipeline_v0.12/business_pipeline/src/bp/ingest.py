"""Structured-file ingestion (gap map P0; B-065). Standard library only.

What it does: reads CSV/TSV and XLSX (XLSX is a zip of XML parts, so `zipfile` + `xml.etree` suffice) into a
typed table — column names, inferred types, missing counts — with a table-level provenance pointer back to the
file, its SHA-256 and the sheet. It does NOT read PDFs, scans or SPSS files: no OCR and no PDF text extraction
is implemented, so those are REFUSED with an explicit message instead of pretending the data was read.

Declared conventions: the first non-empty row is the header; header names must be non-empty and unique after
trimming; a column mixing numbers and text is typed `mixed` (never silently coerced); a missing cell is an
empty or whitespace-only value; formula cells use the cached value stored in the file (a formula with no cached
value is a missing cell); XLSX date cells use the workbook date system with the standard 1900 leap-year
adjustment. Caps: 1000 data rows and 50 columns, refused beyond that rather than truncated.
"""
import base64, csv, hashlib, io, json, re, zipfile
from datetime import date, timedelta
from decimal import Decimal as D, InvalidOperation
from xml.etree import ElementTree as ET

MAX_ROWS = 1000
MAX_COLS = 50
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

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
    cols = []
    for j, name in enumerate(names):
        values = [r[j] if j < len(r) else "" for r in rows]
        present = [v for v in values if not _is_missing(v)]
        cols.append({"name": name, "type": _infer(values), "n_missing": len(values) - len(present),
                     "n_present": len(present), "sample": present[:5]})
    table = {**meta, "n_rows": len(rows), "n_cols": len(names), "columns": cols,
             "rows": [[(v if not _is_missing(v) else None) for v in row] for row in rows],
             "provenance": {"kind": "sourced", "file": meta.get("filename"), "sha256": meta.get("sha256"),
                            "locator": "data row i, column j (1-based, header row excluded)" + (f", sheet {meta['sheet']!r}" if meta.get("sheet") else ""),
                            "note": "Every value is taken from the named file at that locator; nothing is imputed or retyped."},
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

def read_xlsx(raw, filename):
    try: z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile: raise IngestError("the XLSX file is not a readable zip archive")
    sh = _shared_strings(z)
    styles, date1904 = _date_styles(z)
    wb = _xml(z, "xl/workbook.xml")
    if wb is None: raise IngestError("the XLSX file has no workbook part")
    ns = wb.tag.split("}")[0] + "}" if wb.tag.startswith("{") else ""
    sheets = wb.find(ns + "sheets")
    if sheets is None or not list(sheets): raise IngestError("the workbook has no sheets")
    first = list(sheets)[0]
    sheet_name = first.get("name") or "sheet1"
    rels = _xml(z, "xl/_rels/workbook.xml.rels")
    target = None
    if rels is not None:
        rns = rels.tag.split("}")[0] + "}" if rels.tag.startswith("{") else ""
        rid = first.get("{%s}id" % ns.strip("}")) if ns else first.get("r:id")
        for rel in rels.findall(rns + "Relationship"):
            if rel.get("Id") == rid: target = rel.get("Target")
    if not target: target = "worksheets/sheet1.xml"
    target = target.lstrip("/")
    part = target if target.startswith("xl/") else "xl/" + target
    ws = _xml(z, part)
    if ws is None: raise IngestError(f"the first sheet part {part!r} is missing")
    wns = ws.tag.split("}")[0] + "}" if ws.tag.startswith("{") else ""
    grid = {}
    max_row = max_col = 0
    for row in ws.iter(wns + "row"):
        for c in row.findall(wns + "c"):
            ref = c.get("r") or ""
            m = re.fullmatch(r"([A-Z]+)(\d+)", ref)
            if not m: continue
            col = 0
            for ch in m.group(1): col = col * 26 + (ord(ch) - 64)
            r_i = int(m.group(2)); col -= 1
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
            grid[(r_i, col)] = val; max_row = max(max_row, r_i); max_col = max(max_col, col)
    if not grid: raise IngestError("the first sheet is empty")
    if max_row - 1 > MAX_ROWS: raise IngestError(f"too many data rows ({max_row - 1}); the cap is {MAX_ROWS}")
    if max_col + 1 > MAX_COLS: raise IngestError(f"too many columns ({max_col + 1}); the cap is {MAX_COLS}")
    rows = [[grid.get((r, c), "") for c in range(max_col + 1)] for r in range(1, max_row + 1)]
    header = rows[0]
    return _table(header, rows[1:], {"filename": filename, "kind": "xlsx", "sha256": sha(raw), "sheet": sheet_name})

def read_table(filename, raw):
    kind = sniff(filename, raw)
    if kind == "csv": return read_csv(raw, filename)
    if kind == "xlsx": return read_xlsx(raw, filename)
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
    if errs: raise IngestError("the mapped columns do not form a valid request for " + method_id + ": " + "; ".join(errs))
    prof = m.profile(out)
    if prof: raise IngestError("the mapped columns fail the method's pre-checks: " + "; ".join(prof))
    return {"method": method_id, "inputs": out,
            "provenance": {"kind": "sourced", "file": table.get("filename"), "sha256": table.get("sha256"),
                           "locator": table.get("provenance", {}).get("locator"),
                           "note": "Values were read from the named file; the pipeline records them as owner-supplied. The file hash identifies the source, it does not verify the data."},
            "not_mapped": sorted(k for k in m.input_schema if k not in out)}

def decode_request(body):
    """API helper: {'filename': str, 'content_base64': str} -> (table). Validates shape and size first."""
    if not isinstance(body, dict): raise IngestError("body must be an object")
    filename, b64 = body.get("filename"), body.get("content_base64")
    if not isinstance(filename, str) or not filename.strip(): raise IngestError("filename is required")
    if not isinstance(b64, str) or not b64.strip(): raise IngestError("content_base64 is required")
    try: raw = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError): raise IngestError("content_base64 is not valid base64")
    if len(raw) > 5_000_000: raise IngestError("the file is over the 5 MB ingestion limit")
    return read_table(filename, raw)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2: print("usage: python -m bp.ingest <file.csv|file.xlsx>"); raise SystemExit(2)
    p = sys.argv[1]
    with open(p, "rb") as f: data = f.read()
    t = read_table(p, data)
    summary = {k: t[k] for k in ("filename", "kind", "sha256", "sheet", "n_rows", "n_cols") if k in t}
    summary["columns"] = t["columns"]; summary["provenance"] = t["provenance"]
    print(json.dumps(summary, indent=2, ensure_ascii=False))
