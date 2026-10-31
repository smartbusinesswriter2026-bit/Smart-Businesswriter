/* click the rail toggle and capture the button in each state */
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9700 + Math.floor(Math.random() * 200);
const url = process.argv[2];
const out = process.argv[3];

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

const probe = `(() => {
  var t = document.getElementById("railtoggle");
  var cs = getComputedStyle(t);
  var b = t.getBoundingClientRect();
  var expand = t.querySelector(".rt-expand"), collapse = t.querySelector(".rt-collapse");
  return {
    bodyClass: document.body.className,
    color: cs.color, background: cs.backgroundColor, outline: cs.outline,
    focused: document.activeElement === t, focusVisible: t.matches(":focus-visible"),
    hoverRule: t.matches(":hover"),
    box: { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) },
    expand: { shown: getComputedStyle(expand).display, w: Math.round(expand.getBoundingClientRect().width) },
    collapse: { shown: getComputedStyle(collapse).display, w: Math.round(collapse.getBoundingClientRect().width) }
  };
})()`;

(async () => {
  const profile = path.join("D:\\SMART BUSINESSWRITER\\.uitmp", "cdp-click-" + PORT);
  const child = spawn(CHROME, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
    "--force-device-scale-factor=1", "--window-size=1400,900", `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`, url], { stdio: "ignore" });
  try {
    const t = await target();
    const cdp = await connect(t.webSocketDebuggerUrl);
    await cdp.send("Page.enable"); await cdp.send("Runtime.enable");
    await sleep(2500);

    const box = await cdp.send("Runtime.evaluate", {
      expression: `(() => { const b = document.getElementById("railtoggle").getBoundingClientRect();
        return { x: Math.round(b.x + b.width/2), y: Math.round(b.y + b.height/2) }; })()`,
      returnByValue: true,
    });
    const p = box.result.value;
    console.log("toggle at", JSON.stringify(p));

    // hover the hamburger
    await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: p.x, y: p.y, buttons: 0 });
    await sleep(400);
    console.log("hovering   :", JSON.stringify((await cdp.send("Runtime.evaluate", { expression: probe, returnByValue: true })).result.value));
    await cdp.send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 56, width: 300, height: 120, scale: 2 } })
      .then((s) => fs.writeFileSync(out.replace(/\.png$/, "-1-hover.png"), Buffer.from(s.data, "base64")));

    // click it
    await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 1, buttons: 1 });
    await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x, y: p.y, button: "left", clickCount: 1, buttons: 0 });
    await sleep(700);
    console.log("after click:", JSON.stringify((await cdp.send("Runtime.evaluate", { expression: probe, returnByValue: true })).result.value));
    await cdp.send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 56, width: 300, height: 120, scale: 2 } })
      .then((s) => fs.writeFileSync(out.replace(/\.png$/, "-2-clicked.png"), Buffer.from(s.data, "base64")));

    // now hover the chevron, where the button moved to
    const nb = await cdp.send("Runtime.evaluate", {
      expression: `(() => { const b = document.getElementById("railtoggle").getBoundingClientRect();
        return { x: Math.round(b.x + b.width/2), y: Math.round(b.y + b.height/2) }; })()`,
      returnByValue: true,
    });
    const q = nb.result.value;
    await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: q.x, y: q.y, buttons: 0 });
    await sleep(400);
    console.log("hover chev :", JSON.stringify((await cdp.send("Runtime.evaluate", { expression: probe, returnByValue: true })).result.value));
    await cdp.send("Page.captureScreenshot", { format: "png", clip: { x: 180, y: 56, width: 120, height: 120, scale: 2 } })
      .then((s) => fs.writeFileSync(out.replace(/\.png$/, "-3-chevron-hover.png"), Buffer.from(s.data, "base64")));

    cdp.close();
  } finally {
    child.kill(); await sleep(300);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
  }
  process.exit(0);
})().catch((e) => { console.error("FAILED", e.message); process.exit(1); });
