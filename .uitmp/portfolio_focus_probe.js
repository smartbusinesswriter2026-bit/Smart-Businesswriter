// Focused CDP checks for the controls the first audits could not exercise:
// the reference search with no class filter, Use, the two file inputs, the create
// validation, and "Open in the Business Calculator" from a ready prefill.
const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9336;
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

const AUDIT = `
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const txt = (s) => { const el = $(s); return el ? el.textContent.replace(/\\s+/g, " ").trim() : null; };
  const results = [];
  const errors = [];
  window.addEventListener("error", (e) => errors.push("window error: " + e.message));
  window.addEventListener("unhandledrejection", (e) => errors.push("unhandled rejection: " + (e.reason && e.reason.message || e.reason)));
  const step = async (name, fn) => {
    try {
      const note = await fn();
      results.push({ control: name, ok: true, note: note === undefined ? "" : String(note).slice(0, 200) });
    } catch (error) {
      results.push({ control: name, ok: false, note: String(error && error.message || error).slice(0, 200) });
    }
    await sleep(150);
  };

  /* ---- create-book validation on the landing ---- */
  location.hash = "#/portfolio";
  await sleep(3500);
  await step("#pfcreate with no name names the gap", async () => {
    $("#pfname").value = "";
    $("#pfcreate").click(); await sleep(700);
    const msg = txt("#pfmsg");
    if (!/name is required/i.test(msg || "")) throw new Error("unexpected: " + msg);
    return msg.slice(0, 100);
  });

  /* ---- inside the book: reference search without a class filter, Use, file inputs ---- */
  $("[data-pfopen]").click();
  await sleep(3000);
  $('[data-pftab="holdings"]').click(); await sleep(1500);
  const details = $$("#portfolioout details").find((d) => /reference list/i.test(d.textContent));
  details.querySelector("summary").click(); await sleep(500);
  await step("reference list starts on All", async () => {
    const all = $('[data-pfclass="all"]');
    if (!all) throw new Error("no All chip");
    all.click(); await sleep(400);
    return "listings=" + $$("#pfinstrumentrows .pfinstrow").length;
  });
  await step("search AAPL finds the listing", async () => {
    const field = $("#pfsearch");
    field.value = "AAPL"; field.dispatchEvent(new Event("input", { bubbles: true })); await sleep(600);
    const symbols = $$("#pfinstrumentrows .pfinstrow strong").map((e) => e.textContent.trim());
    if (symbols.indexOf("AAPL") < 0) throw new Error("AAPL missing: [" + symbols.join(",") + "]");
    return symbols.join(",");
  });
  await step("Use on the AAPL listing fills the form", async () => {
    const b = $("[data-pfinstrument]");
    if (!b) throw new Error("no Use button");
    b.click(); await sleep(500);
    const sym = ($("#pfhsym") || {}).value;
    if (sym !== "AAPL") throw new Error("#pfhsym=" + sym);
    return "symbol=" + sym + "; focus=" + (document.activeElement && document.activeElement.id);
  });
  await step("the two file inputs have readers bound", async () => {
    $('[data-pftab="data"]').click(); await sleep(1500);
    const prices = $("#pfpfile");
    const holdings = $("#pfhfile");
    return "prices reader=" + !!(prices && prices.onchange) + ", holdings reader=" + !!(holdings && holdings.onchange);
  });

  /* ---- lab: prefill then Open in the Business Calculator ---- */
  $('[data-pftab="screen"]').click(); await sleep(1500);
  $('[data-pltab="prefill"]').click(); await sleep(500);
  await step("#plrisk then #plopenincalc loads the calculator", async () => {
    const select = $("#plid");
    if (!select || select.options.length < 2) throw new Error("no tracked instrument");
    select.selectedIndex = 1;
    $("#plrisk").click(); await sleep(9000);
    const open = $("#plopenincalc");
    if (!open) throw new Error("no Open in the Business Calculator button: " + (txt("#plprefillout") || "").slice(0, 120));
    open.click(); await sleep(3000);
    const panel = $("#panel-calculator");
    const visible = panel && !panel.hidden;
    const filled = $$("#panel-calculator input, #panel-calculator .calcvalue, #panel-calculator [data-val]")
      .filter((el) => (el.value || el.textContent || "").trim()).length;
    if (!visible) throw new Error("calculator panel not shown");
    return "calculator shown, filled fields=" + filled;
  });

  return { results, errors: errors.slice(0, 12) };
})()
`;

async function main() {
  const profile = path.join(process.env.TEMP || ".", "sbw-cdp-audit3");
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    "--remote-debugging-port=" + PORT, "--user-data-dir=" + profile,
    "--window-size=1440,2400", "about:blank",
  ], { stdio: "ignore" });

  let target = null;
  for (let i = 0; i < 60; i += 1) {
    await sleep(300);
    try {
      const list = await getJSON("http://127.0.0.1:" + PORT + "/json/list");
      target = list.find((t) => t.type === "page");
      if (target) break;
    } catch (e) { /* not up */ }
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
      if (msg.error) reject(new Error(JSON.stringify(msg.error))); else resolve(msg.result);
    } else if (msg.method) events.push(msg);
  };
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  const send = (method, params) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params: params || {} }));
  });

  await send("Page.enable");
  await send("Runtime.enable");
  await send("Page.navigate", { url: BASE + "/#/portfolio" });
  await sleep(4500);

  const evaluated = await send("Runtime.evaluate", { expression: AUDIT, awaitPromise: true, returnByValue: true });
  if (evaluated.exceptionDetails) {
    console.error("AUDIT THREW: " + JSON.stringify(evaluated.exceptionDetails).slice(0, 2000));
  }
  const shot = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(OUT, "portfolio-buttons-audit-calculator.png"), Buffer.from(shot.data, "base64"));
  const pageExceptions = events.filter((e) => e.method === "Runtime.exceptionThrown")
    .map((e) => (e.params.exceptionDetails && e.params.exceptionDetails.text) || "").slice(0, 8);
  console.log(JSON.stringify({ report: evaluated.result ? evaluated.result.value : null, pageExceptions }, null, 2));
  ws.close();
  chrome.kill();
}

main().catch((error) => { console.error("AUDIT FAILED: " + (error && error.stack || error)); process.exit(1); });
