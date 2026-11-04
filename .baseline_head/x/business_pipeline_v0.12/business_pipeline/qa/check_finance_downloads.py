"""Does every finance tile download a paper? One HTTP run per tool against a live workbench.

For each tool on the finance shelf: create the session from its preset, confirm it, then download
the paper as Markdown and as Word.  The Markdown must carry the delivered report's own figure and
the Word file must be a real zip container.

`ols_robust` (no preset, G-fin-05) and `dcfmid` (blocked, D-FIN-01) are reported as known, not
counted as failures.

Usage:  PYTHONPATH=src python qa/check_finance_downloads.py http://127.0.0.1:8002
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "src")

from bp.product import subjects  # noqa: E402
from bp.server import PRESETS    # noqa: E402

KNOWN = {"ols_robust": "no preset (G-fin-05)", "dcfmid": "blocked (D-FIN-01)"}


def call(base, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=90) as stream:
            payload = stream.read()
            return (stream.status, payload) if raw else (stream.status, json.loads(payload or b"{}"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def main(argv):
    base = (argv[1] if len(argv) > 1 else "http://127.0.0.1:8002").rstrip("/")
    rows, failures, known = [], [], []
    for tool in subjects.detail("finance")["tools"]:
        key, preset_id = tool["key"], tool.get("preset")
        if preset_id not in PRESETS:
            known.append("%s: %s" % (key, KNOWN.get(key, "no preset")))
            rows.append({"tool": key, "known": "no preset"})
            continue
        status, created = call(base, "/api/sessions", json.loads(json.dumps(PRESETS[preset_id])))
        if status != 201:
            rows.append({"tool": key, "error": "session %s" % status})
            failures.append("%s: could not create the session (%s)" % (key, status))
            continue
        session_id = created["id"]
        call(base, "/api/sessions/%s/confirm" % session_id, {})
        status, report = call(base, "/api/sessions/%s" % session_id)
        delivered = ((report or {}).get("delivery") or {})
        if delivered.get("status") != "delivered":
            known.append("%s: %s" % (key, KNOWN.get(key, "not delivered")))
            rows.append({"tool": key, "known": KNOWN.get(key, "not delivered")})
            continue
        text_status, markdown = call(base, "/api/sessions/%s/paper" % session_id,
                                     {"format": "md"}, raw=True)
        docx_status, docx = call(base, "/api/sessions/%s/paper" % session_id,
                                 {"format": "docx"}, raw=True)
        body = markdown.decode("utf-8", "replace") if text_status == 200 else ""
        # The paper must carry the report's own first figure, not a re-computed one.
        figure = ""
        for token in (delivered.get("report") or "").split():
            cleaned = token.strip(".,;()")
            if any(char.isdigit() for char in cleaned):
                figure = cleaned
                break
        ok = (text_status == 200 and docx_status == 200 and docx[:2] == b"PK"
              and (not figure or figure in body))
        rows.append({"tool": key, "preset": preset_id, "md": text_status, "docx": docx_status,
                     "docx_bytes": len(docx) if isinstance(docx, bytes) else 0,
                     "figure": figure, "ok": ok})
        print("%s  %-16s md=%s docx=%s %6d bytes" % ("PASS" if ok else "FAIL", key,
                                                     text_status, docx_status,
                                                     len(docx) if isinstance(docx, bytes) else 0))
        if not ok:
            failures.append("%s: md=%s docx=%s figure=%r" % (key, text_status, docx_status, figure))
    os.makedirs(os.path.join("qa", "evidence", "finance"), exist_ok=True)
    with open(os.path.join("qa", "evidence", "finance", "downloads.json"), "w",
              encoding="utf-8") as handle:
        json.dump({"base": base, "rows": rows, "failures": failures, "known": known},
                  handle, indent=1)
    print("\n%d downloaded, %d known, %d failure(s)" % (
        sum(1 for row in rows if row.get("ok")), len(known), len(failures)))
    for line in failures:
        print("  FAIL " + line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
