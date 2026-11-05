"use strict";
// Email-derived text must only ever be inserted as text nodes (see el()), never parsed as HTML.

const CATS = {
  Q1: { name: "Important & Urgent", color: "#dc2626", emoji: "🔴" },
  Q2: { name: "Important, Not Urgent", color: "#d97706", emoji: "🟡" },
  Q3: { name: "Urgent, Not Important", color: "#2563eb", emoji: "🔵" },
  Q4: { name: "Neither", color: "#6b7280", emoji: "⚪" },
};
const ORDER = ["Q1", "Q2", "Q3", "Q4"];
const $ = (id) => document.getElementById(id);
let samples = [];
let digest = null;
let history = [];
let dismissed = {};
let digestKey = "";

function el(tag, props = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "style") n.style.cssText = v;
    else if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const c of children) if (c != null) n.append(c instanceof Node ? c : String(c));
  return n;
}

function hash(s) {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h.toString(36);
}
const fp = (m, i) => hash(`${m.subject}|${m.from}|${m.time}|${i}`);

async function api(path, body) {
  const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {};
  const r = await fetch(path, opt);
  let data = {};
  try { data = await r.json(); } catch (e) { /* non-JSON error page */ }
  if (!r.ok) throw new Error(data.error || `Request failed (HTTP ${r.status})`);
  return data;
}

function emailsToText(emails) {
  return emails.map((m) => `Subject: ${m.subject}\nFrom: ${m.from}\nTime: ${m.time}\n${m.body}`).join("\n---\n");
}

function showError(msg) {
  const e = $("error");
  e.textContent = msg || "";
  e.hidden = !msg;
}

async function init() {
  try {
    const st = await api("/api/status");
    const badge = $("mode-badge");
    if (st.mode === "mock") {
      badge.textContent = "Offline mock model";
      badge.classList.add("mock");
      $("mock-banner").hidden = false;
    } else {
      badge.textContent = st.key_configured ? `Live AI: DeepSeek (${st.model})` : "DeepSeek key missing";
    }
    const s = await api("/api/samples");
    samples = s.scenarios || [];
    for (const sc of samples) $("sample-select").append(el("option", { value: sc.id }, sc.title));
  } catch (e) {
    showError("Could not reach the server: " + e.message);
  }
}

function loadSample() {
  const sc = samples.find((x) => x.id === $("sample-select").value);
  if (!sc) return;
  $("email-input").value = emailsToText(sc.emails);
  $("sample-desc").textContent = `${sc.description} (${sc.emails.length} emails)`;
}

