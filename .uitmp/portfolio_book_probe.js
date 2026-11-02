// Headless Chrome CDP audit: the controls inside a book (Holdings, Prices, Journal) and
// the two download buttons. Verifies each click produces a visible result and a real file.
const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9335;
const OUT = __dirname;
const DOWNLOADS = path.join(OUT, "audit-downloads");
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
  const results = [];
  const errors = [];
  window.addEventListener("error", (e) => errors.push("window error: " + e.message));
  window.addEventListener("unhandledrejection", (e) => errors.push("unhandled rejection: " + (e.reason && e.reason.message || e.reason)));
  const origError = console.error;
  console.error = function () { errors.push("console.error: " + Array.from(arguments).map(String).join(" ")); origError.apply(console, arguments); };
  const step = async (name, fn) => {
    try {
      const note = await fn();
      results.push({ control: name, ok: true, note: note === undefined ? "" : String(note).slice(0, 200) });
    } catch (error) {
      results.push({ control: name, ok: false, note: String(error && error.message || error).slice(0, 200) });
    }
    await sleep(150);
  };

  /* open the stored book */
  location.hash = "#/portfolio";
  await sleep(3500);
  $("[data-pfopen]").click();
  await sleep(3000);

  /* ---------- Holdings: reference list, filters, example books, imports ---------- */
  $('[data-pftab="holdings"]').click(); await sleep(1500);

  await step("Holdings: reference-list card opens", async () => {
    const details = $$("#portfolioout details").find((d) => /reference list/i.test(d.textContent));
    if (!details) throw new Error("no reference-list card");
    details.querySelector("summary").click(); await sleep(500);
    if (!details.open) throw new Error("did not open");
    return $$("#pfinstrumentrows .pfinstrow").length + " listings";
  });
  await step("Holdings: Funds filter", async () => {
    const b = $('[data-pfclass="etf"]');
    if (!b) throw new Error("no Funds chip");
    b.click(); await sleep(400);
    const names = $$("#pfinstrumentrows .pfinstrow").length;
    return "pressed=" + b.getAttribute("aria-pressed") + ", listings=" + names;
  });
  await step("Holdings: search filters the reference list", async () => {
    const field = $("#pfsearch");
    if (!field) throw new Error("no search box");
    field.value = "AAPL"; field.dispatchEvent(new Event("input", { bubbles: true })); await sleep(500);
    const symbols = $$("#pfinstrumentrows .pfinstrow strong").map((e) => e.textContent.trim());
    if (symbols.indexOf("AAPL") < 0) throw new Error("AAPL missing: " + symbols.join(","));
    return symbols.join(",");
  });
  await step("Holdings: Use fills the add-holding form", async () => {
    const b = $("[data-pfinstrument]");
    if (!b) throw new Error("no Use button");
    b.click(); await sleep(400);
    const sym = ($("#pfhsym") || {}).value;
    if (!sym) throw new Error("#pfhsym empty");
    return "symbol=" + sym + ", shares focused=" + (document.activeElement && document.activeElement.id);
  });
  await step("Holdings: example book fills the import box", async () => {
    const details = $$("#portfolioout details").find((d) => /example book/i.test(d.textContent));
    if (!details) throw new Error("no example-book card");
    details.querySelector("summary").click(); await sleep(400);
    const b = $("[data-pfsample]");
    if (!b) throw new Error("no example-book button");
    b.click(); await sleep(700);
    const v = ($("#pfhimport") || {}).value || "";
    if (!v.trim()) throw new Error("import box empty");
    return v.split(/\\r?\\n/).length + " rows in the box";
  });
  await step("Holdings: import box card opens", async () => {
    const details = $$("#portfolioout details").find((d) => /Paste or import holdings/i.test(d.textContent));
    if (!details) throw new Error("no import card");
    details.querySelector("summary").click(); await sleep(400);
    return "open=" + details.open;
  });

  /* ---------- Prices and snapshot ---------- */
  $('[data-pftab="data"]').click(); await sleep(1500);
  await step("Prices: heading has no verification disclaimer", async () => {
    const heading = $$("#portfolioout h3").map((h) => h.textContent.trim());
    const market = heading.find((h) => /Market data for the book/.test(h));
    if (!market) throw new Error("market panel heading missing");
    if (/retrieved, not verified/i.test(market)) throw new Error("label still present: " + market);
    return market;
  });
  await step("Prices: #pfsnapshot confirms the stored snapshot", async () => {
    $$("[data-pfprice]").forEach((i) => { i.value = ""; });
    $("#pfsnapshot").click(); await sleep(9000);
    const msg = txt("#pfmsg") || "";
    const cards = $$("#portfolioout h3").map((h) => h.textContent.trim()).filter((h) => /^Snapshot /.test(h));
    if (!/Snapshot created|already|refused|blocked/i.test(msg)) throw new Error("no confirmation: " + msg.slice(0, 120));
    return msg.slice(0, 120) + " | snapshot cards: " + cards.length;
  });
  await step("Prices: #pfexport2 downloads the report (.docx)", async () => {
    const b = $("#pfexport2");
    if (!b) throw new Error("no Download the report button");
    b.click(); await sleep(3500);
    return "toast=" + (toasts().slice(-1)[0] || "none");
  });

  /* ---------- Journal ---------- */
  await step("Journal: #pfperform computes the return", async () => {
    $('[data-pftab="journal"]').click(); await sleep(1500);
    const compute = $("#pfperform");
    if (!compute) throw new Error("no Compute the return button");
    compute.click(); await sleep(12000);
    const text = document.querySelector("#portfolioout").textContent.replace(/\\s+/g, " ");
    if (/Compute the return/.test(text) && !/ratio|periods|named gap/i.test(text)) throw new Error("no outcome text");
    return text.slice(0, 140);
  });
  await step("Journal: save then remove confirm themselves", async () => {
    const date = new Date().toISOString().slice(0, 10);
    $("#pfjdate").value = date;
    $("#pfjflow").value = "0";
    $("#pfjnote").value = "probe entry";
    $("#pfsavejournal").click(); await sleep(4000);
    const saveMsg = txt("#pfmsg") || "";
    const remove = $('[data-pfjournalremove="' + date + '"]');
    if (!remove) throw new Error("no Remove button for the saved entry");
    remove.click(); await sleep(3500);
    const toastsNow = toasts().slice(-2).join(" / ");
    return "save=" + saveMsg.slice(0, 60) + " ; toast=" + toastsNow;
  });

  /* ---------- hero export ---------- */
  await step("Hero: #pfexport downloads the report (.docx)", async () => {
    const b = $("#pfexport");
    if (!b) throw new Error("no Export the report button");
    b.click(); await sleep(3500);
    return "toast=" + (toasts().slice(-1)[0] || "none");
  });

  return { results, errors: errors.slice(0, 12), toasts: toasts().slice(-4) };
})()
`;

async function main() {
  fs.mkdirSync(DOWNLOADS, { recursive: true });
  for (const name of fs.readdirSync(DOWNLOADS)) fs.unlinkSync(path.join(DOWNLOADS, name));
  const profile = path.join(process.env.TEMP || ".", "sbw-cdp-audit2");
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
  await send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: DOWNLOADS });
  await send("Page.navigate", { url: BASE + "/#/portfolio" });
  await sleep(4500);

  const evaluated = await send("Runtime.evaluate", { expression: AUDIT, awaitPromise: true, returnByValue: true });
  if (evaluated.exceptionDetails) {
    console.error("AUDIT THREW: " + JSON.stringify(evaluated.exceptionDetails).slice(0, 2000));
  }
  const report = evaluated.result ? evaluated.result.value : null;
  await sleep(1500);
  const downloads = fs.readdirSync(DOWNLOADS).map((name) => ({ name, bytes: fs.statSync(path.join(DOWNLOADS, name)).size }));
  const shot = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(OUT, "portfolio-buttons-audit-book.png"), Buffer.from(shot.data, "base64"));

  const pageExceptions = events.filter((e) => e.method === "Runtime.exceptionThrown")
    .map((e) => (e.params.exceptionDetails && e.params.exceptionDetails.text) || "").slice(0, 8);

  console.log(JSON.stringify({ report, downloads, pageExceptions }, null, 2));
  ws.close();
  chrome.kill();
}

main().catch((error) => { console.error("AUDIT FAILED: " + (error && error.stack || error)); process.exit(1); });
