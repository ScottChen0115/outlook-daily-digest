"""Generate the color-coded HTML daily report and write it to disk."""
import hashlib
import html
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


def _esc(s):
    return html.escape(str(s or ""))


def _fp(subject, from_, time_):
    """Stable per-item fingerprint: identical items keep the same id across
    regenerations, which lets the browser remember the 'dismissed' state."""
    raw = f"{subject}|{from_}|{time_}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]


def _todo_section(pending):
    if not pending:
        return ('<div class="todo ok">🎉 Nothing pending today — keep it up!</div>')
    rows = []
    for p in pending:
        c = config.CATEGORIES[p["category"]]
        deadline = f' <span class="deadline">⏰ Due: {_esc(p["deadline"])}</span>' if p["deadline"] else ""
        fp = _fp(p["subject"], p["from"], p["time"])
        rows.append(
            f'<li data-fp="{fp}"><button class="dm-btn" onclick="dmToggle(this)">✕</button>'
            f'<span class="tag" style="background:{c["color"]}">{c["emoji"]} {c["name"]}</span>'
            f'<b>{_esc(p["action"])}</b>'
            f'<span class="meta"> | Source: {_esc(p["subject"])} ({_esc(p["from"])})</span>{deadline}</li>'
        )
    return (
        '<div class="todo warn">'
        f'<h2 id="todo-count">⚠️ Pending important items ({len(pending)})</h2><ul>' + "".join(rows) + "</ul></div>"
    )


def _cards(classified):
    cards = []
    for key in config.CATEGORY_ORDER:
        c = config.CATEGORIES[key]
        n = sum(1 for x in classified if x["category"] == key)
        cards.append(
            f'<div class="card" style="background:{c["bg"]};border-top:4px solid {c["color"]}">'
            f'<div class="num" data-q="{key}" style="color:{c["color"]}">{n}</div>'
            f'<div class="label">{c["emoji"]} {c["name"]}</div></div>'
        )
    return f'<div class="cards">{"".join(cards)}</div>'


def _tables(classified):
    parts = []
    for key in config.CATEGORY_ORDER:
        c = config.CATEGORIES[key]
        items = [x for x in classified if x["category"] == key]
        rows = []
        for m in items:
            action = (f'<span class="act">✅ {_esc(m["action"])}</span>'
                      if m["action_needed"] else '<span class="none">No action needed</span>')
            deadline = f' / ⏰{_esc(m["deadline"])}' if m["deadline"] else ""
            fp = _fp(m["subject"], m["from"], m["time"])
            rows.append(
                f'<tr data-fp="{fp}">'
                f'<td class="subj"><b>{_esc(m["subject"])}</b><div class="sum">{_esc(m["summary"])}</div></td>'
                f"<td>{_esc(m['from'])}</td><td>{_esc(m['time'])}</td>"
                f"<td>{action}{deadline}</td>"
                f'<td class="opcell"><button class="dm-btn" onclick="dmToggle(this)">✕</button></td></tr>'
            )
        table_body = "".join(rows) or '<tr><td colspan="5" class="none">(no emails)</td></tr>'
        parts.append(
            f'<section data-q="{key}">'
            f'<h2 style="color:{c["color"]};border-left:6px solid {c["color"]};padding-left:10px">'
            f'{c["emoji"]} {c["name"]} ({len(items)})</h2>'
            f'<table style="background:{c["bg"]}"><thead><tr>'
            "<th>Subject / Summary</th><th>From</th><th>Time</th><th>Action</th>"
            '<th class="op">Dismiss</th></tr></thead>'
            f"<tbody>{table_body}</tbody></table></section>"
        )
    return "\n".join(parts)
