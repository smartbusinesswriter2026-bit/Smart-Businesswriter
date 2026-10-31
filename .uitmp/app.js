"use strict";
const MARK = "__MARK__";

/* ---------- tiny helpers ---------- */
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const esc = (v) => String(v === null || v === undefined ? "" : v)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const txt = (v) => (v === null || v === undefined || v === "") ? "not recorded" : String(v);

async function api(path, opts) {
  const res = await fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts || {}));
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok) {
    const error = new Error((data && data.error) || ("The server returned HTTP " + res.status + "."));
    error.status = res.status;
    error.payload = data;
    throw error;
  }
  return data;
}
const post = (path, body) => api(path, { method: "POST", body: JSON.stringify(body) });

/* ---------- state ---------- */
const state = {
  presets: {}, methods: [], currencies: [], session: null, delivery: null,
  cases: [], caseId: null, caseView: null, caseBundle: null,
  runs: [], runRecords: [], runIndex: null, tab: "documents",
  ingest: null, ingestB64: null, mappedInputs: null,
  ref: null, assist: null, health: null, locale: "en-US",
  versions: [], signoffs: [], compare: null,
  proposals: { facts: [], alternatives: [], critique: [] }
};
const PANELS = ["home", "new", "results", "case", "data", "refs", "deliver", "accounts", "frames", "assistant", "status"];
const CASE_TABS = [["documents", "Documents"], ["data", "Data"], ["arguments", "Arguments"],
                   ["runs", "Runs"], ["versions", "Versions"], ["signoff", "Sign-off"]];

/* ---------- language ---------- */
const LOCALES = {
  "en-US": { date: "en-US", label: "English (US)" },
  "en-GB": { date: "en-GB", label: "English (UK)" },
  "en-CA": { date: "en-CA", label: "English (Canada)" },
  "en-AU": { date: "en-AU", label: "English (Australia)" }
};
function fmtDate(value) {
  if (!value) return "not recorded";
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  return new Intl.DateTimeFormat(LOCALES[state.locale].date, { dateStyle: "medium", timeStyle: "short" }).format(d);
}

/* ---------- chrome ---------- */
function toast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = "<span>" + esc(message) + "</span>";
  const close = document.createElement("button");
  close.type = "button"; close.textContent = "x"; close.setAttribute("aria-label", "Dismiss");
  close.onclick = () => el.remove();
  el.appendChild(close);
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 6000);
}
function banner(kind, title, bodyHtml) {
  return '<div class="banner ' + kind + '"><strong>' + esc(title) + "</strong>" + bodyHtml + "</div>";
}
function errorBanner(error) {
  return banner("blocked", "The server refused this request", "<div>" + esc(error.message || String(error)) + "</div>");
}
function loading(label) { return '<p class="muted"><span class="spin"></span> ' + esc(label) + "</p>"; }
function kv(pairs) {
  return "<dl class=\"kv\">" + pairs.map(([k, v]) => "<dt>" + esc(k) + "</dt><dd>" + esc(txt(v)) + "</dd>").join("") + "</dl>";
}

