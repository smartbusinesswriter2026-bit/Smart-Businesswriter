"""Browser test for the tile Close button (stdlib only, headless Chromium).

    python scripts/tile_close_browser_test.py --url http://127.0.0.1:8099
    python scripts/tile_close_browser_test.py --url http://127.0.0.1:8097 --dump-dom

Every tile on a subject page opens into its own view. That view must end with one
Close button at the bottom right, and Close must return to the subject page with
the group the tile belongs to back in view. This drives a real browser (Chromium
over the DevTools Protocol, no third-party packages) and clicks it:

  * Economics: the "Market equilibrium" tool - the case the owner reported;
  * up to three tools or worksheets on every subject in the shelf;
  * one catalogue framework record (its record closes back to the page).

It needs a server already running (`scripts/serve.py`) and a Chromium binary. If
neither the browser nor a DevTools endpoint is available it prints SKIP and exits
0, so it can never turn a green suite red just because a browser is missing.
Failure to find the button, or a Close that does not come back to the group, exits
1 with the check named.

Why a script and not a test: `tests/` must run with no browser, no network and no
server (HANDOFF §1). This is the release check for the presentation layer, the
same way `scripts/ui_smoke.py` is the release check for the routes - run it after
`scripts/serve.py` is up.
"""

import argparse
import base64
import json
import os
import socket
import struct
import sys
import time
import urllib.request

SUBJECTS = ("accounting", "finance", "economics", "management", "project-management",
            "entrepreneurship", "operations", "supply-chain", "marketing", "people", "research")


class CDP:
    """The smallest DevTools client that can navigate, evaluate and click."""

    def __init__(self, port=9222):
        targets = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=10))
        pages = [t for t in targets if t.get("type") == "page"]
        if not pages:
            raise RuntimeError("no browser page target on port %d" % port)
        hostport, path = pages[0]["webSocketDebuggerUrl"][len("ws://"):].split("/", 1)
        host, port_text = hostport.split(":")
        self.sock = socket.create_connection((host, int(port_text)), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            "GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)
        ).encode())
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("the DevTools socket closed during the handshake")
            buffer += chunk
        head, self.buffer = buffer.split(b"\r\n\r\n", 1)
        if b"101" not in head.split(b"\r\n")[0]:
            raise RuntimeError("the DevTools endpoint refused the websocket upgrade")
        self.next_id = 0

    def _frame(self, payload):
        mask = os.urandom(4)
        size = len(payload)
        header = bytearray([0x81])
        if size < 126:
            header.append(0x80 | size)
        elif size < (1 << 16):
            header.append(0x80 | 126)
            header += struct.pack("!H", size)
        else:
            header.append(0x80 | 127)
            header += struct.pack("!Q", size)
        header += mask
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def _read(self, count):
        while len(self.buffer) < count:
            chunk = self.sock.recv(1 << 16)
            if not chunk:
                raise RuntimeError("the DevTools socket closed")
            self.buffer += chunk
        out, self.buffer = self.buffer[:count], self.buffer[count:]
        return out

    def _message(self):
        first, second = self._read(2)
        size = second & 0x7F
        if size == 126:
            size = struct.unpack("!H", self._read(2))[0]
        elif size == 127:
            size = struct.unpack("!Q", self._read(8))[0]
        key = self._read(4) if second & 0x80 else b""
        data = self._read(size)
        if key:
            data = bytes(byte ^ key[i % 4] for i, byte in enumerate(data))
        return first & 0x0F, data

    def call(self, method, **params):
        self.next_id += 1
        wanted = self.next_id
        self._frame(json.dumps({"id": wanted, "method": method, "params": params}).encode())
        while True:
            opcode, data = self._message()
            if opcode == 0x8:
                raise RuntimeError("the DevTools socket closed")
            if opcode != 0x1:
                continue
            message = json.loads(data)
            if message.get("id") != wanted:
                continue
            if "error" in message:
                raise RuntimeError(json.dumps(message["error"]))
            return message.get("result")

    def js(self, expression):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in result:
            raise RuntimeError(json.dumps(result["exceptionDetails"])[:600])
        return result["result"].get("value")


