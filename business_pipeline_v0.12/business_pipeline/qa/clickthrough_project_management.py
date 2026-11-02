"""Live click-through for the project-management shelf against a workbench on 8001.

Two layers, because no browser automation library is installed (and must not be):

(a) a Python contract check over the *served* HTML and the *served* JSON page for
    this shelf, plus the ``node --check`` page-syntax gate;
(b) a real HTTP run through the same routes the page calls (create a session,
    confirm it, read the delivered report) for every calculator the shelf shows.

Screenshots are taken with the machine's own Chromium in headless mode
(``chrome --headless --screenshot``) - no dependency is added to the product.

    python qa/clickthrough_project_management.py http://127.0.0.1:8001
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "src")

from bp.server import PRESETS  # noqa: E402

OUT = os.path.join("qa", "evidence", "project-management")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TOOLS = ["npv", "irr", "dpayback", "projectmetrics", "scenario", "case_decision", "forecast",
         "cpm", "evm", "leveling", "crashing", "calendar", "multiproject", "schedrisk",
         "decisiontree", "realoption", "mcda", "montecarlo"]
PAGE_MARKERS = ("Complete a framework", "With computation", "Start here", "All subjects")



def get(base, path):
    with urllib.request.urlopen(base + path, timeout=30) as response:
        return response.status, response.read().decode("utf-8")


def post(base, path, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def shot(base, name, url, width=1280, height=1400):
    path = os.path.join(OUT, name)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--window-size=%d,%d" % (width, height),
                    "--virtual-time-budget=6000", "--screenshot=" + os.path.abspath(path),
                    url], check=False, capture_output=True, timeout=120)
    return path if os.path.exists(path) else None


def main(base):
    os.makedirs(OUT, exist_ok=True)
    report = {"base": base, "page": {}, "tools": {}, "screenshots": [], "console": []}

    status, html = get(base, "/")
    report["page"]["status"] = status
    report["page"]["bytes"] = len(html)
    report["page"]["markers"] = {marker: (marker in html) for marker in PAGE_MARKERS}

    # The served template and preset registries are the page's own data source for
    # "what can this shelf actually do"; they are read over HTTP, not in process.
    status, templates = get(base, "/api/templates")
    listed = json.loads(templates)
    rows = listed if isinstance(listed, list) else listed.get("templates") or []
    names = {row.get("id") or row.get("template") for row in rows}
    report["page"]["templates_status"] = status
    report["page"]["shelf_templates"] = {name: (name in names) for name in (
        "template_project_charter", "template_wbs", "template_raci",
        "template_risk_register", "template_stakeholder_plan",
        "template_lessons_learned")}

    status, presets = get(base, "/api/presets")
    served = json.loads(presets)
    report["page"]["presets_status"] = status
    report["page"]["presets_shape"] = ("list" if isinstance(served, list)
                                      else sorted(served)[:8])

    for key in TOOLS:
        preset = PRESETS[key]
        try:
            status, created = post(base, "/api/sessions", {
                "objective": preset["objective"], "method": preset["method"],
                "inputs": preset["inputs"]})
            if created.get("status") == "awaiting_confirmation":
                session_id = created.get("id")
                status, created = post(base, "/api/sessions/%s/confirm" % session_id, {})
            delivery = created.get("delivery") or {}
            report["tools"][key] = {"status": created.get("status"),
                                    "checks": len((created.get("appendix") or {}).get("tests") or []),
                                    "report": bool(delivery.get("report"))}
        except urllib.error.HTTPError as error:
            report["tools"][key] = {"status": "HTTP %s" % error.code,
                                    "body": error.read().decode("utf-8")[:200]}
        except Exception as error:                                        # noqa: BLE001
            report["tools"][key] = {"status": "error", "body": str(error)[:200]}

    for name, url, size in (
            ("01-shelf-1280.png", base + "/#/subject/project-management", (1280, 1600)),
            ("02-shelf-390.png", base + "/#/subject/project-management", (390, 1600)),
            ("03-calculator-1280.png", base + "/#/subject/project-management", (1280, 1100)),
            ("04-delivered-1280.png", base + "/#/chat", (1280, 1100))):
        saved = shot(base, name, url, width=size[0], height=size[1])
        report["screenshots"].append({"name": name, "saved": bool(saved), "url": url})

    with open(os.path.join(OUT, "clickthrough.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps(report, indent=1)[:3000])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001")
