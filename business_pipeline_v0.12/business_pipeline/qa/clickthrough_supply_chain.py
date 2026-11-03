"""Live click-through for the Supply chain & logistics shelf against a workbench on 8001.

Two layers, because no browser automation library is installed (and must not be):

(a) a Python contract check over the *served* HTML and the *served* JSON page for this
    shelf - including the two notes this session added (the hand-filled worksheet and
    the record whose calculator is on another shelf);
(b) a real HTTP run through the same routes the page calls (create a session, confirm
    it, read the delivered report) for all eight calculators the shelf shows.

Screenshots are taken with the machine's own Chromium in headless mode
(``chrome --headless --screenshot``) - no dependency is added to the product.

    python qa/clickthrough_supply_chain.py http://127.0.0.1:8001
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "src")

from bp.server import PRESETS  # noqa: E402

OUT = os.path.join("qa", "evidence", "supply-chain")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TOOLS = ["breakeven", "multibreakeven", "unitecon", "forecast",
         "inventory", "queue", "capacity", "missing"]
PAGE_MARKERS = ("Supply chain", "Inventory and network", "Cost and mix", "Demand and planning")


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


def shot(name, url, width=1280, height=1600):
    path = os.path.join(OUT, name)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--window-size=%d,%d" % (width, height),
                    "--virtual-time-budget=6000", "--screenshot=" + os.path.abspath(path),
                    url], check=False, capture_output=True, timeout=120)
    return path if os.path.exists(path) else None


def post_bytes(base, path, payload=None):
    data = json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.status, response.headers.get("Content-Type"), len(response.read())


def get_bytes(base, path):
    with urllib.request.urlopen(base + path, timeout=120) as response:
        return response.status, response.headers.get("Content-Type"), len(response.read())


def main(base):
    os.makedirs(OUT, exist_ok=True)
    report = {"base": base, "page": {}, "shelf": {}, "tools": {}, "screenshots": []}

    status, html = get(base, "/")
    report["page"] = {"status": status, "bytes": len(html),
                      "markers": {m: (m in html) for m in PAGE_MARKERS},
                      "hand_filled_affordance": "Open worksheet - filled by hand" in html}

    status, raw = get(base, "/api/cases/subjects/supply-chain")
    shelf = json.loads(raw)
    records = {row["id"]: row for row in shelf.get("records") or []}
    sheets = {row["key"]: row for row in shelf.get("worksheets") or []}
    report["shelf"] = {
        "status": status,
        "tools": [t["key"] for t in shelf.get("tools") or []],
        "worksheets": sorted(sheets),
        "records": sorted(records),
        "ops03_draft_note": (sheets.get("OPS-03") or {}).get("draft_note"),
        "records_with_calculator_elsewhere": [rid for rid, row in records.items()
                                              if row.get("tool_here") is False],
        "qnt05_note": (records.get("QNT-OPS-05") or {}).get("status_note"),
    }

    for key in TOOLS:
        preset = PRESETS[key]
        try:
            status, created = post(base, "/api/sessions", {
                "objective": preset["objective"], "method": preset["method"],
                "inputs": preset["inputs"],
                "currency": preset.get("currency"), "period": preset.get("period")})
            if created.get("status") == "awaiting_confirmation":
                session_id = created.get("id")
                status, created = post(base, "/api/sessions/%s/confirm" % session_id, {})
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
                "paper_status": paper_status,
                "paper_type": paper_type,
                "paper_bytes": paper_bytes,
            }
        except urllib.error.HTTPError as error:
            report["tools"][key] = {"status": "HTTP %s" % error.code,
                                    "body": error.read().decode("utf-8")[:200]}
        except Exception as error:                                        # noqa: BLE001
            report["tools"][key] = {"status": "error", "body": str(error)[:200]}

    for name, size in (("01-shelf-1280.png", (1280, 1700)),
                       ("02-shelf-390.png", (390, 1700)),
                       ("03-calculator-1280.png", (1280, 1200))):
        saved = shot(name, base + "/#/subject/supply-chain", width=size[0], height=size[1])
        report["screenshots"].append({"name": name, "saved": bool(saved)})

    with open(os.path.join(OUT, "clickthrough.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps(report, indent=1)[:4000])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001")
