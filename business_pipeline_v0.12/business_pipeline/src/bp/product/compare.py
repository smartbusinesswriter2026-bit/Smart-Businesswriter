"""Side-by-side comparison of stored case versions (product layer, standard library only).

Option A of `docs/proposals/MULTI_PERIOD_VERSIONING.md` (owner-chosen, B-084):
each period/version is an ordinary frozen delivery stored as an immutable
case version; this module lays the stored bundles side by side.  It copies the
recorded values verbatim - it never reformats, re-rounds, interpolates or
computes a business number.

Declared comparability rules, enforced and reported:

* every compared version must have the **same method id** (otherwise the
  comparison is refused with a reason);
* rows are aligned by artifact metric; a metric missing from a version is
  shown as "not computed for this version", never filled in;
* differences in `spec_hash`, `method_version`, `outputs_hash` and unit are
  listed rather than hidden;
* the result carries a **disclosure** naming every version (case id, version,
  bundle/output hashes) it was built from.
"""

import html
import os
import tempfile
from pathlib import Path

from . import export as case_export
from . import versions

FORMAT = "bp-comparison/1"


class CompareError(Exception):
    """The versions cannot be compared honestly."""


def _version_documents(case_id, wanted=None):
    if wanted is None:
        numbers = [entry["version"] for entry in versions.list_versions(case_id) if not entry.get("corrupt")]
    else:
        numbers = list(wanted)
    if len(numbers) < 2:
        raise CompareError("a comparison needs at least two versions")
    documents = [versions.get(case_id, number) for number in numbers]
    return sorted(documents, key=lambda document: document["version"])


def _row_key(row):
    metric = row.get("metric")
    if isinstance(metric, str) and metric.strip():
        return metric
    return str(row.get("id"))


def compare(case_id, wanted=None):
    """Compare stored versions of one case. Returns a JSON-serialisable comparison."""
    documents = _version_documents(case_id, wanted)
    methods = {document["method"] for document in documents}
    if len(methods) != 1:
        raise CompareError("a comparison requires the same method id in every version; found: "
                           + ", ".join(sorted(methods)))
    issues = []
    columns = []
    for document in documents:
        columns.append({"version": document["version"], "created_at": document["created_at"],
                        "spec_hash": document["spec_hash"], "outputs_hash": document["outputs_hash"],
                        "bundle_hash": document["bundle_hash"], "method": document["method"],
                        "method_version": document["method_version"], "tier": document["tier"],
                        "title": document["title"]})
    base = columns[0]
    differences = []
    for column in columns[1:]:
        for field in ("spec_hash", "outputs_hash", "method_version"):
            if column[field] != base[field]:
                differences.append({"version": column["version"], "field": field,
                                    "from": base[field], "to": column[field]})
    ordered = {}
    for document in documents:
        for row in case_export.artifact_rows(document["bundle"]):
            key = _row_key(row)
            entry = ordered.setdefault(key, {"metric": key, "unit": row.get("unit"),
                                             "precision": row.get("precision"),
                                             "derivation": row.get("derivation"),
                                             "values": {}})
            entry["values"][str(document["version"])] = row.get("value")
            if row.get("unit") is not None and entry["unit"] is not None and row.get("unit") != entry["unit"]:
                entry["unit_conflict"] = True
    version_keys = [str(column["version"]) for column in columns]
    rows = []
    for key in sorted(ordered):
        entry = ordered[key]
        values = {version_key: entry["values"].get(version_key) for version_key in version_keys}
        missing = [int(version_key) for version_key in version_keys if values[version_key] is None]
        row = {"metric": entry["metric"], "unit": entry.get("unit"), "precision": entry.get("precision"),
               "derivation": entry.get("derivation"), "values": values, "not_computed": missing}
        if entry.get("unit_conflict"):
            row["unit_conflict"] = True
            issues.append("metric %s records different units across versions; the values are not comparable" % entry["metric"])
        rows.append(row)
    if not rows:
        issues.append("no artifacts were recorded in the compared versions")
    return {"format": FORMAT, "case_id": case_id,
            "columns": columns, "rows": rows, "differences": differences, "issues": issues,
            "comparability": {"method": columns[0]["method"], "same_method": True,
                              "rule": "same method id; artifact rows aligned by metric; stored values copied verbatim; "
                                      "a missing metric is reported as not computed, never filled"},
            "disclosure": [{"case_id": case_id, "version": column["version"],
                            "bundle_hash": column["bundle_hash"], "outputs_hash": column["outputs_hash"]}
                           for column in columns],
            "note": "Values are the ones recorded in each stored version; nothing in this comparison was recomputed."}


