"""Parse an uploaded file into a tile case, gate it, and store it.

The gate is the point: a file is accepted only when its inputs pass the frozen
method's own validation and the method runs.  A rejected file is never written,
so the case store cannot fill with cases that cannot replay.

Formats:
    .json          a case in the stored schema
    .csv / .tsv    a table; headers map automatically onto the method's inputs
    .xlsx / .xlsm  the first worksheet, same automatic mapping
    .docx .pdf .txt .md .png .jpg   the instruction text, replayed against the
                                      tile's published figures
"""

import csv
import io
import json
import os
import re
import zipfile

from .. import methods
from . import case_store
from . import documents
from . import paper_batch

MAX_UPLOAD = 25 * 1024 * 1024


def _header(text):
    return re.sub(r"[^a-z0-9]+", "_", str(text or "").strip().lower()).strip("_")


def _read_csv(raw):
    text = raw.decode("utf-8-sig", errors="replace")
    sample = text[:2048]
    delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
    rows = [list(row) for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    return [row for row in rows if any(str(cell).strip() for cell in row)]


def _xlsx_cell(cell, shared):
    reference = re.search(r'r="([A-Z]+)\d+"', cell)
    if not reference:
        return None, None
    kind = re.search(r't="([^"]+)"', cell)
    value = re.search(r"<v>(.*?)</v>", cell, re.S)
    if value:
        text = value.group(1)
        if kind and kind.group(1) == "s":
            try:
                text = shared[int(text)]
            except (ValueError, IndexError):
                text = ""
        return reference.group(1), text
    inline = re.search(r"<is>.*?<t[^>]*>(.*?)</t>.*?</is>", cell, re.S)
    if inline:
        return reference.group(1), inline.group(1)
    return reference.group(1), ""


def _read_xlsx(raw):
    archive = zipfile.ZipFile(io.BytesIO(raw))
    shared = []
    if "xl/sharedStrings.xml" in archive.namelist():
        xml = archive.read("xl/sharedStrings.xml").decode("utf-8")
        shared = [re.sub(r"<[^>]+>", "", item)
                  for item in re.findall(r"<si>(.*?)</si>", xml, re.S)]
    sheets = sorted(name for name in archive.namelist()
                    if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
    if not sheets:
        raise ValueError("the workbook has no worksheet")
    xml = archive.read(sheets[0]).decode("utf-8")
    rows = []
    for row_xml in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S):
        cells = {}
        for cell_xml in re.findall(r"<c[^>]*?(?:/>|>.*?</c>)", row_xml, re.S):
            column, value = _xlsx_cell(cell_xml, shared)
            if column is not None:
                cells[column] = value
        ordered = [cells[key] for key in sorted(cells, key=lambda key: (len(key), key))]
        if any(str(value).strip() for value in ordered):
            rows.append(ordered)
    return rows


def _read_document(raw, filename):
    return str(documents.extract_document(raw, filename) or "").strip()


def _find_header(headers, name):
    target = _header(name)
    for index, value in enumerate(headers):
        if value == target:
            return index
    for index, value in enumerate(headers):
        if value.replace("_", "") == target.replace("_", ""):
            return index
    return None


def _map_table(rows, schema):
    """Map a table's headers onto the method's input names, automatically."""
    if len(rows) < 2:
        raise ValueError("the table needs a header row and at least one data row")
    headers = [_header(value) for value in rows[0]]
    inputs = {}
    for name, spec in (schema or {}).items():
        kind = str(spec.get("type") or "")
        required = bool(spec.get("required", True))
        if kind in ("records", "rows", "object") or int(spec.get("min_items") or 1) > 1:
            fields = list(spec.get("fields") or {})
            indexes = {field: _find_header(headers, field) for field in fields}
            missing = [field for field, index in indexes.items() if index is None]
            if missing:
                if required:
                    raise ValueError("the table is missing the column(s): " + ", ".join(missing))
                continue
            items = []
            for row in rows[1:]:
                item = {field: (row[index] if index < len(row) else "")
                        for field, index in indexes.items()}
                if any(str(value).strip() for value in item.values()):
                    items.append(item)
            if required and not items:
                raise ValueError("the table has no rows for " + name)
            inputs[name] = items
            continue
        index = _find_header(headers, name)
        if index is None:
            if required:
                raise ValueError("the table is missing the column: " + name)
            continue
        value = next((row[index] for row in rows[1:]
                      if index < len(row) and str(row[index]).strip()), "")
        if not str(value).strip():
            if required:
                raise ValueError("the column " + name + " has no value")
            continue
        inputs[name] = value
    return inputs


def _schema(tile):
    try:
        described = methods.describe(tile.get("method") or "") or {}
    except Exception:
        described = {}
    return described.get("input_schema") or {}


def _dry_run(tile, inputs):
    method = methods.LIBRARY.get(tile.get("method") or "")
    if method is None:
        raise ValueError("the method %r is not in the frozen core" % (tile.get("method"),))
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(str(error) for error in errors)[:300])
    return method.impl(inputs)


def _next_path(subject, tile_key):
    folder = os.path.join(case_store._root(), case_store._slug(subject),
                          case_store._slug(tile_key))
    os.makedirs(folder, exist_ok=True)
    number = 1
    while os.path.exists(os.path.join(folder, "case_%03d.json" % number)):
        number += 1
    return os.path.join(folder, "case_%03d.json" % number), number


