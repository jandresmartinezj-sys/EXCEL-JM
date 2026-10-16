"use strict";
// JARVIZ · aplicación web (PWA). Todo el texto se inserta con textContent (sin HTML de datos).

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* modo privado */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* */ } },
};
let token = store.get("jz_token");
let me = null;

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null) el.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined) el.append(c instanceof Node ? c : String(c));
  return el;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}), ...(opts.headers || {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401) { logoutLocal(); throw new Error("Sesión expirada"); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Error " + res.status);
  return data;
}

const fmt = (v, unit) => {
  if (v === null || v === undefined) return "No disponible";
  if (unit === "COP" || unit === "COP/h") return "$" + Math.round(v).toLocaleString("es-CO") + (unit === "COP/h" ? "/h" : "");
  if (unit === "%") return (v * 100).toFixed(1) + "%";
  if (typeof v === "number") return v.toLocaleString("es-CO", { maximumFractionDigits: 1 });
  return String(v);
};
const STATUS = { pending: "Pendiente", running: "En ejecución", awaiting_approval: "Esperando aprobación", completed: "Completada", failed: "Fallida", cancelled: "Cancelada", approved: "Aprobada", rejected: "Rechazada" };

// ------------------------------------------------------------- sesión
function show(id) { $$(".screen").forEach((s) => s.classList.add("hidden")); $(id).classList.remove("hidden"); }
function logoutLocal() { token = null; store.del("jz_token"); show("#login"); }

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  $("#login-error").textContent = "";
  try {
    const r = await api("/api/auth/login", { method: "POST", body: { username: f.get("username"), password: f.get("password") } });
    token = r.token; store.set("jz_token", token);
    await boot();
  } catch (err) { $("#login-error").textContent = err.message; }
});

async function boot() {
  if (!token) return show("#login");
  try { me = await api("/api/me"); } catch { return; }
  if (me.role === "client") { $("#login-error").textContent = "Usa el portal de clientes."; return logoutLocal(); }
  show("#app");
  $$(".owner-only").forEach((el) => el.classList.toggle("hidden", me.role !== "owner"));
  go("home");
  const q = new URLSearchParams(location.search).get("q");
  if (q) { history.replaceState(null, "", "/"); go("chat"); send(q); }
}

