"""Renderer dispatch: the builtin SVG, and the optional engines behind it.

The builtin renderers (`charts`, `diagrams`) are standard library only and
always run.  Plotly draws charts when installed; Graphviz draws `tree` and
`process` diagrams when the `dot` binary is present; Mermaid is generated from
the same specs and drawn by `mmdc` when it is present.  When an engine is
absent the builtin renderer draws the figure instead, so a document never fails
because a package or a binary is missing.

Every engine reads `theme`, so a chart, a diagram and a deck carry one visual
language rather than three.

A raster (PNG) is only produced when a rasterizer is installed.  Without one,
`png()` returns None and the caller decides how to degrade - it never silently
ships a picture that cannot be checked.

Install for the full path (never required at runtime):

    pip install plotly kaleido        # charts -> PNG, no browser needed at call time
    pip install cairosvg              # builtin SVG (diagrams, gantt) -> PNG
    dot / mmdc on PATH                # Graphviz / Mermaid diagrams
"""

import os
import re
import shutil
import subprocess
import tempfile
import zlib

from . import charts, diagrams, theme
from . import export as case_export

#: The frame a chart is drawn into, in CSS pixels before `scale`.
CHART_WIDTH, CHART_HEIGHT = 1440, 600


def _binary(name):
    return shutil.which(name)


def available():
    """What this machine can actually draw with."""
    try:
        import plotly  # noqa: F401
        plotly_ok = True
    except Exception:
        plotly_ok = False
    try:
        import cairosvg  # noqa: F401
        cairo_ok = True
    except Exception:
        cairo_ok = False
    return {
        "builtin": True,
        "plotly": plotly_ok,
        "cairosvg": cairo_ok,
        "graphviz": bool(_binary("dot")),
        "mermaid": bool(_binary("mmdc")),
        "raster": raster(),
    }


def raster():
    """The name of an installed SVG rasterizer, or None."""
    try:
        import cairosvg  # noqa: F401
        return "cairosvg"
    except Exception:
        pass
    for name in ("rsvg-convert", "inkscape", "magick"):
        if _binary(name):
            return name
    if _chrome():
        return "chrome"
    return None


def chrome():
    """The Chrome binary kaleido carries, or None.  Public for the deck's PDF print."""
    return _chrome()


def _chrome():
    """The Chrome binary kaleido already carries, or None."""
    try:
        import kaleido
    except Exception:
        return None
    try:
        path = kaleido.get_chrome_sync()
    except Exception:
        return None
    return path if path and os.path.exists(path) else None


# --- the builtin SVG -------------------------------------------------------

def svg(figure, bundle=None):
    """Draw one figure as SVG, through the best engine this machine has."""
    spec = figure.get("spec") or {}
    if figure.get("kind") == "diagram":
        if _binary("dot"):
            made = _graphviz(spec, "svg")
            if made:
                return made.decode("utf-8", "replace")
        return diagrams.render_svg(spec, bundle)
    return charts.render_svg(bundle, spec)


def png(figure, bundle=None, scale=3):
    """A PNG of the figure, or None when no rasterizer is installed."""
    spec = figure.get("spec") or {}
    if figure.get("kind") == "chart":
        made = _plotly_png(spec, bundle, scale)
        if made:
            return made
    else:
        if _binary("dot"):
            made = _graphviz(spec, "png")
            if made:
                return made
        made = _mermaid_png(spec, scale)
        if made:
            return made
    return _svg_to_png(svg(figure, bundle), scale)


# --- Plotly ----------------------------------------------------------------

def _stored(rows, key):
    for row in rows:
        if row.get("metric") == key or row.get("id") == key:
            return row.get("value")
    return None


def _series(spec, rows):
    labels, values, stored = [], [], []
    for entry in spec.get("series") or []:
        key = entry.get("artifact")
        value = _stored(rows, key)
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        labels.append(entry.get("label"))
        values.append(number)
        stored.append(str(value))
    return labels, values, stored