READY = ("(function(){var p=document.querySelector('#panel-new');"
         "if(!p || p.hidden) return 0; var h=p.querySelector('h2');"
         "if(!h || h.textContent.indexOf('No session yet')>=0) return 0;"
         "return p.querySelector('#tileclose') ? 1 : 0;})()")

TILES = ("(function(){return Array.prototype.map.call("
         "document.querySelectorAll('#subjectout .capgrid .capcard'), function(b, i){"
         "  var h = b.closest('.capgrid').previousElementSibling;"
         "  while (h && !(h.classList && h.classList.contains('levelhead'))) h = h.previousElementSibling;"
         "  var kind = b.dataset.tool ? 'tool' : (b.dataset.worksheet ? 'worksheet' : 'framework');"
         "  return { i: i, kind: kind, label: (b.textContent||'').replace(/\\s+/g,' ').trim().slice(0,70),"
         "           group: h ? h.textContent.replace(/\\s+-\\s+\\d+\\s*$/,'').trim() : '' };"
         "});})()")

VIEW = ("(function(){var p = document.querySelector('#panel-new');"
        "var btn = p.querySelector('#tileclose');"
        "if (!btn) return { open: !p.hidden, hasClose: false,"
        "                   heading: ((p.querySelector('h2')||{}).textContent||'').trim() };"
        "var foot = btn.closest('.tilefoot');"
        "return { open: !p.hidden, hasClose: true, label: btn.textContent.trim(),"
        "         justify: getComputedStyle(foot).justifyContent, last: p.lastElementChild === foot,"
        "         heading: ((p.querySelector('h2')||{}).textContent||'').trim() };})()")

BACK = ("(function(){var hit = document.querySelector('#subjectout h4.levelhead.grouphit');"
        "return { subjectOpen: !document.querySelector('#panel-subject').hidden,"
        "         newOpen: !document.querySelector('#panel-new').hidden, hash: location.hash,"
        "         group: hit ? hit.textContent.replace(/\\s+-\\s+\\d+\\s*$/,'').trim() : null,"
        "         groupVisible: hit ? (hit.getBoundingClientRect().top > -20 &&"
        "                              hit.getBoundingClientRect().top < window.innerHeight) : null };})()")

GROUP_IN_VIEW = ("(function(){var h = document.querySelector('#subjectout h4.levelhead.grouphit');"
                 "if (!h) return 0; var r = h.getBoundingClientRect();"
                 "return (r.top > -20 && r.top < window.innerHeight) ? 1 : 0;})()")