def _store(subject, tile_key, filename, instruction, inputs, recorded, expected=None):
    subject_info, group, tile = paper_batch._find_tile(subject, tile_key)
    path, number = _next_path(subject, tile_key)
    payload = {
        "format": case_store.FORMAT,
        "id": "%s/%s/%03d" % (case_store._slug(subject), case_store._slug(tile_key), number),
        "subject": subject,
        "subject_label": subject_info.get("label") or subject,
        "tile": tile_key,
        "method": tile.get("method") or "",
        "tile_label": tile.get("label") or tile_key,
        "group": group.get("label") or "",
        "objective": (paper_batch.brief_for(subject, tile_key) or {}).get("objective") or "",
        "instruction": str(instruction or "").strip(),
        "inputs": inputs,
        "expected": expected or {
            "status": "ok",
            "result": case_store._recorded(recorded),
            "contains": [tile.get("label") or tile_key, "What you declared", "How the figures were checked"],
            "xlsx_sheets": ["Summary", "Inputs", "Results", "Record"],
        },
        "created_at": case_store._now(),
        "origin": "uploaded",
        "source_file": str(filename or "")[:200],
    }
    case_store._write(path, payload)
    return payload


def upload(subject, tile_key, filename, raw):
    """Parse one uploaded file, gate it, and store it as a case."""
    try:
        import time as _t
        _debug = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "state", "upload_debug.log")
        os.makedirs(os.path.dirname(_debug), exist_ok=True)
        with open(_debug, "a", encoding="utf-8") as _fh:
            _fh.write("%s | %s | %s | %s bytes | %r\n" % (
                _t.strftime("%Y-%m-%dT%H:%M:%S"), subject, filename,
                len(raw) if isinstance(raw, (bytes, bytearray)) else -1,
                bytes(raw)[:60] if isinstance(raw, (bytes, bytearray)) else raw))
    except Exception:
        pass
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise ValueError("the uploaded file is empty")
    if len(raw) > MAX_UPLOAD:
        raise ValueError("the file is over the 5 MB upload limit")
    subject_info, _group, tile = paper_batch._find_tile(subject, tile_key)
    ext = os.path.splitext(str(filename or ""))[1].lower()
    info = paper_batch.brief_for(subject, tile_key)

    if ext == ".json":
        try:
            document = json.loads(bytes(raw).decode("utf-8"))
        except Exception as error:
            raise ValueError("the JSON is not readable: " + str(error)[:160])
        if not isinstance(document, dict):
            raise ValueError("a JSON case must be an object")
        if isinstance(document.get("problems"), list):
            from . import case_upload_bundle as _cub
            return _cub.upload_bundle(subject, tile_key, filename, raw)
        if document.get("tile") and document["tile"] != tile_key:
            raise ValueError("the case names tile %r, but %r was selected"
                             % (document.get("tile"), tile_key))
        inputs = document.get("inputs")
        if not isinstance(inputs, dict) or not inputs:
            raise ValueError("the case declares no inputs (keys seen: %s)"
                             % (", ".join(sorted(str(k) for k in document)) or "none"))
        instruction = document.get("instruction") or info["brief"]
        recorded = _dry_run(tile, inputs)
        expected = document.get("expected") if isinstance(document.get("expected"), dict) else None
        if expected:
            expected.setdefault("status", "ok")
            expected.setdefault("result", case_store._recorded(recorded))
            expected.setdefault("contains", [tile.get("label") or tile_key,
                                            "What you declared", "How the figures were checked"])
            expected.setdefault("xlsx_sheets", ["Summary", "Inputs", "Results", "Record"])
        return _store(subject, tile_key, filename, instruction, inputs, recorded, expected)

    if ext in (".csv", ".tsv"):
        rows = _read_csv(bytes(raw))
        inputs = _map_table(rows, _schema(tile))
        recorded = _dry_run(tile, inputs)
        instruction = paper_batch._brief(subject_info, tile, info["objective"], inputs)
        return _store(subject, tile_key, filename, instruction, inputs, recorded)

    if ext in (".xlsx", ".xlsm"):
        rows = _read_xlsx(bytes(raw))
        inputs = _map_table(rows, _schema(tile))
        recorded = _dry_run(tile, inputs)
        instruction = paper_batch._brief(subject_info, tile, info["objective"], inputs)
        return _store(subject, tile_key, filename, instruction, inputs, recorded)

    if ext in (".docx", ".docm", ".pdf", ".txt", ".text", ".md",
               ".png", ".jpg", ".jpeg", ".webp"):
        text = _read_document(bytes(raw), filename)
        if len(text) < 15:
            raise ValueError("the document has no readable instruction text")
        inputs = info.get("inputs") or {}
        if not inputs:
            raise ValueError("this tile has no published inputs to replay the document against")
        recorded = _dry_run(tile, inputs)
        instruction = (text + "\n\nThe declared figures (from the tile's published example) are: "
                       + paper_batch._declared(inputs) + ".")
        return _store(subject, tile_key, filename, instruction, inputs, recorded)

    raise ValueError("attach a JSON case, CSV/TSV, Excel .xlsx, Word .docx, PDF, TXT or an image")
