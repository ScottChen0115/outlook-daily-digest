"""Read email for a local time range from the macOS Mail app (Mail.app). Standard library only."""
import logging
import re
import subprocess

import config

logger = logging.getLogger(__name__)

MSG_SEP = "=====MSG====="
_WS_RE = re.compile(r"\s+")

# Possible inbox mailbox names across account types
# (the last entry is the localized Chinese inbox name used by Mail.app)
INBOX_NAMES = ("INBOX", "Inbox", "\u6536\u4ef6\u7bb1")


def build_script(start, end, account):
    """Build the AppleScript: select messages received in [start, end) from the
    account's inbox and output them as separator-delimited plain text
    (subject / sender / ISO time / body).

    Note: all Mail terminology (account/mailbox/message) is referenced inside
    the tell block only; handlers outside the tell block use standard terms
    and no raw «chevron» syntax, which keeps compilation stable.
    """
    # Date constructor: set components one by one to avoid locale-specific
    # date-string parsing issues
    date_builder = '''on mkdate(y, mo, dy, secs)
    set d to current date
    set day of d to 1
    set year of d to y
    set month of d to mo
    set day of d to dy
    set time of d to secs
    return d
end mkdate

on pad(n)
    if n < 10 then return "0" & n
    return n as string
end pad

'''
    inbox_finder = f'''tell application "Mail"
    set d1 to my mkdate({start.year}, {start.month}, {start.day}, {start.hour * 3600 + start.minute * 60 + start.second})
    set d2 to my mkdate({end.year}, {end.month}, {end.day}, {end.hour * 3600 + end.minute * 60 + end.second})

    -- Resolve the account: direct name lookup first, then match by account name / email address
    set theAcct to missing value
    try
        set theAcct to account "{account}"
    end try
    if theAcct is missing value then
        repeat with a in (every account)
            try
                if ((name of a) as string) is "{account}" then set theAcct to a
            end try
            if theAcct is missing value then
                try
                    repeat with ea in (email addresses of a)
                        if (ea as string) is "{account}" then set theAcct to a
                    end repeat
                end try
            end if
        end repeat
    end if
    if theAcct is missing value then error "Account not found in Mail: {account}"

    -- Locate the inbox: prefer INBOX, then match common names
    set theBox to missing value
    try
        set theBox to mailbox "INBOX" of theAcct
    end try
    if theBox is missing value then
        repeat with b in (every mailbox of theAcct)
            if (name of b) is in {{"{INBOX_NAMES[0]}", "{INBOX_NAMES[1]}", "{INBOX_NAMES[2]}"}} then set theBox to b
        end repeat
    end if
    if theBox is missing value then error "Inbox not found for account {account}"

    set sel to (every message of theBox whose date received ≥ d1 and date received < d2)
    set out to ""
    repeat with m in sel
        set out to out & "{MSG_SEP}" & linefeed
        try
            set out to out & (subject of m) & linefeed
        on error
            set out to out & "(no subject)" & linefeed
        end try
        set out to out & (sender of m) & linefeed
        -- Build the ISO time from date components (avoids raw chevron syntax)
        set dRec to date received of m
        set out to out & (year of dRec as string) & "-" & my pad(month of dRec as integer) & "-" & my pad(day of dRec) & "T" & my pad(hours of dRec) & ":" & my pad(minutes of dRec) & linefeed
        try
            set out to out & (content of m) & linefeed
        on error
            set out to out & linefeed
        end try
    end repeat
    return out
end tell
'''
    return date_builder + inbox_finder
def _parse_output(text):
    """Parse AppleScript output into a list of {subject, from, time, importance, body} dicts."""
    emails = []
    for section in text.split(MSG_SEP):
        section = section.lstrip("\r\n")  # strip the newline after the separator
        if not section.strip():
            continue
        lines = section.split("\n", 3)
        if len(lines) < 3:
            continue
        body = _WS_RE.sub(" ", lines[3] if len(lines) > 3 else "").strip()
        emails.append({
            "subject": lines[0].strip() or "(no subject)",
            "from": lines[1].strip(),
            "time": lines[2].strip()[:16].replace("T", " "),
            "importance": "normal",
            "body": body[:config.MAX_EMAIL_CHARS],
        })
    logger.info("Read %d email(s) (account: %s)", len(emails), config.MAIL_ACCOUNT)
    return emails


def get_emails(start_dt, end_dt):
    """Fetch inbox mail received within [start_dt, end_dt) (local-timezone datetimes)."""
    if not config.MAIL_ACCOUNT:
        raise RuntimeError("Please set MAIL_ACCOUNT in .env (the mailbox address to watch)")
    script = build_script(start_dt, end_dt, config.MAIL_ACCOUNT)
    try:
        proc = subprocess.run(["osascript", "-e", script],
                              capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("AppleScript timed out (is Mail.app not responding?)") from e
    if proc.returncode != 0:
        err = proc.stderr.strip()
        if "not allowed" in err.lower() or "-1743" in err:
            raise RuntimeError("Automation permission denied: allow Terminal to control Mail under "
                               "System Settings > Privacy & Security > Automation, or run manually "
                               "once to trigger the consent prompt")
        raise RuntimeError(f"AppleScript failed: {err[:500]}")
    return _parse_output(proc.stdout)
