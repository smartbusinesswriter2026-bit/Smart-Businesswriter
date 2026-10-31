/*
 * Headless harness for the new "plan" panel.
 * Loads the real inline script from web/index.html into a minimal DOM shim,
 * points fetch at the running server, and drives the panel the way a student
 * would: fill the brief, build the plan, give a value, swap, confirm, run.
 */
const fs = require("fs");
const vm = require("vm");

const BASE = "http://127.0.0.1:8012";
const HTML = "D:/SMART BUSINESSWRITER/business_pipeline_v0.12/business_pipeline/web/index.html";

/* ---------- a very small DOM ---------- */
class El {
  constructor(id, tag) {
    this.id = id || "";
    this.tagName = (tag || "div").toUpperCase();
    this.value = "";
    this.textContent = "";
    this.innerHTML = "";
    this.dataset = {};
    this.className = "";
    this.disabled = false;
    this.onclick = null;
    this.children = [];
    this.attrs = {};
  }
  appendChild(c) { this.children.push(c); return c; }
  focus() {}
  setAttribute(k, v) { this.attrs[k] = v; }
  removeAttribute(k) { delete this.attrs[k]; }
  getAttribute(k) { return this.attrs[k]; }
  querySelector() { return null; }
  querySelectorAll(sel) { return sel === "[data-plan-act]" ? scanActions(this) : []; }
  insertAdjacentHTML() {}
  lastElementChild = null;
}

const byId = new Map();
function el(id, tag) { const e = new El(id, tag); byId.set(id, e); return e; }

/* the static markup the panel needs */
["plan-objective", "plan-brief", "plan-rubric", "plan-angle", "plan-case", "planout",
 "toasts", "modal", "drawer", "railtoggle", "chatbtn", "drawerclose", "locale",
 "pricingpill", "accountpill", "signuppill", "healthpill", "run", "micbtn", "chips",
 "panel-home", "panel-new", "panel-results", "panel-cases", "panel-case", "panel-data",
 "panel-refs", "panel-deliver", "panel-accounts", "panel-frames", "panel-assistant",
 "panel-plan", "panel-status"].forEach((id) => el(id));

/* regex scan of generated HTML for elements carrying a data-plan-act attribute */
const actionCache = new Map();
function scanActions(root) {
  const html = root.innerHTML || "";
  const out = [];
  const re = /<button\b([^>]*?)data-plan-act="([^"]+)"([^>]*)>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const attrs = (m[1] || "") + ' data-plan-act="' + m[2] + '" ' + (m[3] || "");
    let e = actionCache.get(m[0]);
    if (!e) {
      e = new El("", "button");
      const dre = /data-plan-([a-z-]+)="([^"]*)"/g;
      let d;
      while ((d = dre.exec(attrs)) !== null) {
        const key = "plan" + d[1].split("-").map((s) => s[0].toUpperCase() + s.slice(1)).join("");
        e.dataset[key] = d[2];
      }
      e.innerHTML = m[0];
      actionCache.set(m[0], e);
    }
    out.push(e);
  }
  return out;
}

const document = {
  title: "",
  body: { classList: { toggle: () => false, contains: () => false, add: () => {}, remove: () => {} } },
  getElementById: (id) => {
    if (byId.has(id)) return byId.get(id);
    // fall back to the rendered markup, the way a real DOM would
    const html = (byId.get("planout") || {}).innerHTML || "";
    const re = new RegExp("<[^>]*\\sid=\"" + id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\"");
    if (re.test(html)) { const e = new El(id, "input"); byId.set(id, e); return e; }
    return null;
  },
  querySelector: (sel) => {
    if (sel.startsWith("#")) return byId.get(sel.slice(1)) || null;
    return null;
  },
  querySelectorAll: (sel, root) => {
    if (sel === "[data-plan-act]") return scanActions(root || byId.get("planout"));
    return [];
  },
  createElement: (tag) => new El("", tag),
  addEventListener: () => {},
  removeEventListener: () => {},
};

const window = {
  location: { origin: BASE, hash: "#/plan" },
  addEventListener: () => {},
  localStorage: { getItem: () => null, setItem: () => {} },
};

/* ---------- load the real script ---------- */
const html = fs.readFileSync(HTML, "utf8");
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1] +
  "\n;globalThis.__probe = { state, buildPlan, postPlan, refreshPlan, confirmAndRunPlan," +
  " renderPlanOut, planRunHtml, planStatusWord, planInputValue, planFlatInputs, RENDERERS, PANELS };";