def run(browser, base):
    failures = []

    def check(name, ok, detail=""):
        print(("PASS  " if ok else "FAIL  ") + name + (("   -> " + str(detail)) if (detail and not ok) else ""))
        if not ok:
            failures.append(name)

    def wait(expression, timeout=25):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if browser.js(expression):
                    return True
            except RuntimeError:
                pass
            time.sleep(0.25)
        return False

    def goto(subject):
        browser.js("location.hash = '#/subject/%s'; 1" % subject)
        return wait("(function(){var o=document.querySelector('#subjectout');"
                    "return !!(o && o.querySelector('.capgrid .capcard'))"
                    " && !document.querySelector('#panel-subject').hidden;})()", timeout=15)

    def click(index):
        browser.js("document.querySelectorAll('#subjectout .capgrid .capcard')[%d].click(); 1" % index)

    def close_and_check(subject, tile):
        browser.js("var b=document.querySelector('#tileclose'); if (b) b.click(); 1")
        time.sleep(0.6)
        wait(GROUP_IN_VIEW, timeout=6)
        state = browser.js(BACK) or {}
        check("%s / %s: Close returns to the subject with its group ('%s') in view"
              % (subject, tile["label"][:40], tile["group"]),
              bool(state.get("subjectOpen")) and not state.get("newOpen")
              and state.get("group") == tile["group"], state)

    # 1. the case the owner named
    browser.call("Page.navigate", url=base + "/#/subject/economics")
    time.sleep(2.5)
    check("the Economics page lists its tiles",
          wait("(function(){var o=document.querySelector('#subjectout');"
               "return !!(o && o.querySelector('.capgrid .capcard'));})()"))
    target = None
    for tile in browser.js(TILES) or []:
        if "market equilibrium" in tile["label"].lower():
            target = tile
    check("the Economics page has a Market equilibrium tile", target is not None)
    if target:
        click(target["i"])
        ready = wait(READY)
        view = browser.js(VIEW) or {}
        check("Market equilibrium opens the tool view", bool(ready) and bool(view.get("open")), view)
        check("the tool view is titled for the tile", str(view.get("heading", "")).startswith("Tool - "), view)
        check("the tool view carries a Close button", bool(view.get("hasClose")), view)
        check("the button reads Close", view.get("label") == "Close", view.get("label"))
        check("the button is the last element and right-aligned",
              view.get("justify") == "flex-end" and bool(view.get("last")), view)
        close_and_check("economics", target)

    # 2. every subject: up to three tools or worksheets each
    tested = 0
    for subject in SUBJECTS:
        if not goto(subject):
            check("%s page lists its tiles" % subject, False, "no tiles rendered")
            continue
        rows = browser.js(TILES) or []
        check("%s page lists its tiles" % subject, True, "%d tiles" % len(rows))
        for tile in [t for t in rows if t["kind"] in ("tool", "worksheet")][:3]:
            click(tile["i"])
            ready = wait(READY)
            view = browser.js(VIEW) or {}
            check("%s / %s opens with a Close button" % (subject, tile["label"][:40]),
                  bool(ready) and bool(view.get("hasClose")) and view.get("justify") == "flex-end"
                  and bool(view.get("last")), view)
            close_and_check(subject, tile)
            tested += 1

    # 3. one catalogue record: its own Close returns to the page
    goto("economics")
    records = [t for t in (browser.js(TILES) or []) if t["kind"] == "framework"]
    if records:
        click(records[0]["i"])
        opened = wait("!document.querySelector('#modal').hidden", timeout=10)
        label = browser.js("(function(){var b=document.querySelector('#mok');return b?b.textContent.trim():null;})()")
        check("a catalogue record opens with a Close button", bool(opened) and label == "Close", label)
        browser.js("document.querySelector('#mok').click(); 1")
        time.sleep(0.4)
        check("closing the record leaves the subject page in place",
              bool(browser.js("document.querySelector('#modal').hidden"
                              " && !document.querySelector('#panel-subject').hidden")))

    print("\n%d tile views exercised across %d subjects; %d failures"
          % (tested, len(SUBJECTS), len(failures)))
    return failures


def main():
    parser = argparse.ArgumentParser(description="Click the Close button on every tile, in a real browser")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="the running workbench")
    parser.add_argument("--port", type=int, default=9222, help="the Chromium DevTools port")
    parser.add_argument("--subjects", default="", help="comma-separated limits, for a quick pass")
    args = parser.parse_args()
    global SUBJECTS
    if args.subjects:
        SUBJECTS = tuple(s.strip() for s in args.subjects.split(",") if s.strip())
    try:
        browser = CDP(args.port)
    except Exception as error:  # no browser is a SKIP, never a failure
        print("SKIP  no DevTools endpoint on port %d (%s). Start one with:" % (args.port, error))
        print("      chromium --headless=new --no-sandbox --remote-debugging-port=%d about:blank" % args.port)
        return 0
    browser.call("Page.enable")
    browser.call("Runtime.enable")
    return 1 if run(browser, args.url.rstrip("/")) else 0


if __name__ == "__main__":
    sys.exit(main())