/* ---------- router ---------- */
function show(id) {
  PANELS.forEach((p) => { const el = document.getElementById("panel-" + p); if (el) el.hidden = p !== id; });
  $$(".railitem").forEach((a) => {
    if (a.dataset.panel === id) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  document.title = "Smart BusinessWriter - " + id;
  const render = RENDERERS[id];
  if (render) render();
  if (location.hash !== "#/" + id) history.replaceState(null, "", "#/" + id);
}
function route() {
  const id = (location.hash || "#/home").replace("#/", "") || "home";
  show(PANELS.includes(id) ? id : "home");
}

/* ---------- panels ---------- */
const RENDERERS = {};

/* ---------- home: the case shelf ---------- */
RENDERERS.home = function () {
  const p = $("#panel-home");
  const chips = Object.keys(state.presets);
  const preferred = ["npv", "irr", "breakeven", "descriptive_stats", "ratio_analysis", "wacc", "dcf_valuation", "unit_economics"];
  const shown = preferred.filter((id) => chips.includes(id)).concat(chips.filter((id) => !preferred.includes(id)));
  p.innerHTML =
    '<div class="hero">' +
      '<img src="' + MARK + '" alt="">' +
      '<h1>Smart Business <span class="g">Writer</span></h1>' +
      '<p class="tagline">BUSINESS | ACCOUNTING | ECONOMICS | FINANCE</p>' +
      '<p class="sub" id="hero-sub">Every figure computed by code, never by the model.</p>' +
    "</div>" +
    '<div class="card"><div class="row" style="justify-content:space-between"><h2 style="margin:0">Your cases</h2>' +
      '<button class="btn sm" id="backup">Back up all cases</button></div>' +
      '<p class="sub">A case is the unit of work: it holds the case study, the spreadsheet, the argument and every run made from them.</p>' +
      '<div id="shelf">' + loading("Reading the case store") + "</div></div>" +
    '<div class="card"><h3>Start a new case</h3>' +
      '<div class="row"><input type="text" id="newcasetitle" placeholder="Name this case" size="40">' +
      '<button class="btn primary" id="newcase">Create case</button>' +
      '<span class="grow"></span><span class="muted">The case exists before anything is run.</span></div></div>' +
    '<div class="card"><h3>Run an analysis</h3>' +
      '<label class="visually-hidden" for="objective">What would you like to work on?</label>' +
      '<textarea id="objective" placeholder="What would you like to work on..."></textarea>' +
      '<div class="actionrow">' +
        '<button class="btn primary" id="run">Run</button>' +
        '<label class="visually-hidden" for="preset">Preset</label><select id="preset"><option value="">No preset</option>' +
          chips.map((id) => "<option value=\"" + esc(id) + "\">" + esc(id) + "</option>").join("") +
        "</select>" +
        '<label class="visually-hidden" for="method">Method</label><select id="method"><option value="">Method</option>' +
          state.methods.map((m) => "<option value=\"" + esc(m.method_id) + "\">" + esc(m.method_id) + "</option>").join("") +
        "</select>" +
        '<label class="visually-hidden" for="currency">Currency</label><select id="currency"><option value="">Currency</option>' +
          state.currencies.map((c) => "<option value=\"" + esc(c.code) + "\">" + esc(c.code) + " - " + esc(c.name) + "</option>").join("") +
        "</select>" +
        '<span class="grow"></span>' +
        '<span class="muted">The run is recorded in a case of its own, and stays in the case you already opened.</span>' +
      "</div></div>" +
    '<div class="chips">' +
      shown.slice(0, 10).map((id) => {
        const pr = state.presets[id] || {};
        const label = pr.method || id;
        return '<button class="chip" data-preset="' + esc(id) + '" title="' + esc(id) + " - " + esc(txt(pr.tier)) +
          '"><span class="dot"></span>' + esc(label) + "</button>";
      }).join("") +
    "</div>" +
    '<div class="card" style="margin-top:14px">' +
      '<div class="row" style="justify-content:space-between"><h3 style="margin:0">Examples <span class="example">example</span></h3>' +
      '<span class="muted">From the owner\'s INITIAL TEST problem set (1.docx). Each one fills the objective; the inputs stay yours to confirm.</span></div>' +
      '<div class="row" style="gap:8px;margin-top:8px">' +
        '<button class="btn sm" data-example="npv">NPV of a 4-year project</button>' +
        '<button class="btn sm" data-example="breakeven">Break-even (TC = 500 + 20Q, price 30)</button>' +
        '<button class="btn sm" data-example="descriptive">Describe exam scores</button>' +
      "</div></div>";
  $("#run").onclick = startFromHome;
  $("#newcase").onclick = createCase;
  $("#backup").onclick = backupCases;
  $("#preset").onchange = () => {
    const id = $("#preset").value; const pr = state.presets[id];
    if (pr) { $("#method").value = pr.method || ""; if (pr.currency) $("#currency").value = pr.currency; }
  };
  $$(".chip").forEach((c) => { c.onclick = () => {
    const id = c.dataset.preset; const pr = state.presets[id];
    if (pr) { $("#preset").value = id; $("#method").value = pr.method || ""; if (pr.currency) $("#currency").value = pr.currency; }
  }; });
  $$("[data-example]").forEach((b) => { b.onclick = () => {
    const id = b.dataset.example; const pr = state.presets[id];
    $("#objective").value = "Example (from the owner's INITIAL TEST problem set): " + b.textContent;
    if (pr) { $("#preset").value = id; $("#method").value = pr.method || ""; if (pr.currency) $("#currency").value = pr.currency; }
  }; });
  loadShelf("shelf");
};

async function loadShelf(boxId) {
  const box = $("#" + boxId);
  if (!box) return;
  box.innerHTML = loading("Reading the case store");
  try {
    const d = await api("/api/cases");
    state.cases = d.cases || [];
    if (!state.cases.length) {
      box.innerHTML = '<div class="empty"><h3>No cases yet</h3>' +
        "<p>Name a case above and start there. The case study, the spreadsheet, the argument and every run live in it.</p></div>";
      return;
    }
    let html = '<div class="tablewrap"><table><caption>Your cases</caption><thead><tr>' +
      "<th>Case</th><th>Method</th><th>Runs</th><th>Created</th><th></th></tr></thead><tbody>";
    state.cases.forEach((c) => {
      html += "<tr" + (c.corrupt ? ' class="row-warn"' : "") + "><td>" + esc(txt(c.title)) +
        (c.corrupt ? ' <span class="badge warn">corrupt</span>' : "") +
        (c.shell ? ' <span class="badge">no run yet</span>' : "") + "</td><td>" + esc(txt(c.method)) +
        "</td><td>" + (c.runs === undefined ? "not recorded" : esc(String(c.runs))) +
        "</td><td>" + esc(txt(c.created_at)) + "</td>" +
        '<td><button class="btn sm" data-open="' + esc(c.id) + '">Open</button></td></tr>';
    });
    html += "</tbody></table></div>";
    box.innerHTML = html;
    $$("[data-open]", box).forEach((b) => { b.onclick = () => openCase(b.dataset.open); });
  } catch (e) { box.innerHTML = errorBanner(e); }
}

async function createCase() {
  const title = $("#newcasetitle").value.trim();
  if (!title) { toast("Name the case first."); return; }
  try {
    const created = await post("/api/cases/new", { title: title });
    toast("Case " + created.id + " created.");
    $("#newcasetitle").value = "";
    await openCase(created.id);
  } catch (e) { toast(e.message); }
}

async function ensureCase(title) {
  if (state.caseId) return state.caseId;
  const created = await post("/api/cases/new", { title: title || "Untitled case" });
  state.caseId = created.id;
  rememberCase(created.id);
  return created.id;
}
function rememberCase(id) {
  state.caseId = id;
  try { localStorage.setItem("bp-case", id); } catch (e) {}
}

async function backupCases() {
  try {
    const r = await post("/api/cases/backup", {});
    toast("Backup written to " + (r.path || "the state directory") + ".");
  } catch (e) { toast(e.message); }
}

/* ---------- the open case ---------- */
RENDERERS.case = function () { renderCase(); };

async function openCase(id) {
  if (!id) { toast("Open a case from the shelf."); return; }
  rememberCase(id);
  state.caseView = null;
  state.runIndex = null;
  show("case");
  const p = $("#panel-case");
  p.innerHTML = '<div class="card">' + loading("Reading the case") + "</div>";
  try {
    const [view, bundle, versions, signoffs, runs] = await Promise.all([
      api("/api/cases/" + id + "/workspace"),
      api("/api/cases/" + id),
      api("/api/cases/" + id + "/versions"),
      api("/api/cases/" + id + "/signoff"),
      api("/api/cases/" + id + "/runs")
    ]);
    state.caseView = view;
    state.caseBundle = bundle;
    state.versions = versions.versions || [];
    state.signoffs = signoffs.signoffs || [];
    state.runs = view.runs || [];
    state.runRecords = runs.runs || [];
    state.runIndex = state.runs.length ? state.runs.length - 1 : null;
    renderCase();
  } catch (e) { p.innerHTML = '<div class="card">' + errorBanner(e) + "</div>"; }
}

function renderCase() {
  const view = state.caseView;
  const box = $("#panel-case");
  if (!view) {
    box.innerHTML = '<div class="card"><div class="empty"><h3>No case open</h3>' +
      "<p>A case holds the case study, the spreadsheet, the argument and every run. Open one from the shelf.</p>" +
      '<button class="btn primary" id="gotoshelf">Your cases</button></div></div>';
    const g = $("#gotoshelf"); if (g) g.onclick = () => show("home");
    return;
  }
  let html = '<div class="card">' +
    '<div class="row" style="justify-content:space-between"><h2 style="margin:0">' + esc(txt(view.title)) + "</h2>" +
    '<span class="badge">' + (view.shell ? "no run yet" : esc(txt(view.tier))) + "</span></div>" +
    '<div class="row"><span class="muted">Case ' + esc(txt(view.id)) + " - " + esc(txt(view.created_at)) +
    (view.shell ? " - nothing run yet" : " - " + esc(txt(view.method))) + "</span>" +
    '<span class="grow"></span><button class="btn sm danger" id="delcase">Delete case</button></div>' +
    '<div class="tabs" role="tablist">' +
      CASE_TABS.map(([key, label]) =>
        '<button class="tab" role="tab" data-tab="' + key + '" aria-selected="' + (state.tab === key) + '">' + label + "</button>").join("") +
    "</div></div>";
  html += '<div class="card">' + caseTabHtml() + "</div>";
  box.innerHTML = html;
  $$("[data-tab]").forEach((t) => { t.onclick = () => { state.tab = t.dataset.tab; renderCase(); }; });
  const del = $("#delcase"); if (del) del.onclick = () => confirmDelete(view.id);
  wireCaseTab();
}

function caseTabHtml() {
  if (state.tab === "documents") return documentsHtml();
  if (state.tab === "data") return dataTabHtml();
  if (state.tab === "arguments") return argumentsHtml();
  if (state.tab === "runs") return runsHtml();
  if (state.tab === "versions") return versionsHtml();
  return signoffHtml();
}

/* -- documents -- */
function documentsHtml() {
  const documents = (state.caseView && state.caseView.documents) || [];
  let html = "<h3>Documents</h3>" +
    '<p class="sub">The case study and any note you attach to this case. The text is read on this machine; ' +
    "nothing is sent anywhere unless you ask the assistant to, and then only after you agree.</p>" +
    '<div class="row"><input type="file" id="docfile" accept=".txt,.md,.pdf,.docx,.doc,.csv">' +
    '<button class="btn primary" id="attachdoc">Attach to this case</button>' +
    '<span class="grow"></span><span class="muted">PDF and Word files are read for their text; a scan is read by the OCR engine on this machine, if one is installed.</span></div>';
  if (!documents.length) {
    html += '<div class="empty"><h3>No document attached yet</h3><p>Attach the case study so the case keeps the evidence behind it.</p></div>';
    return html;
  }
  html += '<div class="tablewrap" style="margin-top:12px"><table><caption>Attached documents</caption><thead><tr>' +
    "<th>File</th><th>Kind</th><th>Bytes</th><th>Provenance</th><th>Text</th><th>Attached</th></tr></thead><tbody>";
  documents.forEach((d) => {
    html += "<tr><td>" + esc(txt(d.filename)) + "</td><td>" + esc(txt(d.kind)) + "</td><td>" + esc(txt(d.bytes)) +
      "</td><td>" + esc(txt(d.provenance)) + "</td><td>" + esc(txt(d.text_chars)) + " characters</td><td>" +
      esc(txt(d.attached_at)) + "</td></tr>";
  });
  html += "</tbody></table></div>";
  documents.forEach((d) => {
    if (!d.warnings || !d.warnings.length) return;
    html += banner("limit", "Warnings for " + txt(d.filename),
      "<ul>" + d.warnings.map((w) => "<li>" + esc(w) + "</li>").join("") + "</ul>");
  });
  return html;
}

async function attachDocument(file) {
  const caseId = state.caseId;
  if (!caseId) { toast("Open a case first."); return; }
  const bytes = new Uint8Array(await file.arrayBuffer());
  /* the product route accepts a body of about 100 KB, so the file goes up in
     pieces: 48 KB of raw bytes is 64 KB of base64, which leaves room for the
     JSON around it. */
  const CHUNK = 48 * 1024;
  const total = Math.max(1, Math.ceil(bytes.length / CHUNK));
  for (let index = 0; index < total; index++) {
    const slice = bytes.slice(index * CHUNK, Math.min(bytes.length, (index + 1) * CHUNK));
    let binary = ""; for (let i = 0; i < slice.length; i++) binary += String.fromCharCode(slice[i]);
    await post("/api/cases/" + caseId + "/documents", {
      filename: file.name,
      chunk_index: index,
      total_chunks: total,
      data: btoa(binary)
    });
  }
  toast(file.name + " attached.");
  await openCase(caseId);
}

/* -- data -- */
function dataTabHtml() {
  const files = (state.caseView && state.caseView.data_files) || [];
  let html = "<h3>Data files</h3>" +
    '<p class="sub">Read a CSV/TSV or XLSX file into a typed table with a provenance pointer, then attach it to this ' +
    "case or use its columns as the inputs of a run. The table is attached exactly as it was read; a table too large " +
    "for the route is refused with a reason rather than trimmed.</p>" +
    '<div class="row"><input type="file" id="ingfile" accept=".csv,.tsv,.txt,.xlsx,.xls">' +
    '<button class="btn primary" id="ingestbtn">Ingest file</button>' +
    '<label class="field" style="margin:0">Sheet <input type="text" id="ingsheet" placeholder="name or number"></label>' +
    '<label class="field" style="margin:0">Merged cells <select id="ingmerged"><option value="refuse">refuse</option>' +
    '<option value="top_left">top_left</option></select></label></div>';
  if (files.length) {
    html += '<div class="tablewrap" style="margin-top:12px"><table><caption>Attached to this case</caption><thead><tr>' +
      "<th>File</th><th>Bytes</th><th>SHA-256</th><th>Attached</th></tr></thead><tbody>" +
      files.map((f) => "<tr><td>" + esc(txt(f.filename)) + "</td><td>" + esc(txt(f.bytes)) + "</td><td>" +
        esc(txt(f.sha256)) + "</td><td>" + esc(txt(f.attached_at)) + "</td></tr>").join("") +
      "</tbody></table></div>";
  }
  html += '<div id="ingout"></div>';
  html += '<div id="mapbox"></div>';
  return html;
}

/* -- arguments -- */
function argumentsHtml() {
  const records = (state.caseView && state.caseView.arguments) || [];
  let html = "<h3>Arguments</h3>" +
    '<p class="sub">The facts, the alternatives and the critique of this case. What is kept here was confirmed by you; ' +
    "the assistant proposes and you decide.</p>" +
    '<div class="row"><button class="btn primary" id="toassist">Open the assistant</button></div>';
  if (!records.length) {
    html += '<div class="empty"><h3>No argument recorded yet</h3>' +
      "<p>Attach the case study, then let the assistant read the facts out of it and keep the ones that are right.</p></div>";
    return html;
  }
  ["facts", "alternatives", "critique"].forEach((kind) => {
    const of = records.filter((r) => r.kind === kind);
    if (!of.length) return;
    html += "<h3>" + kind.charAt(0).toUpperCase() + kind.slice(1) + "</h3>";
    of.forEach((record) => {
      html += '<div class="card"><div class="row" style="justify-content:space-between"><span class="muted">' +
        esc(txt(record.source)) + " - " + esc(txt(record.recorded_at)) + "</span></div><ul>";
      (record.items || []).forEach((item) => {
        const body = item.text || item.description || item.name || "";
        html += "<li>" + esc(txt(body)) +
          (item.target ? ' <span class="muted">(' + esc(txt(item.category)) + " on " + esc(txt(item.target)) + ")</span>" : "") +
          "</li>";
      });
      html += "</ul></div>";
    });
  });
  return html;
}

/* -- runs (the results of a case) -- */
function runsHtml() {
  const runs = state.runs || [];
  if (!runs.length) {
    return "<h3>Runs</h3>" +
      '<div class="empty"><h3>No run yet</h3>' +
      "<p>This case holds nothing computed. Add a spreadsheet under Data and use its columns as the inputs of a run.</p>" +
      '<button class="btn primary" id="runtodata">Go to the data tab</button></div>';
  }
  let html = "<h3>Runs</h3>" +
    '<div class="tablewrap"><table><caption>The runs of this case</caption><thead><tr>' +
    "<th>Run</th><th>Method</th><th>Tier</th><th>Results</th><th>Recorded</th><th></th></tr></thead><tbody>";
  runs.forEach((r, index) => {
    html += '<tr' + (state.runIndex === index ? ' class="row-warn"' : "") + "><td>" + esc(String(index + 1)) +
      "</td><td>" + esc(txt(r.method)) + "</td><td>" + esc(txt(r.tier)) + "</td><td>" + esc(String(r.artifacts)) +
      "</td><td>" + esc(txt(r.recorded_at)) + '</td><td><button class="btn sm" data-run="' + index + '">Open</button></td></tr>';
  });
  html += "</tbody></table></div>";
  const record = state.runRecords[state.runIndex];
  if (record) {
    html += '<div class="card" style="margin-top:14px"><h3>Run ' + (state.runIndex + 1) + "</h3>" +
      runHtml(record) + "</div>";
  }
  return html;
}

function runHtml(run) {
  const delivery = (run && run.delivery) || {};
  const ap = delivery.appendix || {};
  const honesty = ap.honesty || {};
  const honestyKeys = Object.keys(honesty).filter((k) => honesty[k]);
  let html = '<div class="row" style="justify-content:space-between"><h3 style="margin:0">' +
    esc(txt(run && run.method)) + "</h3><span class=\"badge\">" + esc(txt(ap.tier)) + "</span></div>" +
    '<div class="report">' + esc(delivery.report || "") + "</div>";
  if (honestyKeys.length) {
    html += banner("honesty", "Honesty: what was not done", "<ul>" + honestyKeys.map((k) =>
      "<li>" + esc(k) + ": " + esc(typeof honesty[k] === "string" ? honesty[k] : JSON.stringify(honesty[k])) + "</li>").join("") + "</ul>");
  }
  if ((ap.limitations || []).length) {
    html += banner("limit", "Limitations (as recorded)", "<ul>" + ap.limitations.map((l) => "<li>" + esc(l) + "</li>").join("") + "</ul>");
  }
  if ((ap.assumptions || []).length) {
    html += banner("limit", "Assumptions (as recorded)", "<ul>" + ap.assumptions.map((l) => "<li>" + esc(l) + "</li>").join("") + "</ul>");
  }
  html += "<h3>Artifacts</h3>" + artifactTable(ap);
  html += "<h3>Charts</h3>" + '<div id="chartbox">' + loading("Reading the chart plan") + "</div>";
  html += "<h3>Recorded metadata</h3>" + kv([
    ["Method", ap.method && ap.method.id], ["Method version", ap.method && ap.method.version],
    ["Category", ap.method && ap.method.category], ["Tier", ap.tier], ["Spec hash", ap.spec_hash],
    ["Outputs hash", run && run.outputs_hash], ["Code hash", ap.code_hash],
    ["Environment hash", ap.env_hash], ["Run id", ap.run_id],
    ["Checks", (ap.tests || []).join(", ")]]);
  return html;
}

async function loadCharts(caseId, runIndex, boxId) {
  const box = $("#" + (boxId || "chartbox"));
  if (!box) return;
  box.innerHTML = loading("Reading the chart plan");
  try {
    const query = (runIndex === null || runIndex === undefined) ? "" : ("?run_index=" + encodeURIComponent(runIndex));
    const plan = await api("/api/cases/" + caseId + "/charts" + query);
    const specs = (plan.charts || []).filter((spec) => spec.kind !== "table" && (spec.series || []).length);
    if (!specs.length) { box.innerHTML = '<p class="muted">This run recorded no values that can be drawn.</p>'; return; }
    let html = "";
    for (const spec of specs) {
      try {
        const r = await post("/api/cases/" + caseId + "/render", { chart: spec, run_index: runIndex });
        html += '<figure class="chart">' + r.svg + "<figcaption>" + esc(txt(spec.title)) +
          " - drawn by the server from the values that were recorded.</figcaption></figure>";
      } catch (e) {
        html += banner("blocked", "This chart could not be drawn", "<div>" + esc(e.message) + "</div>");
      }
    }
    box.innerHTML = html;
  } catch (e) { box.innerHTML = errorBanner(e); }
}

function artifactTable(ap) {
  const arts = ap.artifacts || [];
  const outs = (ap.reperform && ap.reperform.outputs) || {};
  if (!arts.length) return '<p class="muted">This delivery recorded no artifacts.</p>';
  let html = '<div class="tablewrap"><table><caption>Artifacts recorded by the delivery</caption><thead><tr>' +
    "<th>Artifact</th><th>Metric</th><th>Value</th><th>Derivation</th></tr></thead><tbody>";
  arts.forEach((a) => {
    const id = Array.isArray(a) ? a[0] : a.id;
    const labels = Array.isArray(a) ? a[1] : null;
    const metric = Array.isArray(a) ? (labels && labels[0]) : a.metric;
    const derivation = Array.isArray(a) ? a[2] : a.derivation;
    const value = outs[id] !== undefined ? outs[id] : (Array.isArray(a) ? null : a.value);
    html += "<tr><td>" + esc(txt(id)) + "</td><td>" + esc(txt(metric)) + "</td><td>" + esc(txt(value)) + "</td><td>" + esc(txt(derivation)) + "</td></tr>";
  });
  return html + "</tbody></table></div>";
}

/* -- versions -- */
function versionsHtml() {
  let html = "<h3>Versions</h3>" +
    '<div class="row"><button class="btn" id="newver">Save the current session as a new version</button></div>';
  if (!state.versions.length) {
    html += '<div class="empty">No versions stored yet.</div>';
    return html;
  }
  html += '<div class="tablewrap" style="margin-top:12px"><table><caption>Stored versions</caption><thead><tr>' +
    "<th>Version</th><th>Created</th><th>Method</th><th>Tier</th><th>Bundle hash</th><th></th></tr></thead><tbody>" +
    state.versions.map((v) => "<tr><td>" + esc(v.version) + "</td><td>" + esc(txt(v.created_at)) + "</td><td>" +
      esc(txt(v.method)) + "</td><td>" + esc(txt(v.tier)) + "</td><td>" + esc(txt(v.bundle_hash)) +
      '</td><td><button class="btn sm" data-ver="' + esc(v.version) + '">Open</button></td></tr>').join("") +
    "</tbody></table></div>";
  html += '<div class="row" style="margin-top:14px"><button class="btn" id="cmp">Compare the selected versions</button>' +
    '<span class="muted" id="cmpnote"></span></div><div id="cmpout"></div>';
  if (state.versionDoc) {
    const b = state.versionDoc.bundle || {};
    const ap = (b.delivery && b.delivery.appendix) || {};
    html += '<div class="card" style="margin-top:14px"><div class="row" style="justify-content:space-between">' +
      "<h3>Version " + esc(String(state.versionDoc.version)) + "</h3>" +
      '<button class="btn sm" id="closeversion">Close</button></div>' +
      '<div class="report">' + esc((b.delivery && b.delivery.report) || "not recorded") + "</div>" +
      "<h3>Artifacts</h3>" + artifactTable(ap) +
      "<h3>Recorded metadata</h3>" + kv([["Spec hash", ap.spec_hash], ["Outputs hash", b.outputs_hash],
        ["Method", ap.method && ap.method.id], ["Tier", ap.tier]]) + "</div>";
  }
  return html;
}

/* -- sign-off -- */
function signoffHtml() {
  return "<h3>Sign-off</h3>" +
    '<div class="grid2"><div class="stack"><label class="field" for="sgnrev">Reviewer name</label><input type="text" id="sgnrev">' +
    '<label class="field" for="sgnrole">Role</label><input type="text" id="sgnrole">' +
    '<label class="field" for="sgnscope">Scope</label><input type="text" id="sgnscope" value="the case bundle and its disclosed limitations">' +
    '<label class="field" for="sgnver">Version</label><input type="text" id="sgnver" value="1">' +
    '<button class="btn primary" id="sgnsave">Record sign-off</button></div>' +
    '<div id="sgnlist"></div></div>';
}

/* ---------- wiring of the open case tab ---------- */
function wireCaseTab() {
  const caseId = state.caseId;
  if (state.tab === "documents") {
    const button = $("#attachdoc");
    if (button) button.onclick = async () => {
      const input = $("#docfile");
      if (!input.files || !input.files.length) { toast("Choose a file first."); return; }
      button.disabled = true;
      button.textContent = "Reading the file...";
      try { await attachDocument(input.files[0]); }
      catch (e) { toast(e.message); button.disabled = false; button.textContent = "Attach to this case"; }
    };
  }
  if (state.tab === "data") {
    const button = $("#ingestbtn");
    if (button) button.onclick = ingestFile;
    if (state.ingest) renderIngest(state.ingest);
    else renderMapForm();
    if (state.mappedInputs) renderMappedRequest(state.mappedInputs);
  }
  if (state.tab === "arguments") {
    const button = $("#toassist");
    if (button) button.onclick = () => show("assistant");
  }
  if (state.tab === "runs") {
    $$("[data-run]").forEach((b) => { b.onclick = () => { state.runIndex = Number(b.dataset.run); renderCase(); }; });
    const toData = $("#runtodata");
    if (toData) toData.onclick = () => { state.tab = "data"; renderCase(); };
    if (state.runIndex !== null && state.runRecords[state.runIndex]) {
      loadCharts(caseId, state.runIndex, "chartbox");
    }
  }
  if (state.tab === "versions") {
    const nv = $("#newver"); if (nv) nv.onclick = newVersion;
    const cm = $("#cmp"); if (cm) cm.onclick = compareVersions;
    const cv = $("#closeversion"); if (cv) cv.onclick = () => { state.versionDoc = null; renderCase(); };
    $$("[data-ver]").forEach((btn) => { btn.onclick = () => openVersion(Number(btn.dataset.ver)); });
    renderSignoffs();
  }
  if (state.tab === "signoff") {
    const sv = $("#sgnsave"); if (sv) sv.onclick = recordSignoff;
    renderSignoffs();
  }
}

async function newVersion() {
  const s = state.session;
  if (!s || !s.delivery) { toast("Run an analysis first, then save it as a version."); return; }
  const ap = s.delivery.appendix || {};
  const bundle = { title: (s.work_plan || {}).objective || "Untitled case", method: (s.work_plan || {}).method || "",
    tier: ap.tier || "", spec_hash: ap.spec_hash || "", outputs_hash: (ap.reperform && ap.reperform.outputs_hash) || "",
    session: s, delivery: { report: s.delivery.report, appendix: ap }, reperform: ap.reperform || {} };
  try { const v = await post("/api/cases/" + state.caseId + "/versions", bundle); toast("Version " + v.version + " stored."); await openCase(state.caseId); }
  catch (e) { toast(e.message); }
}

async function openVersion(n) {
  try {
    const doc = await api("/api/cases/" + state.caseId + "/versions/" + n);
    state.versionDoc = { version: n, bundle: doc.bundle || doc };
    renderCase();
    toast("Version " + n + " loaded.");
  } catch (e) { toast(e.message); }
}

async function compareVersions() {
  const out = $("#cmpout");
  if (!out) return;
  const picks = $$("input[data-pick]:checked").map((i) => i.value);
  const versions = picks.length ? picks.join(",") : state.versions.slice(0, 2).map((v) => v.version).join(",");
  if (!versions) { out.innerHTML = '<p class="muted">No versions to compare.</p>'; return; }
  out.innerHTML = loading("Comparing on the server");
  try {
    const cmp = await api("/api/cases/" + state.caseId + "/compare?versions=" + encodeURIComponent(versions));
    state.compare = cmp;
    let h = "";
    if (cmp.issues && cmp.issues.length) h += banner("blocked", "Comparison issues", "<ul>" + cmp.issues.map((i) => "<li>" + esc(i) + "</li>").join("") + "</ul>");
    if (cmp.comparability) h += '<p class="muted">' + esc(cmp.comparability.rule) + "</p>";
    h += '<div class="tablewrap"><table><caption>Comparison (values copied from the stored bundles)</caption><thead><tr><th>Metric</th>' +
      (cmp.columns || []).map((c) => "<th class=\"num\">v" + esc(c.version) + "</th>").join("") + "</tr></thead><tbody>";
    (cmp.rows || []).forEach((r) => {
      h += "<tr><td>" + esc(txt(r.metric)) + "</td>" + (cmp.columns || []).map((c) => {
        const v = r.values ? r.values[String(c.version)] : null;
        const missing = (r.not_computed || []).indexOf(c.version) >= 0;
        return '<td class="num">' + (missing ? '<span class="muted">not computed</span>' : esc(txt(v))) + "</td>";
      }).join("") + "</tr>";
    });
    h += "</tbody></table></div>";
    if (cmp.note) h += '<p class="muted">' + esc(cmp.note) + "</p>";
    out.innerHTML = h;
  } catch (e) { out.innerHTML = errorBanner(e); }
}

function renderSignoffs() {
  const box = $("#sgnlist"); if (!box) return;
  if (!state.signoffs.length) { box.innerHTML = '<p class="muted">No sign-off recorded for this case yet.</p>'; return; }
  box.innerHTML = state.signoffs.map((s) => '<div class="card"><h3>Version ' + esc(txt(s.version)) + "</h3>" +
    kv([["Reviewer", s.reviewer && s.reviewer.name], ["Role", s.reviewer && s.reviewer.role],
        ["Scope", s.scope], ["Decision", s.decision], ["Signed at", s.signed_at],
        ["Bundle hash", s.bundle_hash]]) +
    (s.signature_text ? '<p class="muted">' + esc(s.signature_text) + "</p>" : "") + "</div>").join("");
}

async function recordSignoff() {
  const body = { version: Number($("#sgnver").value), reviewer: $("#sgnrev").value, role: $("#sgnrole").value,
                 scope: $("#sgnscope").value, decision: "reviewed" };
  try { await post("/api/cases/" + state.caseId + "/signoff", body); toast("Sign-off recorded."); await openCase(state.caseId); }
  catch (e) { toast(e.message); }
}

function confirmDelete(id) {
  openModal("Delete this case?", "<p>The stored bundle, its versions and its sign-offs are removed from the local case store.</p>",
    "Delete", async () => {
      try { await api("/api/cases/" + id, { method: "DELETE" }); toast("Case deleted."); state.caseId = null; state.caseView = null; show("home"); }
      catch (e) { toast(e.message); }
    });
}

/* ---------- the work plan and the session ---------- */
async function startFromHome() {
  const objective = $("#objective").value.trim();
  if (!objective) { toast("Describe the question first."); return; }
  const method = $("#method").value || (state.presets[$("#preset").value] || {}).method;
  if (!method) { toast("Choose a method or a preset."); return; }
  const body = { objective: objective, method: method };
  const preset = state.presets[$("#preset").value];
  body.inputs = preset ? JSON.parse(JSON.stringify(preset.inputs)) : {};
  const currency = $("#currency").value;
  if (currency) body.currency = currency;
  if (preset && preset.period) body.period = preset.period;
  try { await ensureCase(objective); } catch (e) { toast(e.message); return; }
  state.mappedInputs = null;
  await createSession(body);
}

async function createSession(body) {
  const p = $("#panel-new");
  p.innerHTML = '<div class="card">' + loading("Creating the session") + "</div>";
  show("new");
  try {
    state.session = await post("/api/sessions", body);
    state.delivery = state.session.delivery || null;
    renderNew();
  } catch (e) { p.innerHTML = '<div class="card">' + errorBanner(e) + "</div>"; }
}

RENDERERS.new = function () { if (state.session) renderNew(); };

function inputField(name, spec) {
  const type = (spec && spec.type) || "text";
  const desc = (spec && spec.desc) || "";
  if (type === "decimal_list") {
    return '<div class="stack" style="gap:4px"><label class="field" for="in-' + esc(name) + '">' + esc(name) +
      ' <span class="muted">' + esc(desc) + "</span></label>" +
      '<input type="text" id="in-' + esc(name) + '" data-type="decimal_list" placeholder="comma separated"></div>';
  }
  if (type === "object" || type === "array") {
    return '<div class="stack" style="gap:4px"><label class="field" for="in-' + esc(name) + '">' + esc(name) +
      ' <span class="muted">' + esc(desc) + "</span></label>" +
      '<textarea id="in-' + esc(name) + '" data-type="object" rows="3" placeholder="{}"></textarea></div>';
  }
  if (type === "boolean") {
    return '<div class="row"><input type="checkbox" id="in-' + esc(name) + '" data-type="boolean"><label class="field" for="in-' + esc(name) +
      '">' + esc(name) + ' <span class="muted">' + esc(desc) + "</span></label></div>";
  }
  return '<div class="stack" style="gap:4px"><label class="field" for="in-' + esc(name) + '">' + esc(name) +
    ' <span class="muted">' + esc(desc) + "</span></label>" +
    '<input type="text" id="in-' + esc(name) + '" data-type="decimal"></div>';
}

function renderNew() {
  const s = state.session;
  if (!s) { $("#panel-new").innerHTML = '<div class="empty">No session yet.</div>'; return; }
  const plan = s.work_plan || {};
  const method = state.methods.find((m) => m.method_id === (plan.method || s.spec && s.spec.method));
  const schema = (method && method.input_schema) || {};
  const delivered = s.delivery && s.delivery.status === "delivered";
  const blocked = s.delivery && s.delivery.status === "blocked";
  const mapping = s.status === "awaiting_mapping_confirmation";
  let html = '<div class="card">' +
    "<h2>New analysis</h2>" +
    '<div class="row" style="justify-content:space-between"><span class="sub">' + esc(plan.objective || "") + "</span>" +
    '<span class="badge">' + esc(plan.tier_label || txt(plan.tier)) + "</span></div>" +
    (blocked ? banner("blocked", "Blocked", "<div>" + esc(s.delivery.blocked_reason) + "</div>") : "") +
    "<h3>Method</h3>" +
    kv([["Method", (method && method.method_id) || plan.method], ["Version", method && method.version],
        ["Tier", plan.tier], ["Review status", method && method.review_status],
        ["Intended use", method && method.intended_use], ["Unsupported use", method && method.unsupported_use]]) +
    "<h3>Inputs</h3>" +
    (Object.keys(schema).length
      ? '<div class="grid2">' + Object.keys(schema).map((n) => inputField(n, schema[n])).join("") + "</div>"
      : '<p class="muted">This method declares no inputs.</p>') +
    '<div class="row" style="margin-top:14px">' +
      '<button class="btn primary" id="draft">Draft work plan</button>' +
      (delivered || blocked ? "" : '<button class="btn accent" id="confirm">Confirm spec and run</button><button class="btn" id="reject">Reject</button>') +
      (mapping ? '<button class="btn accent" id="confirmmap">Confirm account mapping and run</button>' : "") +
      '<span class="grow"></span><span class="muted">Session ' + esc(s.id) + " - " + esc(s.status) + "</span>" +
    "</div></div>";
  if (s.spec) {
    html += '<div class="card"><h2>Draft work plan</h2>' +
      kv([["Spec hash", s.spec.hash || "not frozen yet - the spec is hashed when you confirm"],
          ["Method version", plan.method_version], ["Planned checks", (plan.planned_checks || []).join(", ")]]) +
      (plan.ambiguities && plan.ambiguities.length
        ? "<h3>Assumptions and ambiguities</h3>" + plan.ambiguities.map((a) =>
            '<div class="muted" style="margin-bottom:6px"><strong>' + esc(a.question) + "</strong><br>" +
            esc(a.default_chosen) + "<br>" + esc(a.impact) + "</div>").join("")
        : "") +
      (plan.inputs ? "<h3>Inputs as recorded</h3>" + kv(Object.keys(plan.inputs).map((k) =>
            [k, (plan.inputs[k] && plan.inputs[k].provenance) + ": " + (plan.inputs[k] && plan.inputs[k].value)])) : "") +
      "</div>";
  }
  if (s.delivery) {
    html += '<div class="card"><h2>Stage status (from run events)</h2>' +
      kv(Object.keys(s.stage_states || {}).map((k) => [k, s.stage_states[k]])) +
      '<pre class="json" style="margin-top:12px">' + esc(JSON.stringify(s.events, null, 1)) + "</pre></div>";
  }
  $("#panel-new").innerHTML = html;
  const draft = $("#draft"); if (draft) draft.onclick = redraft;
  const cf = $("#confirm"); if (cf) cf.onclick = () => confirmSession(false);
  const rj = $("#reject"); if (rj) rj.onclick = () => confirmSession(true);
  const cm = $("#confirmmap"); if (cm) cm.onclick = () => confirmSession(false);
}

async function redraft() {
  const s = state.session; if (!s) return;
  const method = state.methods.find((m) => m.method_id === (s.work_plan || {}).method);
  const schema = (method && method.input_schema) || {};
  const inputs = {};
  for (const name of Object.keys(schema)) {
    const el = document.getElementById("in-" + name); if (!el) continue;
    const type = el.dataset.type;
    if (type === "boolean") { inputs[name] = el.checked; continue; }
    const raw = el.value.trim(); if (!raw) continue;
    if (type === "decimal_list") inputs[name] = raw.split(",").map((x) => x.trim()).filter((x) => x.length);
    else if (type === "object") { try { inputs[name] = JSON.parse(raw); } catch (e) { toast("That field is not valid JSON."); return; } }
    else inputs[name] = raw;
  }
  const body = { objective: (s.work_plan || {}).objective, method: (s.work_plan || {}).method,
                 inputs: Object.assign({}, state.mappedInputs || {}, inputs) };
  if (s.work_plan && s.work_plan.currency) body.currency = s.work_plan.currency;
  try { state.session = await post("/api/sessions", body); state.delivery = state.session.delivery || null; renderNew(); }
  catch (e) { $("#panel-new").insertAdjacentHTML("afterbegin", errorBanner(e)); }
}

async function confirmSession(reject) {
  const s = state.session; if (!s) return;
  try {
    state.session = await post("/api/sessions/" + s.id + "/" + (reject ? "reject" : "confirm"), {});
    state.delivery = state.session.delivery || null;
    if (!reject && state.session.delivery && state.session.delivery.status === "delivered") {
      await attachRunToCase();
      show("results");
      renderResults();
    } else {
      renderNew();
    }
  } catch (e) { $("#panel-new").insertAdjacentHTML("afterbegin", errorBanner(e)); }
}

async function attachRunToCase() {
  const s = state.session;
  if (!s || !s.delivery) return null;
  const caseId = await ensureCase((s.work_plan || {}).objective || "Untitled case");
  const ap = s.delivery.appendix || {};
  const run = {
    title: (s.work_plan || {}).objective || "",
    method: (s.work_plan || {}).method || (ap.method && ap.method.id) || "",
    tier: ap.tier || "",
    spec_hash: ap.spec_hash || "",
    outputs_hash: (ap.reperform && ap.reperform.outputs_hash) || "",
    session: s,
    delivery: { report: s.delivery.report, appendix: ap },
    reperform: ap.reperform || {}
  };
  try {
    const stored = await post("/api/cases/" + caseId + "/runs", run);
    toast("Run recorded in case " + caseId + ".");
    await openCase(caseId);
    state.tab = "runs";
    renderCase();
    return stored;
  } catch (e) { toast(e.message); return null; }
}

/* ---------- the result ---------- */
RENDERERS.results = function () { renderResults(); };
function renderResults() {
  const s = state.session; const d = s && s.delivery;
  const p = $("#panel-results");
  if (!d) { p.innerHTML = '<div class="empty"><h3>No result yet</h3><p>Run an analysis first.</p></div>'; return; }
  if (d.status === "blocked") {
    p.innerHTML = '<div class="card">' + banner("blocked", "Blocked", "<div>" + esc(d.blocked_reason) + "</div>") + "</div>";
    return;
  }
  const ap = d.appendix || {};
  const honesty = ap.honesty || {};
  const honestyKeys = Object.keys(honesty).filter((k) => honesty[k]);
  let html = '<div class="card">' +
    '<div class="row" style="justify-content:space-between"><h2>Result</h2><span class="badge">' + esc(ap.tier || "") + "</span></div>" +
    '<div class="report">' + esc(d.report) + "</div>";
  if (honestyKeys.length) {
    html += banner("honesty", "Honesty: what was not done", "<ul>" + honestyKeys.map((k) =>
      "<li>" + esc(k) + ": " + esc(typeof honesty[k] === "string" ? honesty[k] : JSON.stringify(honesty[k])) + "</li>").join("") + "</ul>");
  }
  if ((ap.limitations || []).length) {
    html += banner("limit", "Limitations (as recorded)", "<ul>" + ap.limitations.map((l) => "<li>" + esc(l) + "</li>").join("") + "</ul>");
  }
  if ((ap.assumptions || []).length) {
    html += banner("limit", "Assumptions (as recorded)", "<ul>" + ap.assumptions.map((l) => "<li>" + esc(l) + "</li>").join("") + "</ul>");
  }
  html += '<div class="row" style="margin-top:14px">' +
    '<button class="btn primary" id="savecase">Open the case</button>' +
    '<button class="btn" id="tocharts">Charts and exports</button>' +
    '<button class="btn" id="tostats">Download financial statements</button>' +
    '<span class="grow"></span><span class="muted">Spec hash ' + esc(ap.spec_hash) + "</span></div>" +
    (state.caseId ? '<p class="muted">This run is recorded in case ' + esc(txt(state.caseId)) + ".</p>" : "") +
    "</div>";
  html += '<div class="card"><h3>Artifacts</h3>' + artifactTable(ap) + "</div>";
  html += '<div class="card"><h3>Charts</h3><div id="chartbox">' + loading("Reading the chart plan") + "</div></div>";
  html += '<div class="card"><h3>Recorded metadata</h3>' + kv([
    ["Method", ap.method && ap.method.id], ["Method version", ap.method && ap.method.version],
    ["Category", ap.method && ap.method.category], ["Tier", ap.tier], ["Spec hash", ap.spec_hash],
    ["Code hash", ap.code_hash], ["Environment hash", ap.env_hash], ["Run id", ap.run_id],
    ["Sandbox", ap.sandbox && ap.sandbox.isolation ? ap.sandbox.isolation : ap.sandbox],
    ["Checks", (ap.tests || []).join(", ")]]) + "</div>";
  p.innerHTML = html;
  $("#savecase").onclick = () => { if (state.caseId) { state.tab = "runs"; show("case"); renderCase(); } else show("home"); };
  $("#tocharts").onclick = () => show("deliver");
  $("#tostats").onclick = () => show("accounts");
  if (state.caseId) loadCharts(state.caseId, state.runIndex, "chartbox");
}

/* ---------- the data panel ---------- */
RENDERERS.data = function () {
  const p = $("#panel-data");
  const box = $("#datacase");
  const view = state.caseView;
  if (!view) {
    box.innerHTML = '<div class="empty"><h3>Open a case first</h3>' +
      "<p>A data file belongs to a case. Open one from the shelf and come back.</p>" +
      '<button class="btn primary" id="datatoshelf">Your cases</button></div>';
    const g = $("#datatoshelf"); if (g) g.onclick = () => show("home");
    return;
  }
  box.innerHTML = '<p class="sub">Working on the case <strong>' + esc(txt(view.title)) + "</strong> (" +
    esc(txt(view.id)) + ").</p>" + dataTabHtml();
  wireCaseTab();
};

async function ingestFile() {
  const input = $("#ingfile");
  const out = $("#ingout");
  if (!input.files || !input.files.length) { toast("Choose a file first."); return; }
  const file = input.files[0];
  out.innerHTML = loading("Reading the file");
  const reader = new FileReader();
  reader.onload = async () => {
    const bytes = new Uint8Array(reader.result);
    let binary = ""; for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    const b64 = btoa(binary);
    const body = { filename: file.name, content_base64: b64 };
    const sheet = $("#ingsheet").value.trim(); if (sheet) body.sheet = sheet;
    const merged = $("#ingmerged").value; if (merged) body.merged = merged;
    try {
      const r = await post("/api/ingest", body);
      state.ingest = r;
      state.ingestB64 = b64;
      state.ingestBytes = bytes.length;
      state.mappedInputs = null;
      renderIngest(r);
    } catch (e) { out.innerHTML = errorBanner(e); }
  };
  reader.readAsArrayBuffer(file);
}

function renderIngest(r) {
  const t = r.table || {};
  let h = '<div class="card"><h3>' + esc(txt(t.filename)) + " (" + esc(txt(t.kind)) + ")</h3>" +
    kv([["Rows", t.n_rows], ["Columns", t.n_cols], ["SHA-256", t.sha256], ["Delimiter", t.delimiter]]) +
    '<div class="tablewrap" style="margin-top:12px"><table><caption>Columns as read</caption><thead><tr>' +
    "<th>Column</th><th>Type</th><th>Present</th><th>Missing</th><th>Sample</th></tr></thead><tbody>" +
    (t.columns || []).map((c) => "<tr><td>" + esc(txt(c.name)) + "</td><td>" + esc(txt(c.type)) + "</td><td>" +
      esc(txt(c.n_present)) + "</td><td>" + esc(txt(c.n_missing)) + "</td><td>" + esc((c.sample || []).join(", ")) + "</td></tr>").join("") +
    "</tbody></table></div>";
  if (t.rows) {
    h += '<div class="tablewrap" style="margin-top:12px"><table><caption>Rows as read</caption><thead><tr>' +
      (t.columns || []).map((c) => "<th>" + esc(txt(c.name)) + "</th>").join("") + "</tr></thead><tbody>" +
      t.rows.slice(0, 50).map((row) => "<tr>" + row.map((v) => "<td>" + esc(txt(v)) + "</td>").join("") + "</tr>").join("") +
      "</tbody></table></div>";
  }
  if (t.provenance) h += "<h3>Provenance</h3>" + kv(Object.keys(t.provenance).map((k) => [k, t.provenance[k]]));
  if (t.not_read_as) h += '<p class="muted">' + esc(t.not_read_as) + "</p>";
  h += '<div class="row" style="margin-top:12px"><button class="btn primary" id="attachdata">Attach this file to the case</button></div>';
  h += "</div>";
  $("#ingout").innerHTML = h;
  const attach = $("#attachdata"); if (attach) attach.onclick = attachDataToCase;
  renderMapForm();
}

function renderMapForm() {
  const box = $("#mapbox");
  if (!box) return;
  if (!state.ingest) { box.innerHTML = ""; return; }
  const methods = state.methods.map((m) => "<option value=\"" + esc(m.method_id) + "\">" + esc(m.method_id) + "</option>").join("");
  box.innerHTML = '<div class="card"><h3>Map the columns to a method</h3>' +
    '<p class="sub">The method itself validates the mapping: the server refuses a mapping that does not form a valid request.</p>' +
    '<div class="row"><label class="field" style="margin:0">Method <select id="mapmethod"><option value="">choose a method</option>' +
    methods + "</select></label></div>" +
    '<div id="mapfields" style="margin-top:12px"></div>' +
    '<div class="row" style="margin-top:12px"><button class="btn primary" id="mapbtn">Map the columns</button>' +
    '<span class="grow"></span><span class="muted">A column can only feed an input that takes a list of values.</span></div>' +
    '<div id="mapout"></div></div>';
  const sel = $("#mapmethod");
  sel.onchange = renderMapFields;
  const map = $("#mapbtn");
  if (map) map.onclick = mapColumns;
  if (state.presets && Object.keys(state.presets).length) {
    const first = Object.keys(state.presets).find((id) => (state.presets[id] || {}).method);
    if (first) sel.value = state.presets[first].method;
  }
  renderMapFields();
}

function renderMapFields() {
  const box = $("#mapfields");
  if (!box) return;
  const methodId = $("#mapmethod").value;
  const method = state.methods.find((m) => m.method_id === methodId);
  const schema = (method && method.input_schema) || {};
  const columns = ((state.ingest && state.ingest.table && state.ingest.table.columns) || []).map((c) => c.name);
  const keys = Object.keys(schema);
  if (!keys.length) { box.innerHTML = '<p class="muted">Choose a method to see the inputs it takes.</p>'; return; }
  const MAPPABLE = ("value_list", "code_list", "column_map");
  const typed = keys.filter((name) => {
    const spec = schema[name] || {};
    return spec.required !== false && MAPPABLE.indexOf(spec.type) < 0;
  });
  let html = "";
  if (typed.length) {
    html += banner("limit", "This method needs more than the file can give",
      "<div>" + typed.map((n) => esc(n) + " (" + esc(txt((schema[n] || {}).type)) + ")").join(", ") +
      " cannot come from a column, so the server will refuse the mapping until they are typed in. " +
      "Type them on the work plan screen instead; the columns you do map are kept.</div>");
  }
  html += '<div class="grid2">';
  keys.forEach((name) => {
    const spec = schema[name] || {};
    const type = spec.type || "text";
    if (type === "value_list" || type === "code_list") {
      html += '<div class="stack" style="gap:4px"><label class="field" for="map-' + esc(name) + '">' + esc(name) +
        ' <span class="muted">' + esc(type) + "</span></label>" +
        '<select id="map-' + esc(name) + '" data-maptype="list"><option value="">(not mapped)</option>' +
        columns.map((c) => '<option value="' + esc(c) + '">' + esc(c) + "</option>").join("") + "</select></div>";
    } else if (type === "column_map") {
      html += '<div class="stack" style="gap:4px"><label class="field" for="map-' + esc(name) + '">' + esc(name) +
        ' <span class="muted">column_map</span></label>' +
        '<input type="text" id="map-' + esc(name) + '" data-maptype="column_map" placeholder=\'{"name":"column"}\'></div>';
    } else {
      html += '<div class="stack" style="gap:4px"><label class="field">' + esc(name) +
        ' <span class="muted">' + esc(type) + " - type it on the work plan screen</span></label></div>";
    }
  });
  html += "</div>";
  box.innerHTML = html;
}

function collectMapping() {
  const mapping = {};
  $$("[data-maptype]").forEach((el) => {
    const name = el.id.replace(/^map-/, "");
    const value = el.value.trim();
    if (!value) return;
    if (el.dataset.maptype === "column_map") {
      try { mapping[name] = JSON.parse(value); }
      catch (e) { throw new Error("The mapping for " + name + " is not valid JSON."); }
    } else {
      mapping[name] = value;
    }
  });
  return mapping;
}

async function mapColumns() {
  const out = $("#mapout");
  const method = $("#mapmethod").value;
  if (!method) { out.innerHTML = errorBanner(new Error("Choose a method first.")); return; }
  let columns;
  try { columns = collectMapping(); }
  catch (e) { out.innerHTML = errorBanner(e); return; }
  if (!Object.keys(columns).length) {
    out.innerHTML = errorBanner(new Error("Map at least one column to an input."));
    return;
  }
  try {
    const r = await post("/api/ingest", {
      filename: state.ingest ? state.ingest.table.filename : "",
      content_base64: state.ingestB64 || "",
      map: { method: method, columns: columns }
    });
    renderMappedRequest(r.mapped_request);
  } catch (e) { out.innerHTML = errorBanner(e); }
}

function renderMappedRequest(mapped) {
  const out = $("#mapout");
  if (!out) return;
  if (!mapped) { out.innerHTML = ""; return; }
  state.mappedInputs = mapped.inputs || {};
  let h = "<h3>Mapped request (as returned)</h3>" +
    '<pre class="json">' + esc(JSON.stringify(mapped, null, 1)) + "</pre>";
  if (mapped.provenance && mapped.provenance.note) {
    h += '<p class="muted">' + esc(mapped.provenance.note) + "</p>";
  }
  if ((mapped.not_mapped || []).length) {
    h += banner("limit", "Inputs the file did not fill",
      "<div>" + mapped.not_mapped.map((n) => esc(n)).join(", ") + "</div>");
  }
  h += '<div class="row" style="margin-top:12px">' +
    '<label class="field" style="margin:0">Objective <input type="text" id="useobjective" size="36" value="' +
      esc((state.caseView && state.caseView.title) || "") + '"></label>' +
    '<label class="field" style="margin:0">Currency <select id="usecurrency"><option value="">Currency</option>' +
      state.currencies.map((c) => "<option value=\"" + esc(c.code) + "\">" + esc(c.code) + " - " + esc(c.name) + "</option>").join("") +
    "</select></label>" +
    '<button class="btn primary" id="usebtn">Use these inputs</button></div>';
  out.innerHTML = h;
  const use = $("#usebtn"); if (use) use.onclick = useTheseInputs;
}

async function useTheseInputs() {
  const mapped = state.mappedInputs;
  if (!mapped || !Object.keys(mapped).length) { toast("Map the columns first."); return; }
  const method = $("#mapmethod").value;
  const objective = ($("#useobjective") && $("#useobjective").value.trim()) ||
    (state.caseView && state.caseView.title) || "Analyse the attached data.";
  const currency = $("#usecurrency") ? $("#usecurrency").value : "";
  const body = { objective: objective, method: method, inputs: mapped };
  if (currency) body.currency = currency;
  try { await ensureCase(objective); } catch (e) { toast(e.message); return; }
  state.mappedInputs = mapped;
  await createSession(body);
}

async function attachDataToCase() {
  if (!state.caseId) { toast("Open a case first."); return; }
  if (!state.ingest) { toast("Read a file first."); return; }
  const t = state.ingest.table || {};
  try {
    await post("/api/cases/" + state.caseId + "/data-files", {
      filename: t.filename, table: t, sha256: t.sha256, bytes: state.ingestBytes || null
    });
    toast(t.filename + " attached to the case.");
    await openCase(state.caseId);
    state.tab = "data";
    renderCase();
  } catch (e) { toast(e.message); }
}

/* ---------- the assistant ---------- */
RENDERERS.assistant = function () {
  const p = $("#panel-assistant");
  const view = state.caseView;
  p.innerHTML = '<div class="card"><h2 id="assistant-title">Assistant (optional)</h2><div id="asstcfg" class="sub">' +
    loading("Checking the local configuration") + "</div>" +
    '<p class="sub">The model proposes; the code validates and computes. <strong>The model writes no numbers.</strong> ' +
    "Nothing here is verified computation, and no API key ever reaches the browser.</p>" +
    '<div id="asstcase"></div>' +
    '<div class="row"><button class="btn primary" id="asstfacts">Read the facts from the case</button>' +
    '<button class="btn" id="asstalts">Propose alternatives</button>' +
    '<button class="btn" id="asstcrit">Challenge my analysis</button></div>' +
    '<div id="asstout"></div></div>';
  const box = $("#asstcase");
  if (!view) {
    box.innerHTML = '<p class="muted">Open a case first: the assistant reads the documents you attached to it.</p>';
  } else {
    const documents = (view.documents || []).length;
    box.innerHTML = '<p class="sub">Working on the case <strong>' + esc(txt(view.title)) + "</strong> (" + esc(txt(view.id)) +
      "), which holds " + documents + " document(s) and " + ((view.runs || []).length) + " run(s).</p>" +
      '<div class="row"><label class="field" style="margin:0">Objective <input type="text" id="asstobjective" size="40" value="' +
        esc(txt(view.title)) + '"></label></div>' +
      '<div class="row" style="margin-top:10px"><label class="check"><input type="checkbox" id="consent">' +
      "<span>I agree to send the text of this case's documents to the configured model provider. " +
      "Nothing is sent until this box is ticked.</span></label></div>" +
      '<label class="check" style="margin-top:6px"><input type="checkbox" id="piiok">' +
      "<span>The documents may name people. I accept that the text leaves this machine.</span></label>";
  }
  api("/api/assist/config").then((cfg) => {
    state.assist = cfg;
    $("#asstcfg").textContent = cfg.enabled
      ? "Model assistance is configured on this server (" + (cfg.provider || "") + " / " + (cfg.builder_model || "") + ")."
      : (cfg.reason || "Model assistance is not configured on this server.");
    ["asstfacts", "asstalts", "asstcrit"].forEach((id) => { const b = $("#" + id); if (b) b.disabled = !cfg.enabled; });
  }).catch((e) => { $("#asstcfg").innerHTML = errorBanner(e);
    ["asstfacts", "asstalts", "asstcrit"].forEach((id) => { const b = $("#" + id); if (b) b.disabled = true; }); });
  $("#asstfacts").onclick = assistFacts;
  $("#asstalts").onclick = assistAlternatives;
  $("#asstcrit").onclick = assistCritique;
};

function caseText() {
  const texts = (state.caseView && state.caseView.document_texts) || {};
  return Object.keys(texts).map((name) => "### " + name + "\n" + texts[name]).join("\n\n");
}
function consentGiven() {
  const box = $("#consent");
  if (!box) return false;
  if (!box.checked) { toast("Tick the consent box first: nothing is sent without it."); return false; }
  return true;
}
function confirmedItems(kind) {
  const records = (state.caseView && state.caseView.arguments) || [];
  const items = [];
  records.forEach((record) => {
    if (record.kind !== kind) return;
    (record.items || []).forEach((item) => { if (item && typeof item === "object") items.push(item); });
  });
  return items;
}

async function assistFacts() {
  const out = $("#asstout");
  if (!state.caseView) { out.innerHTML = errorBanner(new Error("Open a case first.")); return; }
  if (!consentGiven()) return;
  const text = caseText();
  if (!text.trim()) { out.innerHTML = errorBanner(new Error("This case holds no document text to read.")); return; }
  out.innerHTML = loading("Reading the facts out of your documents");
  const body = { task: "facts", consent: true, case_text: text };
  const pii = $("#piiok"); if (pii && pii.checked) body.pii_acknowledged = true;
  try {
    const r = await post("/api/assist", body);
    state.proposals.facts = r.proposals || [];
    out.innerHTML = proposalsHtml("facts", r);
  } catch (e) { out.innerHTML = assistErrorHtml(e); }
}

async function assistAlternatives() {
  const out = $("#asstout");
  if (!state.caseView) { out.innerHTML = errorBanner(new Error("Open a case first.")); return; }
  if (!consentGiven()) return;
  const facts = confirmedItems("facts").map((f) => ({ id: f.id, text: f.text }));
  if (!facts.length) {
    out.innerHTML = errorBanner(new Error("Keep some facts first: the alternatives have to follow from them."));
    return;
  }
  const objective = ($("#asstobjective") && $("#asstobjective").value.trim()) || (state.caseView.title || "");
  out.innerHTML = loading("Asking for alternatives");
  try {
    const r = await post("/api/assist", { task: "alternatives", consent: true, facts: facts, objective: objective });
    state.proposals.alternatives = r.proposals || [];
    out.innerHTML = proposalsHtml("alternatives", r);
  } catch (e) { out.innerHTML = assistErrorHtml(e); }
}

async function assistCritique() {
  const out = $("#asstout");
  if (!state.caseView) { out.innerHTML = errorBanner(new Error("Open a case first.")); return; }
  if (!consentGiven()) return;
  const facts = confirmedItems("facts").map((f) => ({ id: f.id, text: f.text }));
  const alternatives = confirmedItems("alternatives").map((a) => ({ id: a.id, name: a.name, text: a.text || a.description || "" }));
  if (!facts.length || !alternatives.length) {
    out.innerHTML = errorBanner(new Error("The critique needs both facts and alternatives that you kept."));
    return;
  }
  out.innerHTML = loading("Asking for a critique");
  try {
    const r = await post("/api/assist", { task: "critique", consent: true, facts: facts, alternatives: alternatives });
    state.proposals.critique = r.items || [];
    out.innerHTML = proposalsHtml("critique", r);
  } catch (e) { out.innerHTML = assistErrorHtml(e); }
}

function assistErrorHtml(error) {
  if (error.status === 503) {
    return banner("blocked", "The assistant is not configured on this server",
      "<div>No model provider is configured, so nothing was sent and nothing was proposed. " +
      "The server has to be started with a provider for the assistant to work.</div>");
  }
  if (error.status === 400) {
    return banner("blocked", "The assistant needs your consent",
      "<div>" + esc(error.message) + "</div>");
  }
  if (error.status === 429) {
    return banner("limit", "The assistant is out of budget for this server run",
      "<div>" + esc(error.message) + "</div>");
  }
  if (error.status === 502) {
    return banner("blocked", "The model provider failed",
      "<div>" + esc(error.message) + "</div>");
  }
  let h = errorBanner(error);
  const rejected = error.payload && error.payload.rejected;
  if (rejected && rejected.length) {
    h += banner("limit", "What the code refused", "<ul>" + rejected.map((r) =>
      "<li>" + esc(txt(r.reason)) + "</li>").join("") + "</ul>");
  }
  return h;
}

function proposalsHtml(kind, r) {
  const items = kind === "critique" ? (r.items || []) : (r.proposals || []);
  if (!items.length) return '<p class="muted">The model returned nothing that passed the code checks.</p>';
  let h = "<h3>What the model proposed</h3>" +
    '<p class="sub">Read them. Keep the ones that are right: they are copied into the case as your argument.</p>' +
    '<div class="card">';
  items.forEach((item) => {
    const label = item.text || item.description || item.name || "";
    h += '<div class="row" style="align-items:flex-start;gap:8px;border-bottom:1px solid var(--border-2);padding:8px 0">' +
      '<input type="checkbox" data-keep="' + esc(txt(item.id)) + '" checked>' +
      "<div><div>" + esc(txt(label)) + "</div>" +
      '<div class="muted">' + esc(txt(item.category || "")) +
      (item.target ? " - on " + esc(txt(item.target)) : "") +
      (item.supports && item.supports.length ? " - follows from " + esc(item.supports.join(", ")) : "") +
      "</div></div></div>";
  });
  h += '<div class="row" style="margin-top:12px"><button class="btn primary" id="keepbtn">Keep the selected ones</button></div></div>';
  const rejected = r.rejected || [];
  if (rejected.length) {
    h += banner("limit", "What the code refused", "<ul>" + rejected.map((x) =>
      "<li>" + esc(txt(x.reason)) + "</li>").join("") + "</ul>");
  }
  if (r.reviewer_same_as_builder) {
    h += '<p class="muted">The reviewer and the builder are the same model, so this critique is not independent.</p>';
  }
  if (r.note) h += '<p class="muted">' + esc(r.note) + "</p>";
  const out = $("#asstout");
  out.innerHTML = h;
  const keep = $("#keepbtn");
  if (keep) keep.onclick = () => keepProposals(kind);
  return h;
}

async function keepProposals(kind) {
  const caseId = state.caseId;
  if (!caseId) { toast("Open a case first."); return; }
  const chosen = $$("[data-keep]:checked").map((el) => el.dataset.keep);
  const items = state.proposals[kind].filter((item) => chosen.indexOf(item.id) >= 0)
    .map((item) => Object.assign({}, item, { status: "confirmed" }));
  if (!items.length) { toast("Select at least one."); return; }
  try {
    await post("/api/cases/" + caseId + "/arguments", {
      kind: kind, items: items, source: "model proposal confirmed by the student"
    });
    toast(items.length + " " + kind + " kept in the case.");
    await openCase(caseId);
    $("#asstout").innerHTML = '<p class="muted">Kept. The case now holds them under Arguments.</p>';
  } catch (e) { toast(e.message); }
}

/* ---------- references ---------- */
RENDERERS.refs = function () {
  const p = $("#panel-refs");
  p.innerHTML = '<div class="card"><h2>References (optional)</h2>' +
    '<p class="sub">The title and DOI are sent to the selected bibliographic API (<code>/api/literature/sources</code>). ' +
    "No case text is sent. A citation is marked verified only when the DOI resolves and the title matches exactly.</p>" +
    '<div class="row"><input type="text" id="refdoi" placeholder="DOI (optional, e.g. 10.1000/example)">' +
    '<input type="text" id="reftitle" placeholder="Title"><select id="refsrc"><option value="auto">auto</option></select>' +
    '<button class="btn primary" id="verify">Verify reference</button>' +
    '<label class="field" style="margin:0">Citation style <select id="refstyle"><option value="apa">APA 7</option>' +
    '<option value="harvard">Harvard</option></select></label>' +
    '<button class="btn" id="cite">Get citation</button></div>' +
    '<div id="refout"></div>' +
    '<div class="row" style="margin-top:14px"><button class="btn" id="showlog">Show retrieval log</button>' +
    '<button class="btn" id="drift">Check drift</button></div><div id="reflog"></div></div>';
  api("/api/literature/sources").then((d) => {
    const sel = $("#refsrc");
    (d.sources || []).forEach((s) => { const o = document.createElement("option"); o.value = s.name; o.textContent = s.label; sel.appendChild(o); });
    $("#refs .sub").insertAdjacentHTML("beforeend", "<br>" + esc(d.notice || ""));
    const notices = d.citation_notices || {};
    if (notices.apa) $("#refs .sub").insertAdjacentHTML("beforeend", "<br>" + esc(notices.apa));
    if (notices.harvard) $("#refs .sub").insertAdjacentHTML("beforeend", "<br>" + esc(notices.harvard));
  }).catch(() => {});
  $("#verify").onclick = verifyReference;
  $("#cite").onclick = getCitation;
  $("#showlog").onclick = showLog;
  $("#drift").onclick = checkDrift;
};

async function verifyReference() {
  const out = $("#refout");
  out.innerHTML = loading("Verifying the reference");
  try {
    const r = await post("/api/literature/verify", { title: $("#reftitle").value, doi: $("#refdoi").value, source: $("#refsrc").value });
    state.ref = r;
    let h = "";
    if (r.error) h += banner("blocked", "Not verified", "<div>" + esc(r.error) + "</div>");
    h += kv(Object.keys(r).filter((k) => !["citation"].includes(k)).map((k) => [k, typeof r[k] === "object" ? JSON.stringify(r[k]) : r[k]]));
    if (r.response_hash) h += "<p class=\"muted\">Retrieval audit: sha256 " + esc(r.response_hash) + " at " + esc(txt(r.retrieved_at)) + "</p>";
    out.innerHTML = h;
  } catch (e) { out.innerHTML = errorBanner(e); }
}

async function getCitation() {
  const out = $("#refout");
  try {
    const r = await post("/api/literature/verify", { title: $("#reftitle").value, doi: $("#refdoi").value,
      source: $("#refsrc").value, cite: $("#refstyle").value });
    state.ref = r;
    let h = "";
    if (r.citation) h += '<pre class="json">' + esc(r.citation.text || r.citation) + "</pre>";
    if (r.citation && r.citation.notice) h += '<p class="muted">' + esc(r.citation.notice) + "</p>";
    if (r.error) h += banner("blocked", "Not verified", "<div>" + esc(r.error) + "</div>");
    out.innerHTML = h || '<p class="muted">The server returned no citation.</p>';
  } catch (e) { out.innerHTML = errorBanner(e); }
}

async function showLog() {
  const out = $("#reflog");
  try {
    const r = await api("/api/literature/log");
    const entries = r.entries || r.log || [];
    if (!entries.length) { out.innerHTML = '<p class="muted">The retrieval log is empty.</p>'; return; }
    out.innerHTML = '<pre class="json">' + esc(JSON.stringify(entries, null, 1)) + "</pre>";
  } catch (e) { out.innerHTML = errorBanner(e); }
}

async function checkDrift() {
  const out = $("#reflog");
  out.innerHTML = loading("Checking for drift");
  try {
    const r = await api("/api/literature/drift");
    out.innerHTML = "<pre class=\"json\">" + esc(JSON.stringify(r, null, 1)) + "</pre>";
  } catch (e) { out.innerHTML = errorBanner(e); }
}

/* ---------- deliverables ---------- */
RENDERERS.deliver = function () {
  const p = $("#panel-deliver");
  const b = state.caseBundle;
  const ap = b && b.delivery ? b.delivery.appendix : null;
  const arts = ap && ap.artifacts ? ap.artifacts : [];
  p.innerHTML = '<div class="card"><h2>Deliverables</h2>' +
    '<div class="row"><label class="field" style="margin:0">Case <input type="text" id="delcaseid" size="14" value="' +
      esc(state.caseId || "") + '"></label><button class="btn" id="delload">Load case</button>' +
    '<span class="grow"></span><span class="muted">Exports are written by the server; the path it returns is shown as-is.</span></div>' +
    '<div id="delout"></div></div>' +
    '<div class="card"><h3>Report</h3><div class="report" id="delreport">' + (b && b.delivery ? esc(b.delivery.report) : "not recorded") + "</div></div>" +
    '<div class="card"><h3>Charts</h3><div class="row"><select id="chartkind"><option value="bar">bar</option>' +
    '<option value="line">line</option><option value="table">table</option></select>' +
    '<select id="chartart"></select><input type="text" id="charttitle" placeholder="Chart title" size="26">' +
    '<button class="btn primary" id="chartbtn">Render chart</button></div>' +
    '<p class="muted">The chart is drawn by the server from the stored values; nothing is computed in the browser.</p>' +
    '<div id="chartout"></div></div>' +
    '<div class="card"><h3>Export</h3><div class="row"><select id="expkind"><option value="csv">csv</option>' +
    '<option value="spreadsheetml">spreadsheetml</option><option value="html">html</option></select>' +
    '<input type="text" id="expdest" size="42" placeholder="exports/case.csv"><button class="btn" id="expbtn">Export</button></div>' +
    '<div id="expout"></div>' +
    '<div class="row" style="margin-top:10px"><button class="btn" id="expzip">Download results (zip)</button>' +
    '<span class="muted">A per-case zip export is requested; the working zip today is the case-store backup.</span></div></div>';
  const sel = $("#chartart");
  arts.forEach((a) => {
    const id = Array.isArray(a) ? a[0] : a.id;
    const labels = Array.isArray(a) ? a[1] : null;
    const metric = Array.isArray(a) ? (labels && labels[0]) : a.metric;
    const o = document.createElement("option"); o.value = metric || id; o.textContent = metric || id; sel.appendChild(o);
  });
  $("#delload").onclick = () => openCase($("#delcaseid").value.trim());
  $("#chartbtn").onclick = renderChart;
  $("#expbtn").onclick = exportCase;
  $("#expzip").onclick = backupCases;
};

async function renderChart() {
  const out = $("#chartout");
  out.innerHTML = loading("Rendering on the server");
  const spec = { kind: $("#chartkind").value, title: $("#charttitle").value || $("#chartart").value,
                 series: [{ label: $("#chartart").value, artifact: $("#chartart").value }] };
  try {
    const r = await post("/api/cases/" + state.caseId + "/render", { chart: spec });
    out.innerHTML = '<figure class="chart">' + r.svg + "<figcaption>Rendered by the server from the stored values.</figcaption></figure>";
  } catch (e) { out.innerHTML = errorBanner(e); }
}

async function exportCase() {
  const out = $("#expout");
  out.innerHTML = loading("Exporting on the server");
  const kind = $("#expkind").value;
  const dest = $("#expdest").value.trim() || ("exports/" + state.caseId + "." + (kind === "spreadsheetml" ? "xml" : kind));
  try {
    const r = await post("/api/cases/" + state.caseId + "/export", { kind: kind, destination: dest });
    out.innerHTML = banner("ok", "Exported", "<div>" + esc(txt(r.path || dest)) + "</div>");
  } catch (e) { out.innerHTML = errorBanner(e); }
}

/* ---------- accounts ---------- */
RENDERERS.accounts = function () {
  const p = $("#panel-accounts");
  p.innerHTML = '<div class="card"><h2>Accounts</h2>' +
    '<p class="sub">Management accounts: a declarative engagement with two checkpoints - the frozen spec, then the account mapping. ' +
    "The mapping is confirmed before anything is posted.</p>" +
    '<div class="row"><select id="acctpreset"></select><button class="btn primary" id="acctstart">Start engagement</button></div>' +
    '<div id="acctout"></div></div>' +
    '<div class="card"><h2>Account mapping</h2><div id="acctmap" class="muted">No mapping yet.</div></div>';
  const sel = $("#acctpreset");
  Object.keys(state.presets).forEach((id) => {
    const pr = state.presets[id];
    if (pr.method === "management_accounts") { const o = document.createElement("option"); o.value = id; o.textContent = id; sel.appendChild(o); }
  });
  if (!sel.options.length) sel.innerHTML = '<option value="management_accounts">management_accounts</option>';
  $("#acctstart").onclick = startAccounts;
};

async function startAccounts() {
  const out = $("#acctout");
  const preset = state.presets[$("#acctpreset").value];
  out.innerHTML = loading("Creating the engagement");
  try {
    const body = { objective: (preset && preset.objective) || "Prepare the management accounts.",
                   method: "management_accounts", inputs: preset ? preset.inputs : {} };
    if (preset && preset.currency) body.currency = preset.currency;
    state.session = await post("/api/sessions", body);
    const s = state.session;
    let h = "";
    if (s.status === "awaiting_confirmation") {
      h += '<p class="muted">The spec is frozen and waiting for confirmation.</p>' +
        '<button class="btn primary" id="acctconfirm">Confirm spec and run</button>';
    } else if (s.status === "awaiting_mapping_confirmation") {
      h += banner("limit", "Account mapping (second checkpoint)", "<p>Confirm the mapping below before anything is posted.</p>");
      const m = s.account_mapping;
      if (m) h += '<pre class="json">' + esc(JSON.stringify(m, null, 1)) + "</pre>";
      h += '<button class="btn primary" id="acctconfirm">Confirm account mapping and run</button>';
    }
    out.innerHTML = h;
    const c = $("#acctconfirm");
    if (c) c.onclick = async () => {
      try { state.session = await post("/api/sessions/" + s.id + "/confirm", {}); renderAccounts(); }
      catch (e) { out.innerHTML = errorBanner(e); }
    };
    renderAccounts();
  } catch (e) { out.innerHTML = errorBanner(e); }
}

function renderAccounts() {
  const s = state.session; const box = $("#acctout");
  if (!s || !box) return;
  const d = s.delivery;
  if (d && d.status === "blocked") { box.innerHTML = banner("blocked", "Blocked", "<div>" + esc(d.blocked_reason) + "</div>"); return; }
  if (d && d.status === "delivered") {
    const ap = d.appendix || {};
    box.innerHTML = '<div class="report">' + esc(d.report) + "</div>" +
      ((ap.limitations || []).length ? banner("limit", "Limitations (as recorded)", "<ul>" + ap.limitations.map((l) => "<li>" + esc(l) + "</li>").join("") + "</ul>") : "") +
      '<div class="row"><button class="btn primary" id="dlstatements">Download financial statements</button></div>';
    $("#dlstatements").onclick = () => exportStatements();
  }
  const mbox = $("#acctmap");
  if (mbox) {
    if (s.account_mapping) mbox.innerHTML = '<pre class="json">' + esc(JSON.stringify(s.account_mapping, null, 1)) + "</pre>";
    else if (s.work_plan && s.work_plan.account_mapping) mbox.innerHTML = '<pre class="json">' + esc(JSON.stringify(s.work_plan.account_mapping, null, 1)) + "</pre>";
    else mbox.innerHTML = '<span class="muted">No mapping yet.</span>';
  }
}

async function exportStatements() {
  try {
    const r = await post("/api/cases/" + (state.caseId || "") + "/export", { kind: "html", destination: "exports/statements.html" });
    toast("Statements written to " + (r.path || "exports/statements.html") + ".");
  } catch (e) { toast(e.message); }
}

/* ---------- frameworks ---------- */
RENDERERS.frames = function () {
  const p = $("#panel-frames");
  p.innerHTML = '<div class="card"><h2>Frameworks &amp; templates</h2>' +
    '<div class="row"><input type="search" id="fq" placeholder="Search the catalogue"><select id="ftype"><option value="">all types</option>' +
    '<option value="F">framework</option><option value="M">model</option><option value="Q">quantitative</option><option value="T">theory</option></select>' +
    '<button class="btn primary" id="fsearch">Search</button></div><div id="fout"></div></div>' +
    '<div class="card"><h3>Frameworks, models and methods</h3>' +
    '<p class="sub">The catalogue below is what the server recorded. Nothing is applied unless ticked: a framework or ' +
    "template is only used when you confirm it in the frozen spec.</p>" +
    '<div class="tablewrap"><table><caption>Method catalogue</caption><thead><tr>' +
    "<th>Method</th><th>Category</th><th>Tier</th><th>Review status</th><th>Intended use</th></tr></thead><tbody>" +
    state.methods.map((m) => "<tr><td>" + esc(txt(m.method_id)) + "</td><td>" + esc(txt(m.category)) + "</td><td>" +
      esc(txt(m.tier)) + "</td><td>" + esc(txt(m.review_status)) + "</td><td>" + esc(txt(m.intended_use)) + "</td></tr>").join("") +
    "</tbody></table></div></div>" +
    '<div class="card"><h3>Templates</h3><div id="tout"></div></div>';
  $("#fsearch").onclick = searchFrameworks;
  api("/api/templates").then((t) => {
    $("#tout").innerHTML = t.map((x) => '<div class="row" style="justify-content:space-between;border-bottom:1px solid var(--border-2);padding:8px 0">' +
      "<span>" + esc(txt(x.id)) + " - " + esc(txt(x.name)) + "</span>" +
      '<button class="btn sm" data-template="' + esc(x.id) + '">Load the ' + esc(txt(x.id)) + " template request</button></div>").join("");
    $$("[data-template]").forEach((b) => { b.onclick = () => loadTemplate(b.dataset.template); });
  }).catch((e) => { $("#tout").innerHTML = errorBanner(e); });
  searchFrameworks();
};

async function searchFrameworks() {
  const out = $("#fout");
  out.innerHTML = loading("Searching the catalogue");
  try {
    const q = encodeURIComponent($("#fq").value.trim());
    const t = $("#ftype").value;
    const r = await api("/api/frameworks?q=" + q + (t ? "&type=" + t : ""));
    const res = r.results || [];
    if (!res.length) { out.innerHTML = '<p class="muted">No catalogue entries matched.</p>'; return; }
    out.innerHTML = '<div class="tablewrap" style="margin-top:12px"><table><caption>Catalogue registry ' + esc(txt(r.registry && r.registry.version)) +
      "</caption><thead><tr><th>Id</th><th>Name</th><th>Type</th><th>Evidence status</th></tr></thead><tbody>" +
      res.map((x) => "<tr><td>" + esc(txt(x.id)) + "</td><td>" + esc(txt(x.name)) + "</td><td>" + esc(txt(x.type)) +
        "</td><td>" + esc(txt(x.evidence_status)) + "</td></tr>").join("") + "</tbody></table></div>";
  } catch (e) { out.innerHTML = errorBanner(e); }
}

async function loadTemplate(id) {
  try {
    const t = await api("/api/templates/" + id);
    const req = t.request || t.example || {};
    const body = { objective: (req.objective || "Work through the " + id + " template."), method: id, inputs: req.inputs || {} };
    state.session = await post("/api/sessions", body);
    show("new"); renderNew();
  } catch (e) { $("#panel-frames").insertAdjacentHTML("afterbegin", errorBanner(e)); }
}

/* ---------- status ---------- */
RENDERERS.status = function () {
  const p = $("#panel-status");
  p.innerHTML = '<div class="card">' + loading("Reading the local status") + "</div>";
  api("/api/health").then((h) => {
    state.health = h;
    let html = '<div class="card"><div class="row" style="justify-content:space-between"><h2>Status</h2>' +
      '<span class="badge ' + (h.status === "ok" ? "" : "warn") + '">' + esc(txt(h.status)) + "</span></div>" +
      kv([["Checked at", h.checked_at], ["Sandbox", h.sandbox], ["Model assistance configured", h.model_assistance],
          ["Case store directory", h.case_store && h.case_store.dir],
          ["Cases", h.case_store && h.case_store.cases], ["Versions", h.case_store && h.case_store.versions],
          ["Sign-offs", h.case_store && h.case_store.signoffs],
          ["Request log", h.request_log && h.request_log.enabled ? h.request_log.path : "disabled"]]) +
      (h.problems && h.problems.length ? banner("blocked", "Problems", "<ul>" + h.problems.map((x) => "<li>" + esc(x) + "</li>").join("") + "</ul>") : "") +
      "<h3>Checks</h3><pre class=\"json\">" + esc(JSON.stringify(h.checks, null, 1)) + "</pre></div>";
    p.innerHTML = html;
    const pill = $("#healthpill");
    if (pill) { pill.className = "pill " + (h.status === "ok" ? "ok" : "bad"); pill.lastElementChild.textContent = h.status === "ok" ? "local - ok" : "local - " + h.status; }
  }).catch((e) => { p.innerHTML = '<div class="card">' + errorBanner(e) + "</div>"; });
};

/* ---------- drawer (chat) ---------- */
function openDrawer(tab) {
  const d = $("#drawer");
  d.hidden = false;
  d.querySelectorAll(".dtab").forEach((t) => t.setAttribute("aria-selected", String(t.dataset.dtab === tab)));
  d.querySelectorAll(".dpanel").forEach((s) => { s.hidden = s.dataset.dpanel !== tab; });
  if (tab === "assistant") fillAssistantDrawer();
}
function fillAssistantDrawer() {
  const box = $("#dassist");
  box.innerHTML = loading("Checking the local configuration");
  api("/api/assist/config").then((cfg) => {
    state.assist = cfg;
    box.innerHTML = "<h3>Assistant</h3><p class=\"sub\">" +
      esc(cfg.enabled ? ("Model assistance is configured on this server (" + (cfg.provider || "") + ").")
                       : (cfg.reason || "Model assistance is not configured on this server.")) + "</p>" +
      "<p class=\"sub\">The model proposes; the code validates and computes. <strong>The model writes no numbers.</strong></p>" +
      '<button class="btn primary" id="dassistopen">Open the assistant</button>' +
      '<div id="dassistout"></div>';
    const b = $("#dassistopen");
    if (b) b.onclick = () => { $("#drawer").hidden = true; show("assistant"); };
  }).catch((e) => { box.innerHTML = errorBanner(e); });
}

/* ---------- modal ---------- */
function openModal(title, bodyHtml, confirmLabel, onConfirm) {
  const m = $("#modal");
  m.innerHTML = '<div class="box" role="document"><h2 id="modaltitle">' + esc(title) + "</h2>" + bodyHtml +
    '<div class="row" style="margin-top:16px;justify-content:flex-end"><button class="btn" id="mcancel">Cancel</button>' +
    '<button class="btn primary" id="mok">' + esc(confirmLabel) + "</button></div></div>";
  m.hidden = false;
  $("#mcancel").onclick = () => { m.hidden = true; };
  $("#mok").onclick = async () => { m.hidden = true; await onConfirm(); };
  $("#mok").focus();
}

/* ---------- boot ---------- */
async function boot() {
  $("#railtoggle").onclick = () => {
    const open = document.body.classList.toggle("rail-open");
    $("#railtoggle").setAttribute("aria-expanded", String(open));
    try { localStorage.setItem("bp-rail", open ? "open" : "closed"); } catch (e) {}
  };
  try { if (localStorage.getItem("bp-rail") === "open") { document.body.classList.add("rail-open"); $("#railtoggle").setAttribute("aria-expanded", "true"); } } catch (e) {}
  const pricing = $("#pricingpill"); if (pricing) pricing.onclick = () => openModal("Pricing (illustrative, not yet available in v1)",
    "<p>Three tiers, as supplied by the owner. Not wired to a payment system.</p>" +
    '<table><thead><tr><th>Tier</th><th>Price</th></tr></thead><tbody>' +
    '<tr><td>Starter</td><td>$14.99</td></tr><tr><td>Pro</td><td>$29.99</td></tr><tr><td>Studio</td><td>$49.99</td></tr></tbody></table>',
    "Close", async () => {});
  const account = $("#accountpill"); if (account) account.onclick = () => openModal("My account",
    "<p>This product runs as a single local user on this machine. No account, login or password is required or stored.</p>", "Close", async () => {});
  const signup = $("#signuppill"); if (signup) signup.onclick = () => openModal("Sign up",
    "<p>Sign up is coming soon. v1 is local single-user, so there is nothing to sign up for yet.</p>", "Close", async () => {});
  $("#chatbtn").onclick = () => { const d = $("#drawer"); if (d.hidden) openDrawer("assistant"); else d.hidden = true; };
  $("#drawerclose").onclick = () => { $("#drawer").hidden = true; $("#chatbtn").focus(); };
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("#modal").hidden) { $("#modal").hidden = true; return; }
    if (!$("#drawer").hidden) { $("#drawer").hidden = true; $("#chatbtn").focus(); }
  });
  $$(".dtab").forEach((t) => { t.onclick = () => openDrawer(t.dataset.dtab); });
  $("#locale").onchange = (e) => { state.locale = e.target.value; try { localStorage.setItem("bp-locale", state.locale); } catch (err) {} };
  try { const l = localStorage.getItem("bp-locale"); if (l && LOCALES[l]) { state.locale = l; $("#locale").value = l; } } catch (e) {}

  const results = await Promise.allSettled([
    api("/api/presets").then((d) => { state.presets = d || {}; }),
    api("/api/methods").then((d) => { state.methods = d || []; }),
    api("/api/currencies").then((d) => { state.currencies = (d && d.currencies) || []; }),
    api("/api/assist/config").then((d) => { state.assist = d; })
  ]);
  const failed = results.filter((r) => r.status === "rejected");
  if (failed.length) {
    $("#panel-home").insertAdjacentHTML("afterbegin", banner("blocked", "The local API did not answer completely",
      "<div>" + esc(failed[0].reason && failed[0].reason.message ? failed[0].reason.message : String(failed[0].reason)) + "</div>"));
  }
  window.addEventListener("hashchange", route);
  route();

  /* the case that was open last time */
  let remembered = null;
  try { remembered = localStorage.getItem("bp-case"); } catch (e) {}
  if (remembered) {
    try { await openCase(remembered); } catch (e) { /* the case was removed; the shelf shows what is there */ }
  }
}
boot();
