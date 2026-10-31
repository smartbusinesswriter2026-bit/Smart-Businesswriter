/*
 * Tiny CDP harness: open a URL in headless Chrome, optionally click the rail
 * toggle, measure the rail geometry, and save a screenshot.
 * usage: node shot.js <url> <outPng> <open|closed> [measureExprFile]
 */
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9223 + Math.floor(Math.random() * 300);

const url = process.argv[2];
const out = process.argv[3];
const state = process.argv[4] || "closed";
const measureFile = process.argv[5];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getTarget() {
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await res.json();
      const page = list.find((t) => t.type === "page" && t.webSocketDebuggerUrl);
      if (page) return page;
    } catch (e) { /* not up yet */ }
    await sleep(250);
  }
  throw new Error("no devtools target");
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let id = 0;
    const pending = new Map();
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { resolve: res, reject: rej } = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
      }
    };
    ws.onerror = (e) => reject(new Error("ws error " + e.message));
    ws.onopen = () => resolve({
      send(method, params) {
        const mid = ++id;
        return new Promise((res, rej) => {
          pending.set(mid, { resolve: res, reject: rej });
          ws.send(JSON.stringify({ id: mid, method, params: params || {} }));
        });
      },
      close() { ws.close(); },
    });
  });
}

(async () => {
  const profile = path.join("D:\\SMART BUSINESSWRITER\\.uitmp", "cdp-profile-" + PORT);
  const child = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
    "--no-default-browser-check", "--force-device-scale-factor=1",
    "--window-size=" + (process.env.WIN || "1400,900"), `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`, url,
  ], { stdio: "ignore" });

  try {
    const target = await getTarget();
    const cdp = await connect(target.webSocketDebuggerUrl);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await sleep(2500);

    if (state === "open") {
      await cdp.send("Runtime.evaluate", {
        expression: `document.getElementById("railtoggle").click()`,
        awaitPromise: false,
      });
      await sleep(900);
    }

    if (measureFile) {
      const expr = fs.readFileSync(measureFile, "utf8");
      const r = await cdp.send("Runtime.evaluate", { expression: expr, returnByValue: true });
      console.log(JSON.stringify(r.result.value, null, 1));
    }

    const shot = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(out, Buffer.from(shot.data, "base64"));
    console.log("saved", out);
    cdp.close();
  } finally {
    child.kill();
    await sleep(400);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
  }
  process.exit(0);
})().catch((e) => { console.error("FAILED", e.message); process.exit(1); });