def generate(classified, pending, provider, date_str):
    """Generate the HTML report and return its path."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Email Digest {date_str}</title>
<style>
 body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;max-width:1080px;margin:24px auto;padding:0 16px;color:#111827;background:#fff}}
 h1{{font-size:24px}} .meta{{color:#6b7280;font-size:13px}}
 .cards{{display:flex;gap:12px;margin:18px 0;flex-wrap:wrap}}
 .card{{flex:1;min-width:150px;border-radius:10px;padding:14px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
 .card .num{{font-size:32px;font-weight:700}} .card .label{{font-size:14px;margin-top:4px}}
 .todo{{border-radius:10px;padding:14px 18px;margin:18px 0}}
 .todo.warn{{background:#fff7ed;border:1px solid #fdba74}}
 .todo.ok{{background:#f0fdf4;border:1px solid #86efac;color:#15803d}}
 .todo ul{{margin:8px 0 0;padding-left:20px;line-height:2}}
 .todo li{{margin:6px 0}} .deadline{{color:#dc2626;font-size:13px}}
 .tag{{color:#fff;font-size:12px;border-radius:6px;padding:2px 8px;margin-right:8px}}
 table{{width:100%;border-collapse:collapse;margin:10px 0 28px;font-size:14px;border-radius:8px;overflow:hidden}}
 th{{background:rgba(0,0,0,.05);padding:8px 10px;text-align:left;font-size:13px}}
 td{{padding:10px;border-top:1px solid rgba(0,0,0,.06);vertical-align:top}}
 .sum{{color:#4b5563;font-size:13px;margin-top:4px}}
 .act{{color:#b45309}} .none{{color:#9ca3af}}
 footer{{color:#9ca3af;font-size:12px;margin:24px 0;border-top:1px solid #e5e7eb;padding-top:12px}}
 .toolbar{{display:flex;gap:10px;align-items:center;margin:10px 0 4px;font-size:13px;color:#6b7280}}
 .toolbar button,.dm-btn{{font-size:12px;padding:3px 9px;border:1px solid #d1d5db;border-radius:6px;background:#fff;color:#6b7280;cursor:pointer}}
 .toolbar button:hover{{background:#f3f4f6}}
 .dm-btn{{float:right;margin-left:8px;color:#9ca3af;opacity:0;transition:opacity .15s}}
 tr:hover .dm-btn,li:hover .dm-btn{{opacity:1}}
 tr.dismissed td,li.dismissed{{opacity:.4}}
 tr.dismissed .subj b,li.dismissed b{{text-decoration:line-through}}
 tr.dismissed .dm-btn,li.dismissed .dm-btn{{opacity:1;color:#2563eb}}
 td.opcell{{width:44px;text-align:right}} th.op{{width:44px}}
 body.hide-dismissed tr.dismissed,body.hide-dismissed li.dismissed{{display:none}}
</style></head><body data-date="{date_str}">
<h1>📬 Daily Email Digest</h1>
<div class="meta">Date: {date_str} | Total emails: {len(classified)} | Generated: {now} | AI provider: {_esc(provider)}</div>
<div class="toolbar"><span id="dm-info"></span><button id="dm-toggle-view" onclick="dmToggleView()">🙈 Hide dismissed</button><button onclick="dmResetAll()">↩️ Restore all</button></div>
{_todo_section(pending)}
{_cards(classified)}
{_tables(classified)}
<footer>Auto-generated by outlook-daily-digest · Eisenhower matrix classification</footer>
<script>
var DM_DATE = document.body.dataset.date || "";
var DM_KEY = "digest_dismissed_" + DM_DATE;
var DM_VIEW_KEY = "digest_hideview_" + DM_DATE;
var DM = {{}};
function dmLoad() {{
    try {{ DM = JSON.parse(localStorage.getItem(DM_KEY) || "{{}}"); }} catch (e) {{ DM = {{}}; }}
    if (!DM || typeof DM !== "object") DM = {{}};
}}
function dmSave() {{
    try {{ localStorage.setItem(DM_KEY, JSON.stringify(DM)); }} catch (e) {{}}
}}
function dmToggle(btn) {{
    var el = btn.closest("[data-fp]");
    if (!el) return;
    var fp = el.dataset.fp;
    if (el.classList.contains("dismissed")) {{
        delete DM[fp];
        el.classList.remove("dismissed");
        btn.textContent = "✕";
    }} else {{
        DM[fp] = 1;
        el.classList.add("dismissed");
        btn.textContent = "Undo";
    }}
    dmSave();
    dmRefresh();
}}
function dmToggleView() {{
    var hide = !document.body.classList.contains("hide-dismissed");
    document.body.classList.toggle("hide-dismissed", hide);
    try {{ localStorage.setItem(DM_VIEW_KEY, hide ? "1" : "0"); }} catch (e) {{}}
    var b = document.getElementById("dm-toggle-view");
    if (b) b.textContent = hide ? "👁 Show dismissed" : "🙈 Hide dismissed";
}}
function dmResetAll() {{
    DM = {{}};
    dmSave();
    document.querySelectorAll(".dismissed").forEach(function (el) {{ el.classList.remove("dismissed"); }});
    document.querySelectorAll(".dm-btn").forEach(function (b) {{ b.textContent = "✕"; }});
    dmRefresh();
}}
function dmRefresh() {{
    var n = Object.keys(DM).length;
    var info = document.getElementById("dm-info");
    if (info) info.textContent = "Dismissed " + n;
    document.querySelectorAll("section[data-q]").forEach(function (sec) {{
        var live = sec.querySelectorAll("tr[data-fp]").length - sec.querySelectorAll("tr.dismissed").length;
        var h2 = sec.querySelector("h2");
        if (h2) h2.textContent = h2.textContent.replace(/\\(\\d+\\)$/, "(" + live + ")");
        var num = document.querySelector('.num[data-q="' + sec.dataset.q + '"]');
        if (num) num.textContent = live;
    }});
    var todo = document.querySelector(".todo.warn");
    if (todo) {{
        var live = todo.querySelectorAll("li[data-fp]").length - todo.querySelectorAll("li.dismissed").length;
        var t = document.getElementById("todo-count");
        if (t) t.textContent = "⚠️ Pending important items (" + live + ")";
    }}
}}
dmLoad();
document.querySelectorAll("[data-fp]").forEach(function (el) {{
    if (DM[el.dataset.fp]) {{
        el.classList.add("dismissed");
        var b = el.querySelector(".dm-btn");
        if (b) b.textContent = "Undo";
    }}
}});
try {{
    if (localStorage.getItem(DM_VIEW_KEY) === "1") {{
        document.body.classList.add("hide-dismissed");
        var b = document.getElementById("dm-toggle-view");
        if (b) b.textContent = "👁 Show dismissed";
    }}
}} catch (e) {{}}
dmRefresh();
</script>
</body></html>"""
    path = config.REPORTS_DIR / f"daily_digest_{date_str}.html"
    path.write_text(html_doc, encoding="utf-8")
    logger.info("HTML report written: %s", path)
    return path
