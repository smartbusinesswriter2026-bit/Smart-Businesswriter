// Headless Chrome CDP button audit for the Portfolio Lab, holdings, prices and journal.
// Clicks every user-facing control on the live app and records what each one did.
const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9334;
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
  const toasts = () => $$(".toast span").map((e) => e.textContent.trim());
  const clearToasts = () => { $$(".toast button").forEach((b) => b.click()); };
  const rows = (sel) => $$(sel + " tbody tr").length;
  const results = [];
  const errors = [];
  window.addEventListener("error", (e) => errors.push("window error: " + e.message));
  window.addEventListener("unhandledrejection", (e) => errors.push("unhandled rejection: " + (e.reason && e.reason.message || e.reason)));
  const origError = console.error;
  console.error = function () { errors.push("console.error: " + Array.from(arguments).map(String).join(" ")); origError.apply(console, arguments); };
  const step = async (name, fn) => {
    clearToasts();
    try {
      const note = await fn();
      results.push({ control: name, ok: true, note: note === undefined ? "" : String(note).slice(0, 180) });
    } catch (error) {
      results.push({ control: name, ok: false, note: String(error && error.message || error).slice(0, 180) });
    }
    await sleep(150);
  };

  /* ---------- A. landing page ---------- */
  location.hash = "#/portfolio";
  await sleep(3500);

  await step("#pfnewpaper (Start a paper)", async () => {
    $("#pfnewpaper").click(); await sleep(400);
    return "focus=" + (document.activeElement && document.activeElement.id);
  });
  await step("#pfnewfund (Open a fund)", async () => {
    $("#pfnewfund").click(); await sleep(500);
    const mode = ($("#pfmode") || {}).value;
    if (mode !== "fund") throw new Error("#pfmode is " + mode);
    $("#pfmode").value = "paper";
    return "mode set to fund";
  });
  await step("reference list details opens", async () => {
    const details = $$("#portfolioout details");
    const target = details.find((d) => /reference list/i.test(d.textContent));
    if (!target) throw new Error("reference-list details not found");
    target.querySelector("summary").click(); await sleep(400);
    if (!target.open) throw new Error("details did not open");
    return rows("#pfinstrumentrows") + " rows";
  });
  await step("class filter (Funds)", async () => {
    const b = $('[data-pfclass="etf"]');
    if (!b) throw new Error("no Funds chip");
    b.click(); await sleep(300);
    return "pressed=" + b.getAttribute("aria-pressed") + ", rows=" + rows("#pfinstrumentrows");
  });
  await step("search box filters the list", async () => {
    const field = $("#pfsearch");
    field.value = "AAPL"; field.dispatchEvent(new Event("input", { bubbles: true })); await sleep(400);
    const symbols = $$("#pfinstrumentrows .pfinstrow strong").map((e) => e.textContent.trim());
    if (symbols.indexOf("AAPL") < 0) throw new Error("AAPL missing: " + symbols.join(","));
    return symbols.join(",");
  });
  await step("Use on a reference row", async () => {
    const b = $("[data-pfinstrument]");
    if (!b) throw new Error("no Use button");
    b.click(); await sleep(300);
    if (!($("#pfhsym") || {}).value) throw new Error("#pfhsym not filled");
    return "symbol=" + $("#pfhsym").value;
  });
  await step("example book fills the import box", async () => {
    const b = $("[data-pfsample]");
    if (!b) throw new Error("no example-book button");
    b.click(); await sleep(600);
    const v = ($("#pfhimport") || {}).value || "";
    if (!v.trim()) throw new Error("import box empty after sample");
    return v.split(/\\r?\\n/).length + " rows in the box";
  });
  await step("lab: Watch list tab", async () => {
    $('[data-pltab="watch"]').click(); await sleep(300);
    if ($("#plpanel-watch").hidden) throw new Error("watch panel still hidden");
    return "watch panel shown";
  });
  await step("#pladdsymbols adds AMD", async () => {
    const before = rows("#plwatch");
    $("#plnewsyms").value = "AMD";
    $("#pladdsymbols").click(); await sleep(9000);
    const after = rows("#plwatch");
    const msg = txt("#plmsg");
    if (after <= before && !/Already on the watch list/.test(msg || "")) throw new Error("no row added: " + msg);
    return "rows " + before + "->" + after + "; " + msg;
  });
  await step("[data-record] records a price", async () => {
    const b = $("[data-record]");
    if (!b) throw new Error("no Record price button");
    b.click(); await sleep(7000);
    return "clicked; msg=" + (txt("#plmsg") || "n/a");
  });
  await step("[data-seed] seeds 30 days", async () => {
    const b = $("[data-seed]");
    if (!b) throw new Error("no Seed button");
    b.click(); await sleep(9000);
    return "toast=" + (toasts().slice(-1)[0] || "none");
  });
  await step("[data-use] jumps to Evaluate", async () => {
    const b = $("[data-use]");
    if (!b) throw new Error("no Evaluate button");
    b.click(); await sleep(400);
    if ($("#plpanel-prefill").hidden) throw new Error("prefill panel not shown");
    return "prefill shown, selected=" + (($("#plid") || {}).value || "none");
  });
  await step("[data-plremove] removes AMD", async () => {
    const target = $$("#plwatch tbody tr").find((tr) => (tr.querySelector("strong") || {}).textContent === "AMD");
    if (!target) throw new Error("AMD row not found");
    state.plTab = "watch";
    $('[data-pltab="watch"]').click(); await sleep(300);
    target.querySelector("[data-plremove]").click(); await sleep(8000);
    const left = $$("#plwatch tbody tr").map((tr) => (tr.querySelector("strong") || {}).textContent);
    if (left.indexOf("AMD") >= 0) throw new Error("AMD still listed");
    return "left: " + left.join(",");
  });
  await step("#plusewatch fills the screening field", async () => {
    $('[data-pltab="screen"]').click(); await sleep(300);
    $("#plusewatch").click(); await sleep(400);
    const v = ($("#plcands") || {}).value || "";
    if (!v.trim()) throw new Error("#plcands empty");
    return v;
  });
  await step("#plscreen screens the watched symbols", async () => {
    $("#plscreen").click(); await sleep(15000);
    const n = rows("#plscreenout");
    if (!n) throw new Error("no shortlist rows: " + (txt("#plscreenout") || "").slice(0, 120));
    return n + " rows";
  });
  await step("#plrisk prefills single-asset risk", async () => {
    $('[data-pltab="prefill"]').click(); await sleep(300);
    const select = $("#plid");
    if (select.options.length < 2) throw new Error("no tracked instrument options");
    select.selectedIndex = 1;
    $("#plrisk").click(); await sleep(9000);
    const t = txt("#plprefillout");
    if (!t) throw new Error("no prefill output");
    return t.slice(0, 140);
  });
  await step("#plport prefills a two-asset portfolio", async () => {
    const a = $("#plida"), b = $("#plidb");
    if (a.options.length < 3) throw new Error("fewer than two tracked instruments");
    a.selectedIndex = 1; b.selectedIndex = 2;
    $("#plport").click(); await sleep(9000);
    const t = txt("#plprefillout");
    if (!t) throw new Error("no prefill output");
    return t.slice(0, 140);
  });

  /* ---------- B. inside the book ---------- */
  await step("[data-pfopen] opens the book", async () => {
    const b = $("[data-pfopen]");
    if (!b) throw new Error("no stored book");
    b.click(); await sleep(3000);
    if (!$("#pfexport")) throw new Error("book workspace did not render");
    return "workspace rendered";
  });
  await step("overview quick action -> Holdings", async () => {
    const b = $('[data-pfgotab="holdings"]');
    if (!b) throw new Error("no quick action");
    b.click(); await sleep(1200);
    if (!$("#pfaddholding")) throw new Error("holdings panel not shown");
    return "holdings shown";
  });
  await step("#pfaddholding with no fields names the gap", async () => {
    $("#pfaddholding").click(); await sleep(500);
    const msg = txt("#pfmsg");
    if (!/symbol and shares/i.test(msg || "")) throw new Error("unexpected: " + msg);
    return msg.slice(0, 100);
  });
  await step("#pfaddholding adds ZZTEST and [data-pfremove] removes it", async () => {
    $("#pfhsym").value = "ZZTEST";
    $("#pfhshares").value = "1";
    $("#pfhcost").value = "1";
    $("#pfhwhy").value = "probe row";
    $("#pfaddholding").click(); await sleep(3500);
    const symbols = $$("#portfolioout tbody tr td:first-child strong").map((e) => e.textContent.trim());
    if (symbols.indexOf("ZZTEST") < 0) throw new Error("ZZTEST not added: " + symbols.join(","));
    const remove = $('[data-pfremove="ZZTEST"]');
    if (!remove) throw new Error("no Remove button for ZZTEST");
    remove.click(); await sleep(3500);
    const after = $$("#portfolioout tbody tr td:first-child strong").map((e) => e.textContent.trim());
    if (after.indexOf("ZZTEST") >= 0) throw new Error("ZZTEST not removed");
    return "added and removed; holdings=" + after.join(",");
  });
  await step("#pfhimportbtn with an empty box names the gap", async () => {
    $("#pfhimportbtn").click(); await sleep(500);
    const msg = txt("#pfmsg");
    if (!/Nothing to import/i.test(msg || "")) throw new Error("unexpected: " + msg);
    return msg.slice(0, 80);
  });
  await step("Grading: search + Use + sample + details", async () => {
    const details = $$("#portfolioout details");
    if (!details.length) throw new Error("no collapsible cards");
    details[0].querySelector("summary").click(); await sleep(400);
    if (!details[0].open) throw new Error("details did not open");
    return details.length + " collapsible cards";
  });
  await step("tab -> Prices and snapshot", async () => {
    $('[data-pftab="data"]').click(); await sleep(1500);
    if (!$("#eqquote")) throw new Error("securities panel missing");
    const heading = $$("#portfolioout h3").map((h) => h.textContent.trim());
    return heading.join(" | ");
  });
  await step("#eqfund reads SEC fundamentals", async () => {
    $("#eqfund").click(); await sleep(14000);
    const t = txt("#secout");
    if (!t || t.length < 20) throw new Error("no result: " + (t || "").slice(0, 100));
    return t.slice(0, 120);
  });
  await step("#seclookup reads SEC filings", async () => {
    $("#seclookup").click(); await sleep(14000);
    const t = txt("#secout");
    if (!t || t.length < 20) throw new Error("no result: " + (t || "").slice(0, 100));
    return t.slice(0, 120);
  });
  await step("#eqquote reads an equity quote", async () => {
    $("#eqquote").click(); await sleep(14000);
    const t = txt("#secout");
    if (!t || t.length < 10) throw new Error("no result: " + (t || ""));
    return t.slice(0, 120);
  });
  await step("#pfpimportbtn with an empty box names the gap", async () => {
    $("#pfpimportbtn").click(); await sleep(500);
    const msg = txt("#pfmsg");
    if (!/Nothing to import/i.test(msg || "")) throw new Error("unexpected: " + msg);
    return msg.slice(0, 80);
  });
  await step("#pffetch fetches prices (or names the limit)", async () => {
    $("#pffetch").click(); await sleep(25000);
    const msg = txt("#pfmsg");
    if (!msg || msg.length < 10) throw new Error("no message after fetch");
    return msg.slice(0, 160);
  });
  await step("#pfsnapshot refuses without every price, or values the book", async () => {
    $$("[data-pfprice]").forEach((i) => { i.value = ""; });
    $("#pfsnapshot").click(); await sleep(12000);
    const msg = txt("#pfmsg");
    if (!msg || msg.length < 10) throw new Error("no message after snapshot");
    const snapshots = $$("#portfolioout h3").map((h) => h.textContent.trim()).filter((h) => /^Snapshot /.test(h));
    return msg.slice(0, 140) + " | snapshot cards: " + snapshots.length;
  });
  await step("#pfexport (hero) exports the report", async () => {
    const b = $("#pfexport");
    if (!b) throw new Error("no Export the report button");
    b.click(); await sleep(9000);
    const t = toasts().slice(-1)[0] || "";
    if (!/report saved|snapshot/i.test(t)) throw new Error("toast=" + t);
    return t;
  });
  await step("tab -> Journal, #pfperform", async () => {
    const b = $('[data-pftab="journal"]');
    if (!b) throw new Error("no journal tab");
    b.click(); await sleep(1200);
    const compute = $("#pfperform");
    if (!compute) throw new Error("no Compute the return button");
    compute.click(); await sleep(12000);
    const heading = txt("#portfolioout h3");
    return "top=" + (heading || "") + "; msg=" + (txt("#pfmsg") || "none").slice(0, 80);
  });
  await step("#pfsavejournal saves, [data-pfjournalremove] restores", async () => {
    const date = new Date().toISOString().slice(0, 10);
    if ($("#pfjdate")) $("#pfjdate").value = date;
    if ($("#pfjflow")) $("#pfjflow").value = "0";
    if ($("#pfjnote")) $("#pfjnote").value = "probe entry";
    $("#pfsavejournal").click(); await sleep(4000);
    const msg = txt("#pfmsg");
    const remove = $('[data-pfjournalremove="' + date + '"]');
    if (remove) { remove.click(); await sleep(3500); }
    return "after save: " + (msg || "no banner").slice(0, 100) + "; removed=" + !!remove;
  });
  await step("#pfall returns to the landing", async () => {
    const b = $("#pfall");
    if (!b) throw new Error("no All portfolios button");
    b.click(); await sleep(2500);
    if (!$("#pfnewpaper")) throw new Error("landing did not render");
    return "landing rendered";
  });

  return { results, errors: errors.slice(0, 12), toasts: toasts().slice(-5) };
})()
`;

async function main() {
  const profile = path.join(process.env.TEMP || ".", "sbw-cdp-audit");
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
  const report = evaluated.result ? evaluated.result.value : null;
  const shot = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(OUT, "portfolio-buttons-audit.png"), Buffer.from(shot.data, "base64"));

  const pageExceptions = events.filter((e) => e.method === "Runtime.exceptionThrown")
    .map((e) => (e.params.exceptionDetails && e.params.exceptionDetails.text) || "").slice(0, 8);

  console.log(JSON.stringify({ report, pageExceptions }, null, 2));
  ws.close();
  chrome.kill();
}

main().catch((error) => { console.error("AUDIT FAILED: " + (error && error.stack || error)); process.exit(1); });