def _plotly_multi_line(go, spec, rows, groups, scale):
    """One line per group, so a burndown or a control chart keeps its series apart."""
    palette = theme.TOKENS["palette"]
    traces = []
    for index, group in enumerate(groups):
        labels, values, stored = [], [], []
        for entry in spec.get("series") or []:
            if str(entry.get("group") or "").strip() != group:
                continue
            value = _stored(rows, entry.get("artifact"))
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                return None
            labels.append(entry.get("label"))
            stored.append(str(value))
        traces.append(go.Scatter(x=labels, y=values, mode="lines+markers",
                                 name=group, text=stored,
                                 line=dict(color=palette["series"][index % len(palette["series"])],
                                           width=theme.TOKENS["stroke"]["series"]),
                                 marker=dict(size=8)))
    figure = go.Figure(data=traces)
    template = theme.plotly_template()
    if template is not None:
        figure.update_layout(template=template)
    figure.update_layout(title=dict(text=spec.get("title")), showlegend=True,
                         legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))
    try:
        return figure.to_image(format="png", width=CHART_WIDTH, height=CHART_HEIGHT, scale=scale)
    except Exception:
        return None


def _plotly_pareto(go, spec, rows, scale):
    """Bars and the stored running total on a second axis, never one derived from the other."""
    try:
        from plotly.subplots import make_subplots
    except Exception:
        return None
    labels, values, stored, running, running_stored = [], [], [], [], []
    for entry in spec.get("series") or []:
        value = _stored(rows, entry.get("artifact"))
        total = _stored(rows, entry.get("cumulative"))
        try:
            values.append(float(value))
            running.append(float(total))
        except (TypeError, ValueError):
            return None
        labels.append(entry.get("label"))
        stored.append(str(value))
        running_stored.append(str(total))
    if len(labels) < 2:
        return None
    palette = theme.TOKENS["palette"]
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(go.Bar(x=labels, y=values, text=stored, textposition="outside",
                            name=str(spec.get("y_label") or "Recorded value"),
                            marker_color=palette["accent"],
                            textfont=dict(color=palette["ink"])), secondary_y=False)
    figure.add_trace(go.Scatter(x=labels, y=running, mode="lines+markers+text",
                                text=running_stored, textposition="top center",
                                name=str(spec.get("y2_label") or "Running total"),
                                line=dict(color=palette["series"][1],
                                          width=theme.TOKENS["stroke"]["series"]),
                                marker=dict(size=8)), secondary_y=True)
    template = theme.plotly_template()
    if template is not None:
        figure.update_layout(template=template)
    figure.update_layout(title=dict(text=spec.get("title")), showlegend=True,
                         legend=dict(orientation="h", y=1.02, x=1, xanchor="right",
                                     yanchor="bottom"))
    try:
        return figure.to_image(format="png", width=CHART_WIDTH, height=CHART_HEIGHT, scale=scale)
    except Exception:
        return None


def _plotly_png(spec, bundle, scale):
    """A PNG from Plotly, or None when Plotly (or its engine) is not installed."""
    try:
        import plotly.graph_objects as go
    except Exception:
        return None
    kind = spec.get("kind")
    if kind in ("gantt", "table", "sparkline", "network"):
        return None  # the builtin renderer owns these shapes
    rows = case_export.artifact_rows(bundle)
    charts.verify_labels(spec, rows)
    if kind == "pareto":
        return _plotly_pareto(go, spec, rows, scale)
    groups = []
    for entry in spec.get("series") or []:
        name = str(entry.get("group") or "").strip()
        if name and name not in groups:
            groups.append(name)
    if kind == "line" and len(groups) > 1:
        return _plotly_multi_line(go, spec, rows, groups, scale)
    resolved = _series(spec, rows)
    if not resolved:
        return None
    labels, values, stored = resolved
    palette = theme.TOKENS["palette"]
    kind_type = theme.TOKENS["type"]
    # A dense chart prints no value on every point: the labels overlap and the
    # picture stops being readable.  The values are still in the document.
    dense = len(labels) > 12
    if kind == "bar":
        trace = go.Bar(x=labels, y=values,
                       text=None if dense else stored,
                       textposition=None if dense else "outside",
                       marker_color=palette["accent"], textfont=dict(color=palette["ink"]))
    elif kind == "stacked_bar":
        trace = go.Bar(x=labels, y=values,
                       text=None if dense else stored,
                       textposition=None if dense else "inside",
                       marker_color=palette["accent"], textfont=dict(color=palette["ink"]))
    elif kind == "waterfall":
        trace = go.Waterfall(x=labels, y=values,
                             text=None if dense else stored,
                             textposition=None if dense else "outside")
    elif kind == "pie":
        trace = go.Pie(labels=labels, values=values, text=stored, textinfo="label+text")
    else:
        trace = go.Scatter(x=labels, y=values,
                           mode="lines+markers" if dense else "lines+markers+text",
                           text=None if dense else stored,
                           textposition=None if dense else "top center",
                           line=dict(color=palette["accent"], width=theme.TOKENS["stroke"]["series"]),
                           marker=dict(size=9, color=palette["accent"]))
    figure = go.Figure(data=[trace])
    template = theme.plotly_template()
    if template is not None:
        figure.update_layout(template=template)
    figure.update_layout(title=dict(text=spec.get("title")),
                         font=dict(family=kind_type["family"], color=palette["ink"]))
    try:
        return figure.to_image(format="png", width=CHART_WIDTH, height=CHART_HEIGHT, scale=scale)
    except Exception:
        return None


