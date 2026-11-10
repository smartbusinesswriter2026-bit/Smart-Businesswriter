"""The business plan as a PDF, printed by the headless Chrome kaleido carries.

The document is the paper's own sections, not a slide deck: headings, paragraphs and
the tables the record holds.  Nothing is recomputed and nothing is added.  When no
Chrome is found the caller is told, rather than shipped an empty file.
"""

import html
import os
import subprocess
import tempfile

from . import business_plan_paper


def _document(record, narrative=None):
    title = "Business plan financials" + (": " + record.get("objective") if record.get("objective") else "")
    body = []
    for heading, lines in business_plan_paper.sections(record, narrative):
        body.append("<h2>" + html.escape(str(heading)) + "</h2>")
        for line in lines:
            body.append("<p>" + html.escape(str(line)) + "</p>")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>" + html.escape(title) + "</title>"
        "<style>"
        "body{font-family:Georgia,'Times New Roman',serif;color:#1a1e21;margin:22mm 18mm;font-size:11pt;line-height:1.5}"
        "h1{font-size:20pt;margin:0 0 4mm}"
        "h2{font-size:13pt;margin:7mm 0 2mm;page-break-after:avoid;color:#132a3a}"
        "p{margin:0 0 2mm;break-inside:avoid}"
        "@page{size:A4;margin:18mm}"
        "</style></head><body><h1>" + html.escape(title) + "</h1>" + "".join(body) + "</body></html>")


def pdf(record, narrative=None):
    """The plan as PDF bytes, or None when this machine has no Chrome."""
    from . import renderers

    chrome = renderers.chrome()
    if not chrome:
        return None
    directory = tempfile.mkdtemp(prefix="bp-plan-pdf-")
    page = os.path.join(directory, "plan.html")
    target = os.path.join(directory, "plan.pdf")
    profile = os.path.join(directory, "profile")
    try:
        with open(page, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(_document(record, narrative))
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--no-first-run", "--no-default-browser-check", "--disable-extensions",
             "--disable-background-networking", "--disable-sync", "--disable-dev-shm-usage",
             "--user-data-dir=" + profile, "--no-pdf-header-footer",
             "--print-to-pdf=" + target,
             "file:///" + page.replace("\\", "/")],
            timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(target):
            return None
        with open(target, "rb") as stream:
            return stream.read()
    except Exception:
        return None
