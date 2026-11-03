"""Measure the Project management grid form in the machine's own Chrome.

Why this exists: ``test_E_pm_080`` can assert only that the page *carries* the
rules that stop a grid pushing the page sideways - it cannot read a scrollbar.
A width claim that leaves no artefact cannot be re-run by the next lane, so this
script drives a real browser, measures ``scrollWidth`` against ``clientWidth`` at
1280 px and 390 px for each of the four grids, and captures the screenshots the
walkthrough cites (the filled grid at both widths and the refusal state).

    python qa/measure_pm_grid.py                  # serves this tree on 8011
    python qa/measure_pm_grid.py 8013             # or a port you choose

No dependency is added and no product code is touched: the server runs in a
thread inside this process, and the browser is the machine's installed Chromium,
driven over the DevTools protocol with the standard library only (a minimal
WebSocket client is included below).  It never touches ports 8000 or 8021.

Writes ``qa/evidence/project-management/grid-form.json`` (the numbers) and
merges them into ``clickthrough.json`` (the shelf's own evidence file), plus
``05``-``07`` PNGs.  Exit code 1 if any grid scrolls sideways, so it can gate.
"""

import base64
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

sys.path.insert(0, "src")

OUT = os.path.join("qa", "evidence", "project-management")
SUBJECT = "project-management"
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
WIDTHS = [(1280, 1600), (390, 1400)]

# Each grid: how the student would fill it.  Plain words, no figures - a
# worksheet cell is the student's evidence, and this demo fill invents none.
GRIDS = [
    {"id": "template_balanced_scorecard", "label": "Balanced Scorecard",
     "rows": "Financial\nCustomer\nInternal process\nOrganisational capacity",
     "cols": "Objective\nMeasure\nTarget\nInitiative",
     "fill": ["the sponsor's funding note", "we track this monthly", "agreed at kick-off",
              "from the delivery review"]},
    {"id": "template_strategy_map", "label": "Strategy Map",
     "rows": "Shorten the order-to-dispatch cycle\nReduce rework at handover",
     "cols": "Perspective\nObjective\nDrives\nMeasure",
     "fill": ["internal process", "fewer handoffs", "the operations review", "our own log"]},
    {"id": "template_kpi_tree", "label": "KPI Tree",
     "rows": "On-time milestone completion\nSchedule variance\nMilestone slip count",
     "cols": "Level\nMetric\nFormula or definition\nSource",
     "fill": ["outcome", "driver", "our tracker", "we define it as we measure it"]},
    {"id": "template_okrs", "label": "OKRs",
     "rows": "Cut cost overrun on delivery projects\nImprove sign-off speed",
     "cols": "Objective\nKey results\nBaseline to target\nSource",
     "fill": ["fewer change orders", "our finance close", "no baseline yet", "sponsor note"]},
]

DRIVE = """(async () => {
  await openWorksheet('__ID__', '__LABEL__', '');
  await new Promise(r => setTimeout(r, 450));
  const rows = document.getElementById('mx-rows');
  const cols = document.getElementById('mx-cols');
  if (!rows || !cols) return {error: 'the grid form did not render'};
  rows.value = __ROWS__; cols.value = __COLS__;
  document.getElementById('mx-build').click();
  await new Promise(r => setTimeout(r, 150));
  const fills = __FILL__;
  const cells = [...document.querySelectorAll('input[id^="mx-cell-"],[id^="mxc-cell-"]')];
  cells.forEach((el, i) => { el.value = fills[i % fills.length]; });
  const wrap = document.querySelector('.mxgridtablewrap');
  const cards = document.querySelector('.mxcards');
  const seen = (el) => !!(el && el.offsetParent);
  const doc = document.documentElement;
  const titles = [...document.querySelectorAll('.wtitle')].map(el => el.textContent.trim());
  return {
    template: '__ID__',
    rows_label: titles[0] || '',
    cols_label: titles[1] || '',
    cols_hint: (document.querySelectorAll('.wprompt')[1] || {}).textContent || '',
    intro: ((document.querySelector('.wintro') || {}).textContent || '').trim(),
    served_copy: (state.worksheet && state.worksheet.form_copy) || null,
    cells: cells.length,
    table_visible: seen(wrap),
    cards_visible: seen(cards),
    aria_label: (cells[0] && cells[0].getAttribute('aria-label')) || '',
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
    grid_scrollWidth: wrap ? wrap.scrollWidth : null,
    grid_clientWidth: wrap ? wrap.clientWidth : null,
    sideways: doc.scrollWidth > doc.clientWidth,
    user_agent: navigator.userAgent
  };
})()"""