# --- Graphviz --------------------------------------------------------------

def _dot_escape(text):
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def dot_source(spec):
    """A DOT program for a `tree` or `process` diagram, or None for another kind.

    The labels are the validated diagram labels; the node ids (`n0`, `c0`) are
    layout handles, never text a reader sees, so no number reaches the drawing.
    """
    if not isinstance(spec, dict):
        return None
    kind = spec.get("kind")
    attrs = theme.graphviz_attrs()
    graph = attrs["graph"]
    node = attrs["node"]
    edge = attrs["edge"]
    lines = ["digraph %s {" % kind,
             '  graph [rankdir=TB, bgcolor="%s", fontname="%s", pad="%s", nodesep="%s", ranksep="%s"];'
             % (graph["bgcolor"], graph["fontname"], graph["pad"], graph["nodesep"], graph["ranksep"]),
             '  node [shape=%s, style="%s", fillcolor="%s", fontname="%s", fontsize="%s", '
             'color="%s", fontcolor="%s"];'
             % (node["shape"], node["style"], node["fillcolor"], node["fontname"],
                node["fontsize"], node["color"], node["fontcolor"]),
             '  edge [color="%s", arrowsize="%s"];' % (edge["color"], edge["arrowsize"])]
    if kind == "process":
        items = [entry for entry in spec.get("items") or [] if isinstance(entry, dict)]
        if len(items) < 2:
            return None
        for index, entry in enumerate(items):
            lines.append('  n%d [label="%s"];' % (index, _dot_escape(entry.get("label"))))
        for index in range(len(items) - 1):
            lines.append("  n%d -> n%d;" % (index, index + 1))
    elif kind == "tree":
        root = spec.get("root")
        children = [entry for entry in spec.get("children") or [] if isinstance(entry, dict)]
        if not root or not children:
            return None
        lines.append('  root [label="%s"];' % _dot_escape(root))
        for index, entry in enumerate(children):
            lines.append('  c%d [label="%s"];' % (index, _dot_escape(entry.get("label"))))
            lines.append("  root -> c%d;" % index)
    else:
        return None
    lines.append("}")
    return "\n".join(lines) + "\n"


def _graphviz(spec, format):
    source = dot_source(spec)
    if not source:
        return None
    return _run(["dot", "-T" + format], source.encode("utf-8"))


# --- Mermaid ---------------------------------------------------------------

def _mermaid_escape(text):
    return str(text).replace('"', "'").replace("\n", " ")