async function run() {
  const text = $("email-input").value;
  showError("");
  if (!text.trim()) return showError("Paste some emails or load a sample first.");
  const btn = $("run");
  btn.disabled = true;
  btn.textContent = "Analysing…";
  try {
    digest = await api("/api/digest", { text });
    history = [];
    digestKey = "dm_" + hash(JSON.stringify(digest.items.map((m) => [m.subject, m.from, m.time])));
    try { dismissed = JSON.parse(localStorage.getItem(digestKey) || "{}"); } catch (e) { dismissed = {}; }
    render();
    addMsg("bot", `Digest ready: ${digest.items.length} emails, ${digest.pending.length} important to-do(s). Ask me anything about it.`);
  } catch (e) {
    showError(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate digest";
  }
}

function dmButton(key) {
  return el("button", { class: "dm-btn", title: "Dismiss / undo", onclick: () => toggleDismiss(key) },
    dismissed[key] ? "Undo" : "✕");
}

function toggleDismiss(key) {
  if (dismissed[key]) delete dismissed[key]; else dismissed[key] = 1;
  try { localStorage.setItem(digestKey, JSON.stringify(dismissed)); } catch (e) { /* storage off */ }
  render();
}

function render() {
  const items = digest.items.map((m, i) => ({ ...m, _fp: fp(m, i) }));
  $("empty-state").hidden = true;
  $("result").hidden = false;
  $("meta").textContent = `${items.length} emails · AI provider: ${digest.provider}`;

  const w = $("warnings");
  w.replaceChildren(...(digest.warnings || []).map((t) => el("div", { class: "warn-box" }, "⚠️ " + t)));

  const live = (arr) => arr.filter((m) => !dismissed[m._fp]).length;
  const pend = items.filter((m) => m.action_needed && (m.category === "Q1" || m.category === "Q2"))
    .sort((a, b) => ORDER.indexOf(a.category) - ORDER.indexOf(b.category) || !a.deadline - !b.deadline);
  const todo = $("todo");
  if (!pend.length) {
    todo.replaceChildren(el("div", { class: "todo ok" }, "🎉 Nothing important is waiting on you."));
  } else {
    todo.replaceChildren(el("div", { class: "todo warn" },
      el("h3", {}, `⚠️ Important to-dos (${live(pend)})`),
      el("ul", {}, ...pend.map((m) => el("li", { class: dismissed[m._fp] ? "dismissed" : "" },
        el("span", { class: "tag", style: `background:${CATS[m.category].color}` }, m.category),
        el("b", {}, m.action),
        m.deadline ? el("span", { class: "deadline" }, "⏰ " + m.deadline) : null,
        el("div", { class: "src" }, `from “${m.subject}” · ${m.from}`),
        dmButton(m._fp))))));
  }

  $("cards").replaceChildren(...ORDER.map((q) => el("div", { class: "card", style: `border-top-color:${CATS[q].color}` },
    el("div", { class: "num", style: `color:${CATS[q].color}` }, live(items.filter((m) => m.category === q))),
    el("div", { class: "label" }, `${CATS[q].emoji} ${CATS[q].name}`))));

  $("quadrants").replaceChildren(...ORDER.map((q) => {
    const list = items.filter((m) => m.category === q);
    return el("div", { class: "quad" },
      el("h3", { style: `border-left-color:${CATS[q].color};color:${CATS[q].color}` },
        `${CATS[q].emoji} ${CATS[q].name} (${live(list)})`),
      ...(list.length ? list.map((m) => el("div", { class: "item" + (dismissed[m._fp] ? " dismissed" : "") },
        el("div", { class: "subj" }, m.subject, m.unclassified ? el("span", { class: "flag" }, "needs manual check") : null),
        el("div", { class: "sum" }, m.summary),
        el("div", { class: "info" }, `${m.from} · ${m.time} · `,
          m.action_needed ? el("span", { class: "act" }, "✅ " + m.action + (m.deadline ? ` (⏰ ${m.deadline})` : ""))
            : "No action needed"),
        dmButton(m._fp))) : [el("div", { class: "hint" }, "(no emails)")]));
  }));
  $("dm-info").textContent = `Dismissed: ${Object.keys(dismissed).length}`;
}

function addMsg(kind, text, via) {
  const m = el("div", { class: "msg " + kind }, text, via ? el("span", { class: "via" }, via) : null);
  $("chat-log").append(m);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
}

async function ask(q) {
  q = q.trim();
  if (!q) return;
  if (!digest) return addMsg("err", "Generate a digest first — I only answer questions about the loaded emails.");
  addMsg("user", q);
  $("chat-input").value = "";
  try {
    const r = await api("/api/ask", { question: q, items: digest.items, history });
    history.push({ role: "user", content: q }, { role: "assistant", content: r.answer });
    addMsg("bot", r.answer, r.provider);
  } catch (e) {
    addMsg("err", e.message);
  }
}

$("load-sample").addEventListener("click", loadSample);
$("sample-select").addEventListener("change", loadSample);
$("run").addEventListener("click", run);
$("clear").addEventListener("click", () => { $("email-input").value = ""; $("sample-desc").textContent = ""; showError(""); });
$("email-input").addEventListener("input", () => {
  const n = $("email-input").value.split(/^\s*-{3,}\s*$/m).filter((b) => b.trim()).length;
  $("count").textContent = n ? `${n} email(s)` : "";
});
$("chat-form").addEventListener("submit", (e) => { e.preventDefault(); ask($("chat-input").value); });
document.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => ask(c.textContent)));
$("toggle-dismissed").addEventListener("click", () => {
  const on = document.body.classList.toggle("hide-dismissed");
  $("toggle-dismissed").textContent = on ? "Show dismissed" : "Hide dismissed";
});
$("restore-all").addEventListener("click", () => {
  dismissed = {};
  try { localStorage.removeItem(digestKey); } catch (e) { /* storage off */ }
  if (digest) render();
});
init();