// ------------------------------------------------------------- navegación
const loaders = { home: loadHome, chat: loadChat, tasks: loadTasks, approvals: loadApprovals, more: () => loadSub("clients") };
function go(view) {
  $$(".view").forEach((v) => v.classList.add("hidden"));
  $("#v-" + view).classList.remove("hidden");
  $$(".tabbar button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  loaders[view]().catch((e) => console.warn(e));
}
$$(".tabbar button").forEach((b) => b.addEventListener("click", () => go(b.dataset.view)));
$$(".chipbtn").forEach((b) => b.addEventListener("click", () => { go("chat"); send(b.dataset.q); }));

// ------------------------------------------------------------- inicio
async function loadHome() {
  const d = await api("/api/dashboard");
  $("#demo-banner").classList.toggle("hidden", !d.demo_data);
  $("#mode-chip").textContent = d.llm_mode ? "Modo IA" : "Modo local";
  $("#kpi-asof").textContent = "· " + d.as_of;
  const al = $("#home-alerts"); al.replaceChildren();
  if (!d.alerts.length) al.append(h("li", { class: "empty" }, "Sin alertas abiertas."));
  d.alerts.slice(0, 5).forEach((a) => al.append(alertItem(a, true)));
  const g = $("#kpis"); g.replaceChildren();
  d.kpis.forEach((k) => {
    g.append(h("button", { class: `kpi ${k.state || ""} ${k.available ? "" : "na"}`, onclick: () => kpiDetail(k) },
      h("div", { class: "name" }, k.name), h("div", { class: "val" }, fmt(k.value, k.unit))));
  });
  updateBadge();
}

function kpiDetail(k) {
  const box = $("#kpi-detail");
  box.replaceChildren(
    h("h3", {}, k.name), h("p", {}, fmt(k.value, k.unit) + (k.goal !== null && k.goal !== undefined ? "  ·  meta " + fmt(k.goal, k.unit) : "")),
    h("p", { class: "small" }, "Definición: " + k.definition), h("p", { class: "small mono" }, "Fórmula: " + k.formula),
    h("p", { class: "small" }, "Fuente: " + k.source + " · Responsable: " + k.owner),
    k.missing ? h("p", { class: "small error" }, "Falta: " + k.missing) : null);
  $("#kpi-dialog").showModal();
}

function alertItem(a, compact = false) {
  if (compact) {
    return h("li", { class: "item sev-" + a.severity, onclick: () => { go("more"); loadSub("alerts"); } },
      h("div", { class: "title" }, a.title), h("div", { class: "meta" }, "Acción: " + a.action));
  }
  return h("li", { class: "item sev-" + a.severity },
    h("div", { class: "title" }, a.title),
    h("div", { class: "meta" }, "Por qué importa: " + a.why),
    h("div", { class: "meta" }, "Evidencia: " + a.evidence + " · Confianza: " + a.confidence),
    h("div", { class: "meta" }, "Acción recomendada: " + a.action),
    h("div", { class: "meta" }, "Tu decisión: " + a.decision),
    h("div", { class: "actions" }, h("button", { class: "btn small", onclick: async (e) => { await api(`/api/alerts/${a.id}/ack`, { method: "POST" }); e.target.closest("li").remove(); } }, "Marcar como vista")));
}

// ------------------------------------------------------------- conversación y voz
let ttsOn = store.get("jz_tts") !== "0";
$("#tts-toggle").checked = ttsOn;
$("#tts-toggle").addEventListener("change", (e) => { ttsOn = e.target.checked; store.set("jz_tts", ttsOn ? "1" : "0"); if (!ttsOn) speechSynthesis.cancel(); });

async function loadChat() {
  const list = $("#chat");
  if (list.childElementCount) return;
  const hist = await api("/api/conversation");
  hist.forEach((m) => list.append(h("li", { class: "msg " + m.role }, m.content)));
  list.lastElementChild?.scrollIntoView();
}

function addMsg(role, text, extra) {
  const li = h("li", { class: "msg " + role }, text);
  if (extra) li.append(extra);
  $("#chat").append(li);
  requestAnimationFrame(() => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }));
  return li;
}

async function send(text) {
  text = (text || "").trim();
  if (!text) return;
  addMsg("user", text);
  const pending = addMsg("assistant", "Procesando…");
  try {
    const r = await api("/api/command", { method: "POST", body: { text } });
    pending.textContent = r.speech || "(sin respuesta)";
    const meta = h("details", {}, h("summary", {}, `${STATUS[r.status] || r.status} · tarea #${r.task_id} · ${(r.agents || []).join(", ") || "orquestador"}`),
      h("pre", {}, JSON.stringify(r.detail || {}, null, 2)));
    pending.append(meta);
    window.scrollTo({ top: document.body.scrollHeight });
    speak(r.speech);
    updateBadge();
  } catch (err) { pending.textContent = "Error: " + err.message; }
}

$("#cmd-form").addEventListener("submit", (e) => { e.preventDefault(); const v = $("#cmd").value; $("#cmd").value = ""; send(v); });

function speak(text) {
  if (!ttsOn || !("speechSynthesis" in window) || !text) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "es-CO";
  const v = speechSynthesis.getVoices().find((x) => x.lang?.startsWith("es"));
  if (v) u.voice = v;
  u.onstart = () => $("#stop").classList.remove("hidden");
  u.onend = () => { if (!recognizing) $("#stop").classList.add("hidden"); };
  speechSynthesis.speak(u);
}

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null, recognizing = false;
$("#voice-support").textContent = SR
  ? "Reconocimiento de voz disponible en este navegador."
  : "Este navegador no ofrece reconocimiento de voz: usa el micrófono del teclado de iOS (dictado) en el campo de texto.";

function stopAll() {
  if (rec && recognizing) rec.stop();
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  $("#stop").classList.add("hidden");
}
$("#stop").addEventListener("click", stopAll);