def mermaid_source(spec):
    """Mermaid source for a `process` or `tree` diagram, or None for another kind."""
    if not isinstance(spec, dict):
        return None
    kind = spec.get("kind")
    if kind == "process":
        items = [entry for entry in spec.get("items") or [] if isinstance(entry, dict)]
        if len(items) < 2:
            return None
        lines = ["flowchart TD"]
        for index, entry in enumerate(items):
            lines.append('  n%d["%s"]' % (index, _mermaid_escape(entry.get("label"))))
        for index in range(len(items) - 1):
            lines.append("  n%d --> n%d" % (index, index + 1))
        return "\n".join(lines) + "\n"
    if kind == "tree":
        root = spec.get("root")
        children = [entry for entry in spec.get("children") or [] if isinstance(entry, dict)]
        if not root or not children:
            return None
        lines = ["flowchart TD", '  r["%s"]' % _mermaid_escape(root)]
        for index, entry in enumerate(children):
            lines.append('  c%d["%s"]' % (index, _mermaid_escape(entry.get("label"))))
            lines.append("  r --> c%d" % index)
        return "\n".join(lines) + "\n"
    return None


def _mermaid_png(spec, scale):
    if not _binary("mmdc"):
        return None
    source = mermaid_source(spec)
    if not source:
        return None
    directory = tempfile.mkdtemp(prefix="bp-mermaid-")
    source_path = os.path.join(directory, "figure.mmd")
    target = os.path.join(directory, "figure.png")
    try:
        with open(source_path, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(source)
        _run(["mmdc", "-i", source_path, "-o", target, "-s", str(scale)],
             None, timeout=120)
        if os.path.exists(target):
            with open(target, "rb") as stream:
                return stream.read()
        return None
    except Exception:
        return None
    finally:
        shutil.rmtree(directory, ignore_errors=True)


# --- SVG -> PNG ------------------------------------------------------------

def _run(command, data, timeout=60):
    """Run a local tool and return its stdout, or None.  Never touches the network."""
    try:
        result = subprocess.run(command, input=data, timeout=timeout,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return result.stdout or None
    except Exception:
        return None


def _svg_to_png(markup, scale=3):
    if not markup:
        return None
    try:
        import cairosvg
    except Exception:
        cairosvg = None
    if cairosvg is not None:
        try:
            return cairosvg.svg2png(bytestring=markup.encode("utf-8"), scale=scale)
        except Exception:
            return None
    name = raster()
    if name in (None, "cairosvg"):
        return None
    if name == "chrome":
        return _chrome_svg_to_png(markup, scale)
    return _binary_raster(name, markup, scale)


def _svg_size(markup, fallback=(720, 300)):
    """(width, height) from the SVG's viewBox, or the fallback."""
    match = re.search(r'viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"', markup or "")
    if not match:
        return fallback
    return int(float(match.group(1))), int(float(match.group(2)))


#: The headless window is taller than the drawing it takes, so the viewport can
#: hold the whole figure.  The surplus rows are cut off the screenshot after it.
WINDOW_HEADROOM = 200


def _chrome_svg_to_png(markup, scale=3):
    """Rasterize the builtin SVG with the headless Chrome kaleido already carries.

    The headless window reserves room for its own frame, so its viewport is
    shorter than the window: the drawing is asked for in a taller window and the
    extra rows are cut off afterwards.  Without that, the bottom of every figure
    is lost - a Gantt loses its last activity.
    """
    chrome = _chrome()
    if not chrome:
        return None
    width, height = _svg_size(markup)
    window_height = height + WINDOW_HEADROOM
    directory = tempfile.mkdtemp(prefix="bp-chrome-")
    page = os.path.join(directory, "figure.html")
    target = os.path.join(directory, "figure.png")
    profile = os.path.join(directory, "profile")
    try:
        with open(page, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("<!doctype html><html><head><meta charset='utf-8'>"
                         "<style>html,body{margin:0;padding:0;background:#fdfdfb}"
                         "svg{display:block}</style></head><body>" + markup + "</body></html>")
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--no-first-run", "--no-default-browser-check", "--disable-extensions",
             "--disable-background-networking", "--disable-sync", "--disable-dev-shm-usage",
             "--user-data-dir=" + profile,
             "--force-device-scale-factor=%d" % scale,
             "--window-size=%d,%d" % (width, window_height),
             "--screenshot=" + target,
             "file:///" + page.replace("\\", "/")],
            timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(target):
            return None
        with open(target, "rb") as stream:
            data = stream.read()
        cropped = _crop_png_rows(data, int(round(height * scale)))
        return cropped if cropped else data
    except Exception:
        return None
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _chunk(chunk_type, payload):
    """One PNG chunk: length, type, data, CRC."""
    return (len(payload).to_bytes(4, "big") + chunk_type + payload
            + zlib.crc32(chunk_type + payload).to_bytes(4, "big"))


def _unfilter(kind, line, previous, channels):
    """Undo one PNG scanline filter, in place (the PNG specification's five)."""
    if kind == 0:
        return
    for index in range(len(line)):
        left = line[index - channels] if index >= channels else 0
        up = previous[index]
        corner = previous[index - channels] if index >= channels else 0
        if kind == 1:
            line[index] = (line[index] + left) & 0xFF
        elif kind == 2:
            line[index] = (line[index] + up) & 0xFF
        elif kind == 3:
            line[index] = (line[index] + (left + up) // 2) & 0xFF
        elif kind == 4:
            estimate = left + up - corner
            da, db, dc = abs(estimate - left), abs(estimate - up), abs(estimate - corner)
            if da <= db and da <= dc:
                predictor = left
            elif db <= dc:
                predictor = up
            else:
                predictor = corner
            line[index] = (line[index] + predictor) & 0xFF


def _crop_png_rows(data, rows):
    """The first `rows` scanlines of a PNG, as a new PNG.

    The standard library only: the bytes are decoded, the wanted rows are kept
    and the picture is written again.  A picture this code cannot read is
    returned unchanged, so a crop never breaks a figure.
    """
    if not data or rows <= 0:
        return None
    try:
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        offset = 8
        header = None
        idat = []
        palette = []
        while offset + 8 <= len(data):
            length = int.from_bytes(data[offset:offset + 4], "big")
            chunk_type = data[offset + 4:offset + 8]
            payload = data[offset + 8:offset + 8 + length]
            offset += 12 + length
            if chunk_type == b"IHDR":
                header = payload
            elif chunk_type == b"IDAT":
                idat.append(payload)
            elif chunk_type == b"IEND":
                break
            elif chunk_type in (b"PLTE", b"tRNS"):
                palette.append((chunk_type, payload))
        if header is None or not idat:
            return None
        width = int.from_bytes(header[0:4], "big")
        height = int.from_bytes(header[4:8], "big")
        depth, colour, interlace = header[8], header[9], header[12]
        if depth != 8 or interlace != 0 or colour not in (0, 2, 6):
            return None
        channels = {0: 1, 2: 3, 6: 4}[colour]
        stride = width * channels
        raw = zlib.decompress(b"".join(idat))
        kept = []
        previous = bytearray(stride)
        position = 0
        for _ in range(height):
            if position + 1 + stride > len(raw):
                return None
            kind = raw[position]
            position += 1
            line = bytearray(raw[position:position + stride])
            position += stride
            _unfilter(kind, line, previous, channels)
            kept.append(bytes(line))
            previous = line
            if len(kept) >= rows:
                break
        if not kept:
            return None
        body = bytearray()
        for line in kept:
            body.append(0)
            body.extend(line)
        out = bytearray(b"\x89PNG\r\n\x1a\n")
        out.extend(_chunk(b"IHDR", header[:4] + len(kept).to_bytes(4, "big") + header[8:]))
        for chunk_type, payload in palette:
            out.extend(_chunk(chunk_type, payload))
        out.extend(_chunk(b"IDAT", zlib.compress(bytes(body), 9)))
        out.extend(_chunk(b"IEND", b""))
        return bytes(out)
    except Exception:
        return None


def _binary_raster(name, markup, scale):
    """Rasterize through an installed command-line tool, never a network call."""
    directory = tempfile.mkdtemp(prefix="bp-raster-")
    source = os.path.join(directory, "figure.svg")
    target = os.path.join(directory, "figure.png")
    try:
        with open(source, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(markup)
        if name == "rsvg-convert":
            command = [name, "-z", str(scale), "-o", target, source]
        elif name == "inkscape":
            command = [name, source, "--export-type=png", "--export-filename=" + target]
        else:  # magick
            command = [name, "-density", str(96 * scale), source, target]
        subprocess.run(command, check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(target, "rb") as stream:
            return stream.read()
    except Exception:
        return None
    finally:
        shutil.rmtree(directory, ignore_errors=True)
