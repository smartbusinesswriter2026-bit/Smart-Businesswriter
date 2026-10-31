/* hover a rail item in the collapsed strip and screenshot the tooltip */
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9500 + Math.floor(Math.random() * 300);
const url = process.argv[2];
const out = process.argv[3];
const selector = process.argv[4] || "#railsubjects .railitem";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = list.find((t) => t.type === "page" && t.webSocketDebuggerUrl);
      if (p) return p;
    } catch (e) {}
    await sleep(250);
  }
  throw new Error("no target");
}
function connect(u) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(u);
    let id = 0; const pending = new Map();
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && pending.has(m.id)) {
        const { resolve: r, reject: j } = pending.get(m.id); pending.delete(m.id);
        m.error ? j(new Error(JSON.stringify(m.error))) : r(m.result);
      }
    };
    ws.onerror = (e) => reject(new Error("ws " + e.message));
    ws.onopen = () => resolve({
      send: (method, params) => new Promise((res, rej) => {
        const mid = ++id; pending.set(mid, { resolve: res, reject: rej });
        ws.send(JSON.stringify({ id: mid, method, params: params || {} }));
      }),
      close: () => ws.close(),
    });
  });
}

(async () => {
  const profile = path.join("D:\\SMART BUSINESSWRITER\\.uitmp", "cdp-hover-" + PORT);
  const child = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
    "--force-device-scale-factor=1", "--window-size=1400,900", `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`, url], { stdio: "ignore" });
  try {
    const t = await target();
    const cdp = await connect(t.webSocketDebuggerUrl);
    await cdp.send("Page.enable"); await cdp.send("Runtime.enable");
    await sleep(2500);
    const box = await cdp.send("Runtime.evaluate", {
      expression: `(() => { const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return null; const b = el.getBoundingClientRect();
        return { x: Math.round(b.x + b.width/2), y: Math.round(b.y + b.height/2) }; })()`,
      returnByValue: true,
    });
    const p = box.result.value;
    console.log("hovering at", JSON.stringify(p));
    await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: p.x, y: p.y, buttons: 0 });
    await sleep(700);
    const tip = await cdp.send("Runtime.evaluate", {
      expression: `(() => { const t = document.querySelector("body > .railtip");
        if (!t) return null; const b = t.getBoundingClientRect(); const cs = getComputedStyle(t);
        return { text: t.textContent, x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width),
                 opacity: cs.opacity, position: cs.position }; })()`,
      returnByValue: true,
    });
    console.log("tooltip:", JSON.stringify(tip.result.value));
    const shot = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(out, Buffer.from(shot.data, "base64"));
    console.log("saved", out);
    cdp.close();
  } finally {
    child.kill(); await sleep(300);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
  }
  process.exit(0);
})().catch((e) => { console.error("FAILED", e.message); process.exit(1); });
