"""Self-contained HTML export of a stored case bundle (product layer).

`export_html(bundle, path)` writes one HTML file that contains:

* the delivered report text, verbatim (escaped for HTML, so it renders
  identically - no re-formatting, no re-rounding, no recomputation);
* the artifacts table, with every value exactly as stored.

Standard library only, no external resource: the file opens offline, with
nothing fetched and nothing embedded that was not already recorded.
"""

import html
import os
import tempfile
from pathlib import Path

_STYLE = """
body { font-family: Georgia, 'Times New Roman', serif; margin: 2rem auto; max-width: 52rem;
       color: #1b1b1b; background: #fdfdfb; line-height: 1.45; }
h1 { font-size: 1.4rem; border-bottom: 1px solid #d8d4c8; padding-bottom: .3rem; }
h2 { font-size: 1.05rem; margin-top: 2rem; letter-spacing: .02em; }
pre { white-space: pre-wrap; word-wrap: break-word; background: #f6f5f0; border: 1px solid #e2ded2;
      padding: .9rem; font-family: ui-monospace, Consolas, monospace; font-size: .85rem; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; }
th, td { border: 1px solid #e2ded2; padding: .35rem .5rem; text-align: left; vertical-align: top; }
th { background: #f0eee6; }
footer { margin-top: 2.5rem; font-size: .75rem; color: #6b6b6b; }
"""


def artifact_rows(bundle):
    """The stored artifacts of a bundle, with their stored values.

    Each row is a dict with `id`, `metric`, `unit`, `precision`, `value` and
    `derivation`.  Nothing is derived: the value is the one recorded in the
    re-perform bundle, and a field the bundle does not record stays None.
    """
    if not isinstance(bundle, dict):
        return []
    delivery = bundle.get("delivery")
    appendix = delivery.get("appendix") if isinstance(delivery, dict) else None
    artifacts = appendix.get("artifacts") if isinstance(appendix, dict) else None
    if not isinstance(artifacts, list):
        return []
    reperform = bundle.get("reperform")
    outputs = reperform.get("outputs") if isinstance(reperform, dict) else None
    if not isinstance(outputs, dict):
        outputs = {}
    rows = []
    for artifact in artifacts:
        if isinstance(artifact, dict):
            artifact_id = artifact.get("id")
            metric = artifact.get("metric")
            unit = artifact.get("unit")
            precision = artifact.get("precision")
            value = artifact.get("value")
            derivation = artifact.get("derivation")
        elif isinstance(artifact, (list, tuple)):
            artifact_id = artifact[0] if artifact else None
            labels = artifact[1] if len(artifact) > 1 else None
            metric = labels[0] if isinstance(labels, (list, tuple)) and labels else None
            unit = None
            precision = None
            value = None
            derivation = artifact[2] if len(artifact) > 2 else None
        else:
            continue
        if value is None and isinstance(artifact_id, str):
            value = outputs.get(artifact_id)
        rows.append({"id": artifact_id, "metric": metric, "unit": unit,
                     "precision": precision, "value": value, "derivation": derivation})
    return rows


def _cell(value):
    """A stored value in a table cell, exactly as stored."""
    if value is None:
        return "not recorded"
    if isinstance(value, str):
        return value if value.strip() else "not recorded"
    return html.escape(str(value), quote=False)


def _artifacts_html(bundle):
    rows = artifact_rows(bundle)
    if not rows:
        return "<p>not recorded</p>"
    head = "<tr><th>Artifact</th><th>Metric</th><th>Unit</th><th>Precision</th><th>Value</th><th>Derivation</th></tr>"
    body = []
    for row in rows:
        body.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                html.escape(_cell(row["id"]), quote=False),
                html.escape(_cell(row["metric"]), quote=False),
                html.escape(_cell(row["unit"]), quote=False),
                html.escape(_cell(row["precision"]), quote=False),
                html.escape(_cell(row["value"]), quote=False),
                html.escape(_cell(row["derivation"]), quote=False),
            )
        )
    return "<table>%s%s</table>" % (head, "".join(body))


def _report_text(bundle):
    delivery = bundle.get("delivery") if isinstance(bundle, dict) else None
    if isinstance(delivery, dict) and isinstance(delivery.get("report"), str):
        return delivery["report"]
    return "not recorded"


def _title(bundle):
    if not isinstance(bundle, dict):
        return "Case export"
    title = bundle.get("title")
    case_id = bundle.get("id")
    if title and case_id:
        return "%s (case %s)" % (title, case_id)
    return title or case_id or "Case export"


def export_html(bundle, path, charts=None, diagrams=None):
    """Write the self-contained HTML export of `bundle` to `path`.

    Returns the path written.  The stored report text and the stored artifact
    values are copied, never recomputed.  Optional `charts` and `diagrams` are
    lists of specs rendered by `bp.product.charts` / `bp.product.diagrams` into
    inline SVG from the same stored values (no network, no model, no new number).
    """
    if not isinstance(bundle, dict):
        raise ValueError("case bundle must be an object")
    chart_section = ""
    if charts:
        from . import charts as chart_renderer
        figures = "".join('<figure class="chart">%s</figure>' % chart_renderer.render_svg(bundle, spec)
                          for spec in charts)
        chart_section = '<section id="charts">\n<h2>Charts</h2>\n%s\n</section>\n' % figures
    diagram_section = ""
    if diagrams:
        from . import diagrams as diagram_renderer
        figures = "".join('<figure class="chart">%s</figure>' % diagram_renderer.render_svg(spec)
                          for spec in diagrams)
        diagram_section = '<section id="diagrams">\n<h2>Business graphics</h2>\n%s\n</section>\n' % figures
    target = Path(path)
    if str(target.parent) not in ("", "."):
        target.parent.mkdir(parents=True, exist_ok=True)

    report = _report_text(bundle)
    document = (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>%s</title>\n"
        "<style>%s</style>\n"
        "</head>\n"
        "<body>\n"
        "<main>\n"
        "<h1>%s</h1>\n"
        "<section id=\"report\">\n"
        "<h2>Delivered report</h2>\n"
        "<pre class=\"report\">%s</pre>\n"
        "</section>\n"
        "<section id=\"artifacts\">\n"
        "<h2>Artifacts</h2>\n"
        "%s\n"
        "</section>\n"
        "</main>\n"
        "<footer>Exported from a stored case bundle. The numbers above are the ones that were recorded; "
        "nothing in this file was recomputed.</footer>\n"
        "</body>\n"
        "</html>\n"
    ) % (
        html.escape(_title(bundle), quote=False),
        _STYLE,
        html.escape(_title(bundle), quote=False),
        html.escape(report, quote=False),
        _artifacts_html(bundle),
    )
    if chart_section or diagram_section:
        document = document.replace("</main>", chart_section + diagram_section + "</main>")

    handle, temp_name = tempfile.mkstemp(dir=str(target.parent or "."), prefix=".tmp-export-", suffix=".html")
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
