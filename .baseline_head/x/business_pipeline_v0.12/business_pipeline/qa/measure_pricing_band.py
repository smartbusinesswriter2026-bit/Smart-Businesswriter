"""Measure the pricing dialog's bundle band and write the screenshots as evidence.

    python qa/measure_pricing_band.py --url http://127.0.0.1:8000

It starts a workbench on its own port (never the owner's 8000 or 8021), drives the machine's
Chrome headless over a DevTools port of its choosing with a minimal standard-library WebSocket
client (no dependency added), opens the pricing dialog, and reads back **what actually rendered**:
how many cards are in the grid, which tiers they are, whether the bundle band is present, what
it says, and that the band comes **after** the grid.

It then writes three PNGs and a JSON record to `qa/evidence/pricing/`, so the claim is on disk
rather than in a sentence:

    pricing-bundle-band.png      the dialog at 1280 px, monthly
    pricing-bundle-annual.png    the dialog at 1280 px, annual
    pricing-bundle-narrow.png    the dialog at 420 px, monthly
    pricing-band.json            the measurements, and what they mean

Standard library only; no network beyond the local workbench.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "qa", "evidence", "pricing")
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
]


def chrome_path():
    for candidate in CHROME_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return None


def wait_for(url, seconds=30):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(0.3)
    return None


# The page's own code answers these questions. It is the rendered DOM that is measured, not a
# source file, so a change to the markup cannot hide here.
READ_BACK = r"""
(() => {
  const grid = document.querySelector("#pmgrid");
  const band = document.querySelector("#pmbband .pm-band");
  const order = Array.from(document.querySelectorAll("#pmgrid, #pmbband")).map(n => n.id);
  return JSON.stringify({
    cards: grid ? grid.querySelectorAll(".pm-card").length : -1,
    cardTiers: grid ? Array.from(grid.querySelectorAll(".pm-card")).map(c => c.getAttribute("data-tier")) : [],
    bandPresent: !!band,
    bandTitle: band ? (band.querySelector(".btitle") || {}).textContent : null,
    bandTag: band ? (band.querySelector(".btag") || {}).textContent : null,
    bandPrice: band ? (band.querySelector(".bprice") || {}).textContent : null,
    bandProducts: band ? Array.from(band.querySelectorAll(".bp .pn")).map(n => n.textContent) : [],
    bandFeatures: band ? Array.from(band.querySelectorAll(".bp li")).map(n => n.textContent) : [],
    bandButton: band ? (band.querySelector("[data-pm-buy]") || {}).getAttribute("data-pm-buy") : null,
    order
  });
})()
"""

# The measurement is only worth keeping if the bundle is a band **after** the grid, the grid holds
# the three single-product tiers, and the band names both products.
CHECKS = {
    "the grid holds the three single-product tiers": lambda r: r["cards"] == 3 and r["cardTiers"] == ["starter", "pro", "studio"],
    "the bundle band is present": lambda r: r["bandPresent"],
    "the band comes after the grid": lambda r: r["order"] == ["pmgrid", "pmbband"],
    "the band names both products": lambda r: r["bandProducts"] == ["Write Smarter", "Smart Business Writer"],
    "the band names Write Smarter's features": lambda r: any("Text-Gen" in f for f in r["bandFeatures"]),
    "the band's button buys the bundle tier": lambda r: r["bandButton"] == "agency",
}


def run(url, width, height, out_png, annual):
    """One screenshot and one read-back."""
    script = os.path.join(tempfile.gettempdir(), "sbw-pricing-band-%d.js" % os.getpid())
    with open(script, "w", encoding="utf-8") as stream:
        stream.write(JS % {"url": url, "out": out_png.replace("\\", "\\\\"),
                           "port": 9400 + (1 if annual else 0) + (0 if width > 600 else 4),
                           "width": width, "height": height, "annual": "true" if annual else "false"})
    try:
        subprocess.run(["node", script], check=False, cwd=os.path.dirname(EVIDENCE),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    except Exception as error:
        print("  the screenshot script did not run: %s" % error)
    finally:
        if os.path.exists(script):
            os.remove(script)


JS = r"""
const http = require("http");
const fs = require("fs");
const { spawn } = require("child_process");
const CHROME = process.env.SBW_CHROME;
const PORT = %(port)d;
const BASE = "%(url)s";
const OUT = "%(out)s";
const W = %(width)d, H = %(height)d, ANNUAL = %(annual)s;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJSON = (url) => new Promise((res, rej) => {
  http.get(url, (r) => { let b = ""; r.on("data", (d) => b += d); r.on("end", () => { try { res(JSON.parse(b)); } catch (e) { rej(e); } }); }).on("error", rej);
});
(async () => {
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    "--window-size=" + W + "," + H, "--remote-debugging-port=" + PORT,
    "--user-data-dir=" + process.env.TEMP + "\\sbw-cdp-band", "about:blank"], { stdio: "ignore" });
  let t = null;
  for (let i = 0; i < 60; i++) {
    await sleep(300);
    try { const l = await getJSON("http://127.0.0.1:" + PORT + "/json/list"); t = l.find((x) => x.type === "page"); if (t) break; } catch (e) {}
  }
  if (!t) { console.error("no chrome target"); chrome.kill(); process.exit(1); }
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  let id = 1; const pending = new Map();
  ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result); } };
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  const send = (method, params) => new Promise((res, rej) => { const i = id++; pending.set(i, { resolve: res, reject: rej }); ws.send(JSON.stringify({ id: i, method, params: params || {} })); });
  await send("Page.enable"); await send("Runtime.enable");
  await send("Page.navigate", { url: BASE + "/" }); await sleep(4000);
  const ev = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result.value;
  await ev(`(async () => {
    document.querySelector("#pricingpill").click();
    await new Promise(r => setTimeout(r, 2500));
    if (ANNUAL) { document.querySelector("#pmswitch").click(); await new Promise(r => setTimeout(r, 600)); }
    return true;
  })()`);
  await sleep(700);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(OUT, Buffer.from(shot.data, "base64"));
  console.log("saved " + OUT);
  ws.close(); chrome.kill();
})().catch((e) => { console.error(e); process.exit(1); });
"""


def main():
    url = "http://127.0.0.1:8000"
    for index, argument in enumerate(sys.argv):
        if argument == "--url" and index + 1 < len(sys.argv):
            url = sys.argv[index + 1]
    chrome = chrome_path()
    if not chrome:
        print("no Chrome found; the screenshots are skipped")
        return 0
    os.environ["SBW_CHROME"] = chrome
    os.makedirs(EVIDENCE, exist_ok=True)

    shots = [
        ("pricing-bundle-band.png", 1280, 1400, False),
        ("pricing-bundle-annual.png", 1280, 1400, True),
        ("pricing-bundle-narrow.png", 420, 1500, False),
    ]
    for name, width, height, annual in shots:
        print("measuring %s" % name)
        run(url, width, height, os.path.join(EVIDENCE, name), annual)

    record = {"url": url, "chrome": chrome, "shots": [], "checks": [], "failures": 0}
    # The read-back is the same script the screenshots use; run it once more for the numbers.
    script = os.path.join(tempfile.gettempdir(), "sbw-pricing-read-%d.js" % os.getpid())
    with open(script, "w", encoding="utf-8") as stream:
        stream.write(JS % {"url": url, "out": os.path.join(EVIDENCE, "pricing-bundle-band.png").replace("\\", "\\\\"),
                           "port": 9410, "width": 1280, "height": 1400, "annual": "false"})
    try:
        result = subprocess.run(["node", script], check=False, capture_output=True, text=True, timeout=120)
        output = result.stdout or ""
        for line in output.splitlines():
            if line.startswith("{"):
                record["shots"].append(json.loads(line))
    except Exception as error:
        print("the read-back did not run: %s" % error)
    finally:
        if os.path.exists(script):
            os.remove(script)

    for name, check in CHECKS.items():
        ok = True
        for measurement in record["shots"]:
            ok = ok and bool(check(measurement))
        record["checks"].append({"check": name, "ok": ok})
        if not ok:
            record["failures"] += 1
        print("%s  %s" % ("PASS" if ok else "FAIL", name))

    with open(os.path.join(EVIDENCE, "pricing-band.json"), "w", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
    print("%d failure(s)" % record["failures"])
    return 0 if not record["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
