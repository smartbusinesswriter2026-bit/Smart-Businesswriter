"""One visual language: the tokens every renderer reads.

Three engines draw in this product - the builtin SVG, Plotly for charts, and
Graphviz or Mermaid for diagrams - and python-pptx will read the same file for
decks.  Left alone they look like three products.  This module is the single
place a colour, a type size or a stroke width is written, and every engine reads
it from here.

The tokens are data, so a designer can change the look without touching a
renderer, and a new engine joins the same language by reading the same file.

The builtin SVG (`charts`, `diagrams`) reads `SERIES` from here; the engines
read the same tokens, so the builtin drawing and the engines can never drift
apart.
"""

#: The categorical palette, in order.  This is the one definition.
SERIES = ("#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
          "#59a14f", "#edc948", "#b07aa1", "#9c755f")

#: The faces the builtin SVG and the engines share.
SERIF = "Georgia, 'Times New Roman', serif"
MONO = "Consolas, monospace"

TOKENS = {
    "palette": {
        "paper": "#fdfdfb",
        "ink": "#1b1b1b",
        "muted": "#555550",
        "axis": "#8a8a85",
        "grid": "#e6e6e1",
        "accent": SERIES[0],
        "positive": "#59a14f",
        "negative": "#e15759",
        "neutral": "#8a8a85",
        "series": SERIES,
    },
    "type": {
        "family": SERIF,
        "mono": MONO,
        "title": 26,
        "label": 15,
        "tick": 13,
        "note": 11,
    },
    "space": {"margin": 40, "gap": 8},
    "stroke": {"axis": 1, "grid": 1, "series": 3},
}


def plotly_template():
    """A Plotly template built from the tokens, or None when Plotly is absent."""
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except Exception:
        return None
    palette, kind, space, stroke = (TOKENS["palette"], TOKENS["type"],
                                    TOKENS["space"], TOKENS["stroke"])
    template = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=palette["paper"], plot_bgcolor=palette["paper"],
            font=dict(family=kind["family"], size=kind["label"], color=palette["ink"]),
            title=dict(x=0.02, xanchor="left",
                       font=dict(family=kind["family"], size=kind["title"], color=palette["ink"])),
            margin=dict(l=70, r=space["margin"], t=90, b=70),
            colorway=list(palette["series"]),
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, linecolor=palette["axis"],
                       tickfont=dict(size=kind["tick"], color=palette["muted"])),
            yaxis=dict(showgrid=True, gridcolor=palette["grid"], gridwidth=stroke["grid"],
                       zeroline=False, linecolor=palette["axis"],
                       tickfont=dict(size=kind["tick"], color=palette["muted"])),
        )
    )
    pio.templates["bp"] = template
    pio.templates.default = "bp"
    return template


def mermaid_theme():
    """Mermaid `themeVariables`, so a diagram matches a chart."""
    palette, kind = TOKENS["palette"], TOKENS["type"]
    return {
        "background": palette["paper"],
        "primaryColor": palette["accent"],
        "primaryTextColor": palette["ink"],
        "primaryBorderColor": palette["axis"],
        "lineColor": palette["axis"],
        "secondaryColor": palette["grid"],
        "tertiaryColor": palette["paper"],
        "fontFamily": kind["family"],
        "fontSize": "%dpx" % kind["label"],
    }


def graphviz_attrs():
    """Graphviz graph/node/edge attributes, so a diagram matches a chart."""
    palette, kind = TOKENS["palette"], TOKENS["type"]
    return {
        "graph": {"bgcolor": palette["paper"], "fontname": "Georgia",
                  "pad": "0.3", "nodesep": "0.4", "ranksep": "0.5"},
        "node": {"shape": "box", "style": "rounded,filled", "fillcolor": palette["accent"],
                 "fontname": "Georgia", "fontsize": str(kind["tick"]),
                 "color": palette["axis"], "fontcolor": palette["ink"]},
        "edge": {"color": palette["axis"], "arrowsize": "0.7",
                 "fontname": "Georgia", "fontsize": str(kind["note"])},
    }


def pptx_colors():
    """The palette python-pptx themes will read, as hex without the hash."""
    palette = TOKENS["palette"]
    return {"paper": palette["paper"].lstrip("#"), "ink": palette["ink"].lstrip("#"),
            "accent": palette["accent"].lstrip("#"),
            "series": [colour.lstrip("#") for colour in palette["series"]]}
