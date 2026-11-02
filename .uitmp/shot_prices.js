const http = require("http");
const fs = require("fs");
const { spawn } = require("child_process");
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9338;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJSON = (url) => new Promise((res, rej) => { http.get(url, (r) => { let b = ""; r.on("data", (d) => b += d); r.on("end", () => { try { res(JSON.parse(b)); } catch (e) { rej(e); } }); }).on("error", rej); });
(async () => {
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--window-size=1440,2200", "--remote-debugging-port=" + PORT, "--user-data-dir=" + process.env.TEMP + "\\sbw-cdp-shot", "about:blank"], { stdio: "ignore" });
  let t = null;
  for (let i = 0; i < 60; i++) { await sleep(300); try { const l = await getJSON("http://127.0.0.1:" + PORT + "/json/list"); t = l.find((x) => x.type === "page"); if (t) break; } catch (e) {} }
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  let id = 1; const pending = new Map();
  ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result); } };
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  const send = (method, params) => new Promise((res, rej) => { const i = id++; pending.set(i, { resolve: res, reject: rej }); ws.send(JSON.stringify({ id: i, method, params: params || {} })); });
  await send("Page.enable"); await send("Runtime.enable");
  await send("Page.navigate", { url: "http://127.0.0.1:8000/#/portfolio" }); await sleep(4500);
  const ev = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result.value;
  await ev(`(async () => { document.querySelector("[data-pfopen]").click(); await new Promise(r => setTimeout(r, 3000)); document.querySelector('[data-pftab="data"]').click(); await new Promise(r => setTimeout(r, 1500)); document.querySelector("[data-pftab]").scrollIntoView({block:"start"}); return true; })()`);
  await sleep(800);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync("portfolio-prices-tab-heading.png", Buffer.from(shot.data, "base64"));
  console.log("saved");
  ws.close(); chrome.kill();
})().catch((e) => { console.error(e); process.exit(1); });