def _cell(value, precision=None):
    if value is None:
        return "not computed for this version"
    if isinstance(value, str):
        return html.escape(value, quote=False)
    return html.escape(str(value), quote=False)


def render_html(comparison, path):
    """Write a self-contained HTML comparison; values are the stored strings."""
    if not isinstance(comparison, dict) or comparison.get("format") != FORMAT:
        raise ValueError("not a comparison document")
    columns = comparison["columns"]
    header = ["Metric", "Unit"] + ["v%s" % column["version"] for column in columns] + ["Derivation"]
    head = "<tr>%s</tr>" % "".join("<th>%s</th>" % html.escape(str(cell), quote=False) for cell in header)
    body = []
    for row in comparison["rows"]:
        cells = [str(row["metric"]), row.get("unit") or "not recorded"]
        for column in columns:
            cells.append(_cell(row["values"].get(str(column["version"]))))
        cells.append(row.get("derivation") or "not recorded")
        body.append("<tr>%s</tr>" % "".join("<td>%s</td>" % html.escape(str(cell), quote=False) for cell in cells))
    difference_rows = "".join(
        "<tr><td>v%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            item["version"], html.escape(str(item["field"]), quote=False),
            html.escape(str(item["from"]), quote=False), html.escape(str(item["to"]), quote=False))
        for item in comparison["differences"]) or "<tr><td colspan=\"4\">no recorded differences</td></tr>"
    disclosure = "<br>".join(
        "v%s - case %s - bundle %s - outputs %s" % (
            item["version"], html.escape(item["case_id"], quote=False),
            html.escape(item["bundle_hash"], quote=False), html.escape(item["outputs_hash"], quote=False))
        for item in comparison["disclosure"])
    template = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Case comparison</title>
<style>
body { font-family: Georgia, 'Times New Roman', serif; margin: 2rem auto; max-width: 60rem; color: #1b1b1b; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; margin-top: .6rem; }
th, td { border: 1px solid #ddd8cc; padding: .3rem .5rem; text-align: left; vertical-align: top; }
th { background: #f0eee6; }
h2 { font-size: 1rem; margin-top: 2rem; }
footer { margin-top: 2rem; font-size: .78rem; color: #555; }
</style></head>
<body>
<h1>Comparison of @@CASE@@</h1>
<p>@@RULE@@</p>
<h2>Artifacts</h2>
<table>@@HEAD@@@@BODY@@</table>
<h2>Recorded differences</h2>
<table><tr><th>Version</th><th>Field</th><th>From</th><th>To</th></tr>@@DIFFS@@</table>
<h2>What was compared</h2>
<p>@@DISCLOSURE@@</p>
<footer>Values are the ones recorded in each stored version; nothing in this file was recomputed. Missing metrics are shown as "not computed for this version".</footer>
</body></html>
"""
    document = (template.replace("@@CASE@@", html.escape(comparison["case_id"], quote=False))
                        .replace("@@RULE@@", html.escape(comparison["comparability"]["rule"], quote=False))
                        .replace("@@HEAD@@", head).replace("@@BODY@@", "".join(body))
                        .replace("@@DIFFS@@", difference_rows)
                        .replace("@@DISCLOSURE@@", html.escape(disclosure, quote=False)))
    target = Path(path)
    if str(target.parent) not in ("", "."):
        target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(target.parent or "."), prefix=".tmp-compare-", suffix=".html")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(document)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return str(target)
