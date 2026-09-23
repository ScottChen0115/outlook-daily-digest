"""Development self-test: date range, AppleScript generation, output parsing, report rendering."""
import config
import fetch_emails
import main
import report

# 1) Local date range: 2026-09-21 must map to 00:00 -> next day 00:00
s, e = main.date_range_local("2026-09-21")
assert (s.year, s.month, s.day, s.hour) == (2026, 9, 21, 0), s
assert (e.year, e.month, e.day, e.hour) == (2026, 9, 22, 0), e
print("OK date range:", s, "->", e)

# 2) AppleScript generation: account resolution, date components, inbox lookup
script = fetch_emails.build_script(s, e, "me@example.com")
for token in ('account "me@example.com"', "on mkdate(y, mo, dy, secs)", "on pad(n)",
              "2026", 'date received ≥ d1', 'date received < d2', "my pad(month of dRec as integer)"):
    assert token in script, f"missing: {token}"
assert "«" not in script and "»" not in script, "raw chevron syntax must not appear"
print("OK AppleScript generation")

# 3) AppleScript output parsing (two mock emails, with quotes and newlines in the body)
sample = (
    fetch_emails.MSG_SEP + "\n"
    "[URGENT] Client A project outage\n"
    "Zhang Wei <zhangwei@example.com>\n"
    "2026-09-21T09:12:00\n"
    "System is down,  please\nrespond ASAP!\n" + fetch_emails.MSG_SEP + "\n"
    "Weekly report\n"
    "Li Na <lina@example.com>\n"
    "2026-09-21T14:00:00\n"
    "Progress this week..."
)
emails = fetch_emails._parse_output(sample)
assert len(emails) == 2, emails
assert emails[0]["subject"] == "[URGENT] Client A project outage"
assert "zhangwei@example.com" in emails[0]["from"]
assert emails[0]["time"] == "2026-09-21 09:12"
assert "respond ASAP" in emails[0]["body"] and "!" in emails[0]["body"]
assert emails[1]["body"] == "Progress this week..."
print("OK AppleScript output parsing")

# 4) Full HTML report generated from mock emails
mock = [
    dict(subject="[URGENT] Client A outage needs immediate response",
         **{"from": "Zhang Wei <zhangwei@example.com>"}, time="2026-09-21 09:12",
         importance="high", body="Client reports the system is down...",
         summary="Client A system outage, must be handled now", category="Q1", action_needed=True,
         action="Contact IT ops, investigate, reply to the client", deadline="Today 10:30"),
    dict(**{"from": "Li Na <lina@example.com>"}, subject="Q4 product planning weekly",
         time="2026-09-21 14:00", importance="normal", body="Progress this week...",
         summary="Q4 product planning update", category="Q2", action_needed=True,
         action="Send feedback within this week", deadline=""),
    dict(**{"from": "Admin <admin@example.com>"}, subject="Please confirm receipt",
         time="2026-09-21 16:30", importance="normal", body="Please reply to confirm",
         summary="Routine confirmation", category="Q3", action_needed=False, action="", deadline=""),
    dict(**{"from": "Union <union@example.com>"}, subject="Company sports day sign-up",
         time="2026-09-21 18:00", importance="low", body="Optional participation",
         summary="Sports day sign-up", category="Q4", action_needed=False, action="", deadline=""),
]
pending = [m for m in mock if m["action_needed"] and m["category"] in ("Q1", "Q2")]

# 5) Item fingerprint: stable for identical input, different otherwise
#    (the basis for persisting the browser's 'dismissed' state)
assert report._fp("a", "f", "t") == report._fp("a", "f", "t")
assert report._fp("a", "f", "t") != report._fp("b", "f", "t")
print("OK item fingerprint")

# 6) Demo report rendering: dismiss buttons, section counts, persistence script
#    (the demo file is removed afterwards so real reports are never overwritten)
path = report.generate(mock, pending, "Zhipu (demo)", "2026-09-21")
html_doc = path.read_text(encoding="utf-8")
for token in ('data-fp="', 'dmToggle(this)', 'digest_dismissed_', 'Dismissed ',
              '<section data-q="Q1"', 'dmResetAll', 'id="todo-count"', 'dmToggleView'):
    assert token in html_doc, f"report missing: {token}"
assert html_doc.count('data-fp="') == len(mock) + len(pending), "data-fp count mismatch"
path.unlink()
print("OK demo report rendering (dismiss feature included, demo file cleaned up)")