const sandbox = {
  document, window,
  location: window.location,
  history: { replaceState: () => {} },
  localStorage: window.localStorage,
  fetch: (path, opts) => fetch(path.startsWith("http") ? path : BASE + path, opts),
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  clearTimeout: (id) => clearTimeout(id),
  console, Promise, JSON, Math, Date, Intl, Object, Array, String, Number, Error,
  isNaN, parseInt, parseFloat, Boolean, RegExp, Set, Map, URL,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: "index.html.inline.js" });

const S = sandbox;
process.on("unhandledRejection", (e) => { console.error("(unhandled from boot():", (e && e.message) || e, ")"); });

/* ---------- drive it ---------- */
const log = (...a) => console.log(...a);

/* wait for the panel to stop showing the spinner */
async function settle(ms = 15000) {
  await new Promise((r) => setTimeout(r, 250));
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const h = byId.get("planout").innerHTML || "";
    if (!h.includes("class=\"spin\"")) return true;
    await new Promise((r) => setTimeout(r, 150));
  }
  return false;
}
async function click(el) { el.onclick(); await settle(); }

async function main() {
  // 1. the brief form
  byId.get("plan-objective").value = "Decide whether to proceed with the new plant investment.";
  byId.get("plan-brief").value =
    "Compute the NPV and IRR of the cash flows for the new plant investment.";
  byId.get("plan-rubric").value = "";
  byId.get("plan-angle").value = "The company should proceed because the new plant lowers unit cost.";

  // 2. build the plan
  await S.__probe.buildPlan();
  let plan = S.__probe.state.plan;
  log("=== after Build the plan ===");
  log("case id:", S.__probe.state.planCaseId);
  log("agent.enabled:", S.__probe.state.planAgent && S.__probe.state.planAgent.enabled);
  log("agent.reason:", (S.__probe.state.planAgent && S.__probe.state.planAgent.reason || "").slice(0, 90) + "...");
  log("model.enabled:", plan.model.enabled);
  log("rubric:", plan.rubric.map((r) => r.id + ":" + r.text));
  log("item_status:", JSON.stringify(plan.item_status));
  log("coverage:", JSON.stringify(plan.coverage));
  log("analyses:", plan.analyses.map((a) => a.id + "/" + a.method + "/" + a.status + "/missing=" + JSON.stringify(a.missing)));
  log("alternatives:", plan.analyses.map((a) => JSON.stringify(a.alternatives.map((x) => x.method))));
  log("questions:", plan.questions.map((q) => q.id + " | " + q.question + " | " + q.impact));
  log("structures:", plan.structures.map((s) => s.structure.name + " / " + s.structure.implementation_status));
  log("gates:", plan.gates.map((g) => g.gate + "=" + g.ok).join(", "));
  log("angle.note:", plan.angle.note.slice(0, 60) + "...");
  log("planout length:", byId.get("planout").innerHTML.length);
  log("has status word 'calculation, needs input':", byId.get("planout").innerHTML.includes("calculation, needs input"));
  log("has 'I know this value':", byId.get("planout").innerHTML.includes("I know this value"));
  log("has engine anomaly verbatim:",
    byId.get("planout").innerHTML.includes(plan.analyses[0].engine_check.anomalies[0]));

  // 3. give the missing value, exactly as the button does
  const acts = scanActions(byId.get("planout"));
  const know = acts.filter((a) => a.dataset.planAct === "know");
  const frag = byId.get("planout").innerHTML; const k = frag.indexOf("I know this value"); console.log("FRAG:", JSON.stringify(frag.slice(Math.max(0,k-320), k+40)));
  console.log("ALLBUTTONS:", scanActions(byId.get("planout")).length); console.log("HEAD:", JSON.stringify(byId.get("planout").innerHTML.slice(0,160)));
  log("=== value buttons found:", know.length, know.map((k) => k.dataset.planMethod + "/" + k.dataset.planInput).join(","));
  const field = document.getElementById(know[0].dataset.planField);
  field.value = "-1000, 400, 400, 400, 200";
  await click(know[0]);
  plan = S.__probe.state.plan;
  log("=== after 'I know this value' ===");
  log("state.planInputs:", JSON.stringify(S.__probe.state.planInputs));
  log("coverage:", JSON.stringify(plan.coverage));
  log("item_status:", JSON.stringify(plan.item_status));
  log("analysis status:", plan.analyses.map((a) => a.method + "=" + a.status).join(", "));
  log("engine_check:", JSON.stringify(plan.analyses[0].engine_check));

  // 4. swap
  const acts2 = scanActions(byId.get("planout"));
  const swap = acts2.filter((a) => a.dataset.planAct === "swap");
  console.log("AFTERCLICK HEAD:", JSON.stringify(byId.get("planout").innerHTML.slice(0,400)));
  log("=== swap buttons:", swap.map((s) => s.dataset.planRubric + "->" + s.dataset.planMethod).join(", "));
  if (swap.length) {
    await click(swap[0]);
    log("state.planSwaps:", JSON.stringify(S.__probe.state.planSwaps));
    log("after swap analyses:", S.__probe.state.plan.analyses.map((a) => a.rubric_id + ":" + a.method + ":" + a.status).join(", "));
    // undo the swap so the run below has the ready irr analysis
    const unswap = scanActions(byId.get("planout")).filter((a) => a.dataset.planAct === "unswap");
    log("unswap buttons:", unswap.length);
    if (unswap.length) { await click(unswap[0]); log("after undo swaps:", JSON.stringify(S.__probe.state.planSwaps)); }
  }

  // 5. confirm and run
  const acts3 = scanActions(byId.get("planout"));
  const confirm = acts3.filter((a) => a.dataset.planAct === "confirm");
  log("=== confirm buttons:", confirm.length);
  await click(confirm[0]);
  const out = byId.get("planout").innerHTML;
  log("planStored recorded_at:", S.__probe.state.planStored && S.__probe.state.planStored.recorded_at);
  log("planRuns:", S.__probe.state.planRuns.length);
  S.__probe.state.planRuns.forEach((r) => {
    const d = (r.session && r.session.delivery) || {};
    log("  run:", r.analysis.method, "->", d.status, "| tier:", d.tier,
        "| blocked:", JSON.stringify(d.blocked_reason), "| artifacts:", ((d.appendix || {}).artifacts || []).length,
        "| error:", r.error ? r.error.message : null);
  });
  log("out mentions 'stored on the case':", out.includes("stored on the case"));
  log("out mentions the recorded_at:", out.includes(S.__probe.state.planStored.recorded_at));
  log("out mentions delivery status 'delivered':", out.includes("delivered"));
  log("out contains a number computed by us? (artifacts count shown):", /Artifacts<\/dt><dd>\d+/.test(out));

  // 6. the no-ready path
  log("=== now the no-ready path ===");
  S.__probe.state.planInputs = {};
  await S.__probe.postPlan(S.__probe.state.planFields);
  const acts4 = scanActions(byId.get("planout"));
  log("coverage now:", JSON.stringify(S.__probe.state.plan.coverage));
  const confirm2 = acts4.filter((a) => a.dataset.planAct === "confirm");
  const before = S.__probe.state.planRuns.length;
  await click(confirm2[0]);
  log("runs added when nothing ready:", S.__probe.state.planRuns.length - before);
  const out2 = byId.get("planout").innerHTML;
  log("says nothing will run:", out2.includes("No analysis is ready, so nothing will be run"));
  const m = out2.match(/waiting on ([\w]+) inputs/);
  log("outstanding inputs named:", m ? m[1] : null);
  log("open_questions from server:", S.__probe.state.plan.coverage.open_questions);

  // 7. escaping: a hostile server string must not reach innerHTML raw
  log("=== escaping check ===");
  const hostile = JSON.parse(JSON.stringify(S.__probe.state.plan));
  const XSS = '<img src=x onerror="alert(1)"> & "quoted"';
  hostile.rubric[0].text = XSS;
  hostile.analyses[0].why = XSS;
  hostile.analyses[0].method_label = XSS;
  hostile.analyses[0].category = XSS;
  hostile.analyses[0].tier = XSS;
  hostile.analyses[0].will_produce = XSS;
  hostile.analyses[0].rubric_text = XSS;
  hostile.analyses[0].inputs[0].name = XSS;
  hostile.analyses[0].inputs[0].type = XSS;
  hostile.analyses[0].inputs[0].source = XSS;
  hostile.analyses[0].engine_check.anomalies = [XSS];
  hostile.questions[0].question = XSS;
  hostile.questions[0].detail = XSS;
  hostile.questions[0].impact = XSS;
  hostile.gates[0].detail = XSS;
  hostile.gates[0].gate = XSS;
  hostile.angle.note = XSS;
  hostile.notice = XSS;
  hostile.structures = [{ rubric_text: XSS, note: XSS, structure: { name: XSS, implementation_status: XSS } }];
  hostile.unsupported = [{ rubric_text: XSS, why: XSS }];
  hostile.analyses[0].alternatives = [{ method: XSS, method_label: XSS, category: XSS }];
  S.__probe.state.plan = hostile;
  S.__probe.renderPlanOut();
  const h = byId.get("planout").innerHTML;
  log("raw '<img' present:", h.includes("<img"));
  log("raw 'onerror=\"' present:", h.includes("onerror=\""));
  log("'onerror=' only as inert text:", h.includes("onerror=&quot;alert(1)&quot;"));
  log("escaped '&lt;img' present:", h.includes("&lt;img"));
  log("escaped quote present:", h.includes("&quot;"));
  log("hostile text still readable:", h.includes("&amp; &quot;quoted&quot;"));

  // 8. the em dash and the other status words
  log("=== status words ===");
  log("structure word:", JSON.stringify(S.__probe.planStatusWord("structure").text));
  log("computed word:", JSON.stringify(S.__probe.planStatusWord("computed").text));
  log("needs_input word:", JSON.stringify(S.__probe.planStatusWord("needs_input").text));
  log("uncovered word:", JSON.stringify(S.__probe.planStatusWord("uncovered").text));

  // 9. a blocked delivery, rendered the way a run is rendered
  log("=== blocked delivery ===");
  const blockedHtml = S.__probe.planRunHtml({
    analysis: { method_label: "npv", rubric_text: "Value the plant." },
    session: { delivery: { status: "blocked", tier: "T4", report: "", blocked_reason: "profiling anomalies: [\"missing required input 'rate'\"]", appendix: { events: [] } } },
    error: null
  });
  log("blocked html has 'blocked':", blockedHtml.includes("blocked"));
  log("blocked html has the reason:", blockedHtml.includes("missing required input 'rate'"));
  log("blocked html has tier T4:", blockedHtml.includes("T4"));
  log("blocked html shows 0 artifacts:", /Artifacts<\/dt><dd>0<\/dd>/.test(blockedHtml));
  log("blocked html has no report block:", !blockedHtml.includes("class=\"report\""));

  // 10. a brief that produces structures and an unsupported item
  log("=== structures scenario ===");
  S.__probe.state.plan = null;
  S.__probe.state.planInputs = {};
  S.__probe.state.planSwaps = {};
  S.__probe.state.planStored = null;
  S.__probe.state.planRuns = [];
  byId.get("plan-objective").value = "Decide whether to proceed with the new plant investment.";
  byId.get("plan-brief").value =
    "Evaluate the proposed new plant investment. Compute the NPV and IRR of the cash flows. " +
    "Recommend whether to proceed and explain the risks.";
  byId.get("plan-rubric").value = "";
  await S.__probe.buildPlan();
  await settle();
  const p2 = S.__probe.state.plan;
  log("rubric:", p2.rubric.map((r) => r.id + ":" + r.text.slice(0, 30)));
  log("item_status:", JSON.stringify(p2.item_status));
  log("structures:", p2.structures.map((s) => s.structure.name + " / " + s.structure.implementation_status));
  log("unsupported:", p2.unsupported.length, "questions:", p2.questions.length);
  const h2 = byId.get("planout").innerHTML;
  log("shows 'structure only':", h2.includes("structure only"));
  log("shows 'not covered yet':", h2.includes("not covered yet"));
  log("shows 'calculation, needs input':", h2.includes("calculation, needs input"));
  log("shows a framework name:", h2.includes(p2.structures[0].structure.name));
  log("shows implementation_status:", h2.includes(p2.structures[0].structure.implementation_status));
  log("shows the structure note:", h2.includes(p2.structures[0].note.slice(0, 40)));
  log("shows the question impact:", h2.includes(p2.questions[0].impact));
  log("shows the angle note:", h2.includes(p2.angle.note));
  log("shows the gate details:", p2.gates.every((g) => h2.includes(g.detail)));
  log("shows every rubric item verbatim:", p2.rubric.every((r) => h2.includes(r.text)));
  log("shows the coverage counts:", Object.keys(p2.coverage).every((k) => h2.includes(k)));
}

main().then(() => { console.log("\nHARNESS OK"); process.exit(0); })
  .catch((e) => { console.error("HARNESS FAILED:", e); process.exit(1); });