REFUSE = """(async () => {
  const rows = document.getElementById('mx-rows');
  const cols = document.getElementById('mx-cols');
  rows.value = 'An objective I cannot evidence yet';
  cols.value = 'One\\nTwo\\nThree\\nFour';
  document.getElementById('mx-build').click();
  await new Promise(r => setTimeout(r, 120));
  document.querySelectorAll('input[id^="mx-cell-"],[id^="mxc-cell-"]').forEach(el => { el.value = ''; });
  const returned = collectMatrixInputs(state.worksheet);
  await new Promise(r => setTimeout(r, 120));
  const box = document.getElementById('mx-refusal');
  const doc = document.documentElement;
  return {
    returned_null: returned === null,
    shown: !!(box && !box.hidden),
    banner: box ? box.textContent.replace(/\\s+/g, ' ').trim() : '',
    tokens: /[{}]|template_|undefined/.test(box ? box.textContent : ''),
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth
  };
})()"""


class Ws:
    """A minimal WebSocket client: enough for the DevTools protocol, nothing more."""

    def __init__(self, url):
        rest = url.split("://", 1)[1]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=90)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n"
                           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
                           "Sec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("the browser closed the socket during the handshake")
            head += chunk
        if b"101" not in head.split(b"\r\n", 1)[0]:
            raise RuntimeError("websocket handshake refused: %r" % head.split(b"\r\n", 1)[0])
        self.buf = head.split(b"\r\n\r\n", 1)[1]

    def _read(self, size):
        while len(self.buf) < size:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("the browser closed the socket")
            self.buf += chunk
        out, self.buf = self.buf[:size], self.buf[size:]
        return out

    def _frame(self, opcode, data):
        header = bytearray([0x80 | opcode])
        mask = os.urandom(4)
        size = len(data)
        if size < 126:
            header.append(0x80 | size)
        elif size < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", size)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", size)
        header += mask
        return bytes(header) + bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))

    def send(self, text):
        self.sock.sendall(self._frame(0x1, text.encode("utf-8")))

    def _payload(self, masked, size):
        mask = self._read(4) if masked else None
        payload = self._read(size)
        if mask:
            payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        return payload

    def recv(self):
        while True:
            first, second = self._read(2)
            fin, opcode = first & 0x80, first & 0x0F
            masked, size = second & 0x80, second & 0x7F
            if size == 126:
                size = struct.unpack(">H", self._read(2))[0]
            elif size == 127:
                size = struct.unpack(">Q", self._read(8))[0]
            payload = self._payload(masked, size)
            if opcode == 0x8:
                raise RuntimeError("the browser closed the socket")
            if opcode == 0x9:
                self.sock.sendall(self._frame(0xA, payload))
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x1, 0x2):
                while not fin:
                    first, second = self._read(2)
                    fin = first & 0x80
                    masked, size = second & 0x80, second & 0x7F
                    if size == 126:
                        size = struct.unpack(">H", self._read(2))[0]
                    elif size == 127:
                        size = struct.unpack(">Q", self._read(8))[0]
                    payload += self._payload(masked, size)
                return payload.decode("utf-8", "replace")