$("#mic").addEventListener("click", () => {
  if (!SR) { $("#cmd").focus(); addMsg("assistant", "Tu navegador no permite reconocimiento de voz aquí. Toca el micrófono del teclado para dictar."); return; }
  if (recognizing) return rec.stop();
  if ("speechSynthesis" in window) speechSynthesis.cancel(); // interrumpe la respuesta en curso
  rec = new SR();
  rec.lang = "es-CO"; rec.interimResults = true; rec.continuous = false; rec.maxAlternatives = 1;
  let finalText = "";
  rec.onstart = () => { recognizing = true; $("#mic").classList.add("on"); $("#listening").classList.remove("hidden"); $("#stop").classList.remove("hidden"); };
  rec.onresult = (ev) => {
    let interim = "";
    for (const r of ev.results) (r.isFinal ? (finalText = r[0].transcript) : (interim += r[0].transcript));
    $("#cmd").value = finalText || interim;
  };
  rec.onerror = (ev) => { if (ev.error === "not-allowed") addMsg("assistant", "Permiso de micrófono denegado. Actívalo en Ajustes de iOS > Safari > Micrófono."); };
  rec.onend = () => {
    recognizing = false; $("#mic").classList.remove("on"); $("#listening").classList.add("hidden"); $("#stop").classList.add("hidden");
    const t = $("#cmd").value.trim();
    if (t) { $("#cmd").value = ""; send(t); }
  };
  rec.start();
});

// ------------------------------------------------------------- tareas y aprobaciones
$("#task-filter").addEventListener("change", loadTasks);
async function loadTasks() {
  const st = $("#task-filter").value;
  const list = await api("/api/tasks" + (st ? "?status=" + st : ""));
  const ul = $("#tasks"); ul.replaceChildren();
  if (!list.length) ul.append(h("li", { class: "empty" }, "Sin tareas."));
  list.forEach((t) => {
    const acts = h("div", { class: "actions" });
    if (["pending", "running"].includes(t.status)) {
      acts.append(h("button", { class: "btn small", onclick: () => setTask(t.id, "completed") }, "Completar"),
        h("button", { class: "btn small", onclick: () => setTask(t.id, "cancelled") }, "Cancelar"));
    }
    ul.append(h("li", { class: "item" }, h("div", { class: "title" }, t.title),
      h("div", { class: "meta" }, h("span", { class: "status " + t.status }, STATUS[t.status]), ` #${t.id} · ${t.agent || "manual"}` + (t.due_date ? " · vence " + t.due_date : "")),
      t.error ? h("div", { class: "meta error" }, "Error: " + t.error) : null, acts));
  });
}
async function setTask(id, status) { try { await api(`/api/tasks/${id}/status`, { method: "POST", body: { status } }); } catch (e) { alert(e.message); } loadTasks(); }

async function loadApprovals() {
  const list = await api("/api/approvals");
  const ul = $("#approvals"); ul.replaceChildren();
  if (!list.length) ul.append(h("li", { class: "empty" }, "Nada por aprobar."));
  list.forEach((a) => {
    const payload = (() => { try { return JSON.parse(a.payload_json); } catch { return {}; } })();
    const acts = h("div", { class: "actions" });
    if (a.status === "pending" && me.role === "owner") {
      acts.append(h("button", { class: "btn small primary", onclick: () => decide(a.id, true) }, "Aprobar"),
        h("button", { class: "btn small danger", onclick: () => decide(a.id, false) }, "Rechazar"));
    }
    ul.append(h("li", { class: "item" }, h("div", { class: "title" }, `${a.action} (nivel ${a.level})`),
      h("div", { class: "meta" }, payload.instruction || payload.description || payload.title || JSON.stringify(payload)),
      h("div", { class: "meta" }, h("span", { class: "status " + (a.status === "pending" ? "pending" : a.status === "approved" ? "completed" : "failed") }, STATUS[a.status]), " · " + (a.reason || "")),
      acts));
  });
  updateBadge();
}
async function decide(id, approve) {
  try { const r = await api(`/api/approvals/${id}/decide`, { method: "POST", body: { approve } }); if (r.note) alert(r.note); }
  catch (e) { alert(e.message); }
  loadApprovals();
}
async function updateBadge() {
  try {
    const n = (await api("/api/approvals")).filter((a) => a.status === "pending").length;
    $("#appr-badge").textContent = n; $("#appr-badge").classList.toggle("hidden", !n);
  } catch { /* */ }
}

