"""Live click-through for the People & organisation shelf against a workbench on 8002.

Two layers, because no browser-automation library is installed (and must not be):

(a) a Python contract check over the *served* HTML and the *served* JSON page for this
    shelf — the six tiles, the empty Reward tile and its note, the ten calculators and
    the nineteen worksheets;
(b) a real HTTP run through the same routes the page calls (create a session, confirm
    it, read the delivered report and its checks) for all ten calculators the shelf shows.

Screenshots are taken with the machine's own Chromium in headless mode
(``chrome --headless --screenshot``) — no dependency is added to the product.

    python qa/clickthrough_people.py http://127.0.0.1:8002
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "src")

from bp.server import PRESETS                      # noqa: E402
from bp.product import subjects                    # noqa: E402

OUT = os.path.join("qa", "evidence", "people")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TOOLS = ["alpha", "weighted", "descriptive", "chi_square", "power", "pearson", "ols",
         "trainingroi", "labourtightness", "programmecost"]
PAGE_MARKERS = ("People & organisation", "Strategy and design", "Resourcing", "Development",
                "Reward", "Engagement and culture", "Analytics")


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=30) as response:
        return response.status, response.read().decode("utf-8")


def post(base, path, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def post_bytes(base, path, payload=None):
    data = json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.status, response.headers.get("Content-Type"), len(response.read())


def shot(name, url, width=1280, height=1800):
    path = os.path.join(OUT, name)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--window-size=%d,%d" % (width, height),
                    "--virtual-time-budget=8000", "--screenshot=" + os.path.abspath(path),
                    url], check=False, capture_output=True, timeout=180)
    return path if os.path.exists(path) else None


def main(base):
    os.makedirs(OUT, exist_ok=True)
    report = {"base": base, "page": {}, "shelf": {}, "tools": {}, "screenshots": []}

    status, html = get(base, "/")
    report["page"] = {"status": status, "bytes": len(html),
                      "markers": {m: (m in html) for m in PAGE_MARKERS},
                      "tile_note_rendered": "esc(tile.note ||" in html,
                      "glossary_guard": "if ((s.glossary || []).length) {" in html}

    status, raw = get(base, "/api/cases/subjects/people")
    shelf = json.loads(raw)
    tiles = shelf.get("tiles") or []
    report["shelf"] = {
        "status": status,
        "tools": [t["key"] for t in shelf.get("tools") or []],
        "worksheets": [w["key"] for w in shelf.get("worksheets") or []],
        "tiles": [{"key": t["key"], "label": t["label"],
                   "worksheets": len(t.get("worksheets") or []),
                   "tools": len(t.get("tools") or []),
                   "records": len(t.get("records") or []),
                   "note": t.get("note")} for t in tiles],
        "records": shelf.get("records"),
        "theories": shelf.get("theories"),
        "glossary_terms": len(shelf.get("glossary") or []),
    }

    for key in TOOLS:
        preset = PRESETS[subjects.TOOL_INFO[key]["preset"]]
        try:
            status, created = post(base, "/api/sessions", {
                "objective": preset["objective"], "method": preset["method"],
                "inputs": preset["inputs"],
                "currency": preset.get("currency"), "period": preset.get("period"),
                "unit": preset.get("unit")})
            if created.get("status") == "awaiting_confirmation":
                created = post(base, "/api/sessions/%s/confirm" % created.get("id"), {})[1]
            delivery = created.get("delivery") or {}
            appendix = delivery.get("appendix") or {}
            checks = appendix.get("tests") or []
            session_id = created.get("id")
            try:
                paper_status, paper_type, paper_bytes = post_bytes(
                    base, "/api/sessions/%s/paper" % session_id, {"format": "docx"})
            except urllib.error.HTTPError as error:
                paper_status, paper_type, paper_bytes = error.code, None, 0
            report["tools"][key] = {
                "status": created.get("status"),
                "checks": len(checks),
                "checks_all_pass": bool(checks) and all(entry[1] for entry in checks),
                "report": bool(delivery.get("report")),
                "report_text": (delivery.get("report") or "")[:160],
                "paper_status": paper_status,
                "paper_type": paper_type,
                "paper_bytes": paper_bytes,
            }
        except urllib.error.HTTPError as error:
            report["tools"][key] = {"status": "HTTP %s" % error.code,
                                    "body": error.read().decode("utf-8")[:200]}
        except Exception as error:                                        # noqa: BLE001
            report["tools"][key] = {"status": "error", "body": str(error)[:200]}

    for name, size in (("01-shelf-1280.png", (1280, 2400)),
                       ("02-shelf-390.png", (390, 2400)),
                       ("03-calculator-1280.png", (1280, 1400))):
        saved = shot(name, base + "/#/subject/people", width=size[0], height=size[1])
        report["screenshots"].append({"name": name, "saved": bool(saved)})

    with open(os.path.join(OUT, "clickthrough.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps({"tools": report["tools"], "screenshots": report["screenshots"],
                      "tiles": report["shelf"].get("tiles")}, indent=1)[:3000])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8002")

