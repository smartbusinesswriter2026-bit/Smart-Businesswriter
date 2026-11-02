// Headless Chrome CDP probe for the Portfolio Lab redesign.
// Loads the live app, exercises the multi-symbol add, and captures screenshots.
const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9333;
const OUT = __dirname;
const BASE = process.argv[2] || "http://127.0.0.1:8000";

function getJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let body = "";
      res.on("data", (d) => (body += d));
      res.on("end", () => { try { resolve(JSON.parse(body)); } catch (e) { reject(e); } });
    }).on("error", reject);
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const profile = path.join(process.env.TEMP || ".", "sbw-cdp-profile");
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    "--remote-debugging-port=" + PORT, "--user-data-dir=" + profile,
    "--window-size=1440,2200", "about:blank",
  ], { stdio: "ignore" });

  let target = null;
  for (let i = 0; i < 60; i += 1) {
    await sleep(300);
    try {
      const list = await getJSON("http://127.0.0.1:" + PORT + "/json/list");
      target = list.find((t) => t.type === "page");
      if (target) break;
    } catch (e) { /* not up yet */ }
  }
  if (!target) { chrome.kill(); throw new Error("chrome devtools did not come up"); }

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let nextId = 1;
  const pending = new Map();
  const events = [];
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
    } else if (msg.method) {
      events.push(msg);
    }
  };
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  const send = (method, params) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params: params || {} }));
  });

  await send("Page.enable");
  await send("Runtime.enable");
  await send("Console.enable");
  const evaluate = async (expression) => {
    const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error("eval threw: " + JSON.stringify(r.exceptionDetails));
    return r.result.value;
  };

  await send("Page.navigate", { url: BASE + "/#/portfolio" });
  await sleep(4500);

  const report = {};
  report.labPresent = await evaluate(`!!document.querySelector("#portfoliolab")`);
  report.tabs = await evaluate(`Array.from(document.querySelectorAll("[data-pltab]")).map(b => b.textContent.trim())`);
  report.watchVisible = await evaluate(`(() => { const p = document.querySelector("#plpanel-watch"); return p ? !p.hidden : null; })()`);
  report.provider = await evaluate(`(() => { const s = document.querySelector("#plprovider"); return s ? Array.from(s.options).map(o => o.textContent) : null; })()`);

  // Screenshot the landing (lab is in the "Find and screen candidates" section).
  const shot = async (name, clip) => {
    const params = { format: "png" };
    if (clip) params.clip = Object.assign({ scale: 1 }, clip);
    const r = await send("Page.captureScreenshot", params);
    fs.writeFileSync(path.join(OUT, name), Buffer.from(r.data, "base64"));
    return name;
  };
  report.shotLanding = await shot("portfolio-lab-1-landing.png");

  // Exercise the multi-symbol add exactly as a student would.
  const before = await evaluate(`document.querySelectorAll("#plwatch tbody tr").length`);
  await evaluate(`(() => {
    const field = document.querySelector("#plnewsyms");
    field.value = "GOOGL";
    field.dispatchEvent(new Event("input", { bubbles: true }));
    document.querySelector("#pladdsymbols").click();
    return true;
  })()`);
  await sleep(9000);
  report.msgAfterAdd = await evaluate(`(document.querySelector("#plmsg") || {}).textContent || ""`);
  report.rowsBefore = before;
  report.rowsAfter = await evaluate(`document.querySelectorAll("#plwatch tbody tr").length`);
  report.watchSymbols = await evaluate(`Array.from(document.querySelectorAll("#plwatch tbody tr td:first-child strong")).map(e => e.textContent)`);
  report.prefillOptions = await evaluate(`(() => { const s = document.querySelector("#plida"); return s ? Array.from(s.options).map(o => o.textContent) : null; })()`);

  // Adding an already-tracked symbol must not duplicate it.
  await evaluate(`(() => {
    const field = document.querySelector("#plnewsyms");
    field.value = "MSFT, NVDA";
    field.dispatchEvent(new Event("input", { bubbles: true }));
    document.querySelector("#pladdsymbols").click();
    return true;
  })()`);
  await sleep(3000);
  report.msgOnDuplicate = await evaluate(`(document.querySelector("#plmsg") || {}).textContent || ""`);
  report.rowsAfterDuplicate = await evaluate(`document.querySelectorAll("#plwatch tbody tr").length`);

  // Switch to the screen tab and check the panel swaps.
  await evaluate(`document.querySelector('[data-pltab="screen"]').click()`);
  await sleep(400);
  report.screenPanelShown = await evaluate(`(() => { const p = document.querySelector("#plpanel-screen"); return p ? !p.hidden : null; })()`);
  report.watchPanelHidden = await evaluate(`(() => { const p = document.querySelector("#plpanel-watch"); return p ? p.hidden : null; })()`);
  // Screen from the watch list (JS click, then wait for the sourced rows).
  await evaluate(`document.querySelector("#plusewatch").click()`);
  await sleep(200);
  report.candsValue = await evaluate(`(document.querySelector("#plcands") || {}).value || ""`);
  await evaluate(`document.querySelector("#plscreen").click()`);
  await sleep(14000);
  report.screenRows = await evaluate(`Array.from(document.querySelectorAll("#plscreenout tbody tr")).map(tr => tr.textContent.replace(/\\s+/g, " ").trim())`);
  const labBox = await evaluate(`(() => { const el = document.querySelector("#portfoliolab"); if (!el) return null; const r = el.getBoundingClientRect(); return { x: Math.max(0, r.x), y: r.y + window.scrollY, width: r.width, height: r.height }; })()`);
  if (labBox) {
    await evaluate(`document.querySelector("#portfoliolab").scrollIntoView({ block: "start" })`);
    await sleep(500);
    report.shotLab = await shot("portfolio-lab-2-lab.png");
  }

  // Watch tab screenshot with the new rows.
  await evaluate(`document.querySelector('[data-pltab="watch"]').click()`);
  await sleep(1000);
  report.shotWatch = await shot("portfolio-lab-3-watch.png");

  // Evaluate tab screenshot.
  await evaluate(`document.querySelector('[data-pltab="prefill"]').click()`);
  await sleep(600);
  report.shotPrefill = await shot("portfolio-lab-4-evaluate.png");

  // Open the stored book and check the workspace "Find candidates" tab renders the lab.
  report.openBook = await evaluate(`(() => { const b = document.querySelector("[data-pfopen]"); if (!b) return null; b.click(); return true; })()`);
  await sleep(3000);
  report.workspaceTabs = await evaluate(`Array.from(document.querySelectorAll("[data-pftab]")).map(b => b.textContent.trim())`);
  await evaluate(`(() => { const b = document.querySelector('[data-pftab="screen"]'); if (b) b.click(); return true; })()`);
  await sleep(3500);
  report.labInWorkspace = await evaluate(`!!document.querySelector("#portfoliolab")`);
  report.workspaceTabChips = await evaluate(`Array.from(document.querySelectorAll("[data-pltab]")).map(b => b.textContent.trim())`);
  report.shotWorkspace = await shot("portfolio-lab-5-book-tab.png");

  // Holdings tab structure: a card per task, references behind a details card.
  await evaluate(`(() => { const b = document.querySelector('[data-pftab="holdings"]'); if (b) b.click(); return true; })()`);
  await sleep(1500);
  report.holdingsCards = await evaluate(`Array.from(document.querySelectorAll("#portfolioout h3")).map(h => h.textContent.trim())`);
  report.holdingsDetails = await evaluate(`Array.from(document.querySelectorAll("#portfolioout details > summary")).map(s => s.textContent.replace(/\\s+/g, " ").trim())`);
  report.addHoldingForm = await evaluate(`!!document.querySelector("#pfaddholding") && !!document.querySelector("#pfhsym")`);
  report.shotHoldings = await shot("portfolio-lab-6-holdings.png");

  report.pageErrors = events.filter((e) => e.method === "Runtime.consoleAPICalled" && e.params.type === "error")
    .map((e) => (e.params.args || []).map((a) => a.value || a.description || "").join(" ")).slice(0, 8);
  report.pageExceptions = events.filter((e) => e.method === "Runtime.exceptionThrown")
    .map((e) => (e.params.exceptionDetails && e.params.exceptionDetails.text) || "").slice(0, 8);

  console.log(JSON.stringify(report, null, 2));
  ws.close();
  chrome.kill();
}

main().catch((error) => { console.error("PROBE FAILED: " + (error && error.stack || error)); process.exit(1); });