class Devtools:
    def __init__(self, ws):
        self.ws = ws
        self.next_id = 0

    def call(self, method, params=None, timeout=90):
        self.next_id += 1
        wanted = self.next_id
        self.ws.send(json.dumps({"id": wanted, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            message = json.loads(self.ws.recv())
            if message.get("id") != wanted:
                continue
            if "error" in message:
                raise RuntimeError("%s refused: %s" % (method, message["error"]))
            return message.get("result") or {}
        raise RuntimeError("no answer to %s within %ss" % (method, timeout))

    def script(self, expression, await_promise=True):
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True,
                                                "awaitPromise": await_promise})
        if result.get("exceptionDetails"):
            detail = result["exceptionDetails"]
            raise RuntimeError("page error: %s" % (detail.get("text") or detail))
        return (result.get("result") or {}).get("value")



def launch():
    """Start the machine's Chromium headless with a DevTools port of its choosing."""
    for path in CHROME:
        if not os.path.exists(path):
            continue
        profile = tempfile.mkdtemp(prefix="bw-grid-")
        process = subprocess.Popen(
            [path, "--headless=new", "--disable-gpu", "--no-first-run",
             "--no-default-browser-check", "--disable-extensions",
             "--disable-background-networking", "--mute-audio",
             "--remote-debugging-port=0", "--user-data-dir=" + profile,
             "--window-size=1280,1600", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        marker = os.path.join(profile, "DevToolsActivePort")
        for _ in range(160):
            if os.path.exists(marker):
                lines = open(marker, encoding="utf-8").read().split()
                if len(lines) >= 2:
                    return process, path, lines[0]
            if process.poll() is not None:
                break
            time.sleep(0.25)
        process.terminate()
    raise RuntimeError("no Chromium found to measure with")


def serve_here(port):
    """Serve this tree from inside this process, so the measurement is of the commit."""
    from bp.server import serve
    threading.Thread(target=serve, kwargs={"port": port, "sandbox": False}, daemon=True).start()
    for _ in range(160):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/api/health" % port, timeout=2) as answer:
                if answer.status == 200:
                    return "http://127.0.0.1:%d" % port
        except Exception:                                            # noqa: BLE001
            time.sleep(0.25)
    raise RuntimeError("the workbench did not answer on %d" % port)


def load(page, url):
    """Load a fresh document.  Navigating to the same hash twice is a same-document
    navigation in Chrome, which would leave the previous width's DOM - and its
    toasts - in place, so the page is blanked first and the width is in the query."""
    page.call("Page.navigate", {"url": "about:blank"})
    time.sleep(0.2)
    page.call("Page.navigate", {"url": url})
    deadline = time.time() + 45
    while time.time() < deadline:
        try:
            if page.script("document.readyState", await_promise=False) == "complete" and \
                    page.script("typeof openWorksheet === 'function'", await_promise=False):
                return
        except Exception:                                            # noqa: BLE001
            pass
        time.sleep(0.2)
    raise RuntimeError("the page did not boot: " + url)


def focus_grid(page):
    """Bring the grid into view, so a narrow screenshot shows the cards and not
    the top of the form."""
    page.script("(() => { const el = document.querySelector('.mxgrid') || "
                "document.querySelector('.mxcards'); if (el) el.scrollIntoView(); "
                "window.scrollBy(0, -12); return true; })()", await_promise=False)
    time.sleep(0.25)


def build_pill(page):
    """The top bar's build pill, as the student sees it.

    It is painted from `/api/health` after boot, so this waits for the number to
    arrive rather than reading an empty span.  D-PM-07 was a literal here; the
    pill must now state the build the server reports.
    """
    for _ in range(40):
        text = page.script("(() => { const p = document.getElementById('buildpill'); "
                           "return p ? p.textContent.trim() : null; })()", await_promise=False)
        if text:
            return text
        time.sleep(0.15)
    return text


def shot(page, name):
    answer = page.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
    path = os.path.join(OUT, name)
    with open(path, "wb") as handle:
        handle.write(base64.b64decode(answer["data"]))
    return {"name": name, "saved": os.path.exists(path),
            "bytes": os.path.getsize(path) if os.path.exists(path) else 0}


def drive(page, grid):
    script = (DRIVE.replace("__ID__", grid["id"]).replace("__LABEL__", grid["label"])
              .replace("__ROWS__", json.dumps(grid["rows"]))
              .replace("__COLS__", json.dumps(grid["cols"]))
              .replace("__FILL__", json.dumps(grid["fill"])))
    return page.script(script)



def main(port):
    os.makedirs(OUT, exist_ok=True)
    base = serve_here(port)
    process, chrome, devtools_port = launch()
    try:
        listing = "http://127.0.0.1:%s/json/list" % devtools_port
        with urllib.request.urlopen(listing, timeout=20) as answer:
            targets = json.loads(answer.read().decode("utf-8"))
        target = [row for row in targets if row.get("type") == "page"][0]
        page = Devtools(Ws(target["webSocketDebuggerUrl"]))
        page.call("Page.enable")
        page.call("Runtime.enable")

        report = {"base": base, "chrome": chrome, "subject": SUBJECT,
                  "url": base + "/#/subject/" + SUBJECT,
                  "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                  "note": ("The cell text in the screenshots is a fixed cycle of short "
                           "phrases typed into the form to prove the grid renders filled. "
                           "It is not student data and it contains no figures."),
                  "widths": {}, "refusal": {}, "screenshots": [], "sideways": []}
        for width, height in WIDTHS:
            page.call("Emulation.setDeviceMetricsOverride", {
                "width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
            load(page, base + "/?viewport=%d#/subject/" % width + SUBJECT)
            report.setdefault("build_pill", {})[str(width)] = build_pill(page)
            for grid in GRIDS:
                measured = drive(page, grid)
                measured["viewport"] = {"width": width, "height": height}
                report["widths"].setdefault(str(width), {})[grid["id"]] = measured
                if measured.get("error"):
                    continue
                if measured.get("sideways"):
                    report["sideways"].append({"width": width, "template": grid["id"],
                                               "scrollWidth": measured.get("scrollWidth"),
                                               "clientWidth": measured.get("clientWidth")})
                if grid["id"] in ("template_okrs", "template_balanced_scorecard"):
                    short = "okrs" if grid["id"] == "template_okrs" else "scorecard"
                    focus_grid(page)
                    report["screenshots"].append(
                        shot(page, "05-grid-form-%s-%d.png" % (short, width)))
            # the designed refusal, at this width, on the grid the walkthrough opens
            drive(page, GRIDS[-1])
            report["refusal"][str(width)] = page.script(REFUSE)
            if width == 1280:
                report["screenshots"].append(shot(page, "07-grid-form-refusal-1280.png"))

        with open(os.path.join(OUT, "grid-form.json"), "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=1)
        # the shelf's own evidence file carries the numbers too, so the claim and
        # the artefact are not in two places
        carried = os.path.join(OUT, "clickthrough.json")
        existing = {}
        if os.path.exists(carried):
            with open(carried, encoding="utf-8") as handle:
                existing = json.load(handle)
        existing["grid_form"] = {
            "measured_at": report["measured_at"],
            "url": report["url"],
            "method": "Chrome over the DevTools protocol: scrollWidth against clientWidth",
            "script": "qa/measure_pm_grid.py",
            "widths": {width: {tid: {"scrollWidth": row.get("scrollWidth"),
                                     "clientWidth": row.get("clientWidth"),
                                     "table_visible": row.get("table_visible"),
                                     "cards_visible": row.get("cards_visible"),
                                     "cells": row.get("cells")}
                               for tid, row in rows.items()}
                       for width, rows in report["widths"].items()},
            "refusal": report["refusal"],
            "sideways": report["sideways"],
            "build_pill": report.get("build_pill", {}),
            "screenshots": [row["name"] for row in report["screenshots"]],
        }
        with open(carried, "w", encoding="utf-8") as handle:
            json.dump(existing, handle, indent=1)

        for width, rows in report["widths"].items():
            for template, row in rows.items():
                print("%5s px  %-30s scroll %-5s client %-5s table %-5s cards %-5s %s"
                      % (width, template, row.get("scrollWidth"), row.get("clientWidth"),
                         row.get("table_visible"), row.get("cards_visible"),
                         "SIDEWAYS" if row.get("sideways") else "ok"))
        for width, row in report["refusal"].items():
            print("%5s px  refusal: shown=%s null=%s token=%s"
                  % (width, row.get("shown"), row.get("returned_null"), row.get("tokens")))
        print("build pill: " + ", ".join("%s px -> %s" % (w, p)
                                         for w, p in (report.get("build_pill") or {}).items()))
        print("screenshots: " + ", ".join(row["name"] for row in report["screenshots"]))
        return 1 if report["sideways"] else 0
    finally:
        try:
            process.terminate()
            process.wait(timeout=20)
        except Exception:                                            # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8011))