// ------------------------------------------------------------- más
$$(".subnav button").forEach((b) => b.addEventListener("click", () => loadSub(b.dataset.sub)));
async function loadSub(name) {
  $$(".subnav button").forEach((b) => b.classList.toggle("active", b.dataset.sub === name));
  $$(".sub").forEach((s) => s.classList.add("hidden"));
  $("#s-" + name).classList.remove("hidden");
  if (name === "clients") {
    const list = await api("/api/clients"); const ul = $("#clients"); ul.replaceChildren();
    if (!list.length) ul.append(h("li", { class: "empty" }, "Sin clientes activos registrados."));
    list.forEach((c) => ul.append(h("li", { class: "item" }, h("div", { class: "title" }, c.name),
      h("div", { class: "meta" }, `${c.plan || "sin plan"} · ${fmt(c.monthly_fee, "COP")}/mes · ${c.hours} h este mes · ${c.rev_per_hour ? fmt(c.rev_per_hour, "COP/h") : "sin horas"} · rentabilidad ${c.state}`))));
  } else if (name === "alerts") {
    const list = await api("/api/alerts"); const ul = $("#alerts"); ul.replaceChildren();
    if (!list.length) ul.append(h("li", { class: "empty" }, "Sin alertas abiertas."));
    list.forEach((a) => ul.append(alertItem(a)));
  } else if (name === "agents") {
    const list = await api("/api/agents"); const ul = $("#agents"); ul.replaceChildren();
    list.forEach((a) => ul.append(h("li", { class: "item" }, h("div", { class: "title" }, a.name),
      h("div", { class: "meta" }, `Estado: ${a.status} · autonomía máx. ${a.max_autonomy}`), h("div", { class: "meta" }, a.purpose),
      a.pending.length ? h("div", { class: "meta" }, "Pendiente: " + a.pending.join("; ")) : null)));
  } else if (name === "audit") {
    if (me.role !== "owner") { $("#audit-integrity").textContent = "Solo el propietario puede ver la auditoría."; return; }
    const a = await api("/api/audit");
    $("#audit-integrity").textContent = a.integrity.ok ? `Cadena íntegra (${a.integrity.checked} registros).` : `¡Cadena rota en el registro ${a.integrity.broken_at_id}!`;
    const ul = $("#audit"); ul.replaceChildren();
    a.entries.forEach((e) => ul.append(h("li", { class: "item" }, `${e.ts}  ${e.actor}  ${e.action}  ${e.target || ""}`)));
  } else if (name === "settings") {
    const s = await api("/api/settings"); $("#autonomy").value = s.max_autonomy;
  }
}
$("#autonomy").addEventListener("change", async (e) => { try { await api("/api/settings/autonomy", { method: "POST", body: { level: +e.target.value } }); } catch (err) { alert(err.message); } });
$("#gen-token").addEventListener("click", async () => {
  const r = await api("/api/auth/personal-token", { method: "POST", body: { label: "Atajo iPhone", days: 90 } });
  const out = $("#token-out"); out.textContent = r.token + "\n\n" + r.warning; out.classList.remove("hidden");
});
$("#run-scheduled").addEventListener("click", async () => {
  const r = await api("/api/scheduled/run", { method: "POST" });
  $("#sched-out").textContent = `Alertas nuevas: ${r.alerts_new} · tareas de obligaciones: ${r.obligation_tasks}`;
});
$("#clear-chat").addEventListener("click", async () => { if (confirm("¿Borrar tu historial de conversación?")) { await api("/api/conversation", { method: "DELETE" }); $("#chat").replaceChildren(); } });
$("#logout").addEventListener("click", async () => { try { await api("/api/auth/logout", { method: "POST" }); } catch { /* */ } logoutLocal(); });

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
boot();
