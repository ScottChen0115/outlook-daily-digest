"""Daily email digest - main entry point (reads mail via the macOS Mail app).

Usage:
    python3 main.py                     # summarize yesterday (default)
    python3 main.py --date 2026-09-21   # backfill a specific date
    python3 main.py --no-open           # do not open the browser
"""
import argparse
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config
import fetch_emails
import notify
import report
import summarize

logger = logging.getLogger("outlook-digest")


def setup_logging():
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in (logging.StreamHandler(sys.stdout),
              logging.FileHandler(config.LOGS_DIR / "run.log", encoding="utf-8")):
        h.setFormatter(fmt)
        root.addHandler(h)


def date_range_local(date_str):
    """Convert a local date (e.g. 2026-09-21) into that day's 00:00 -> next-day 00:00 datetime range."""
    tz = ZoneInfo(config.TIMEZONE)
    d = datetime.strptime(date_str, "%Y-%m-%d")
    start = datetime(d.year, d.month, d.day, tzinfo=tz)
    return start, start + timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description="Daily email digest")
    parser.add_argument("--date", help="which day to summarize (YYYY-MM-DD), default: yesterday")
    parser.add_argument("--force", action="store_true", help="regenerate even if the report exists")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = parser.parse_args()

    yesterday = (datetime.now(ZoneInfo(config.TIMEZONE)) - timedelta(days=1)).strftime("%Y-%m-%d")
    date_str = args.date or yesterday
    out_path = config.REPORTS_DIR / f"daily_digest_{date_str}.html"
    if out_path.exists() and not args.force:
        logger.info("✅ Report for %s already exists (%s); skipping. Use --force to regenerate.", date_str, out_path)
        subprocess.run(["open", str(out_path)], check=False)
        return

    logger.info("====== Generating daily digest for %s ======", date_str)

    # 1) Read email from the system Mail app
    start_dt, end_dt = date_range_local(date_str)
    emails = fetch_emails.get_emails(start_dt, end_dt)
    if not emails:
        logger.info("📭 No email in this time range; generating an empty report.")

    # 2) AI summarization (on failure, fall back to an unsummarized report so output is still produced)
    provider = "none"
    if emails:
        try:
            classified, pending, provider = summarize.summarize_emails(emails)
        except Exception as e:
            logger.error("AI summarization failed: %s; generating an unsummarized report.", e)
            classified = [dict(m, summary="(AI summary failed - open the email to read the original)",
                               category="Q4", action_needed=False, action="", deadline="")
                          for m in emails]
            pending = []
    else:
        classified, pending = [], []

    # 3) Generate the HTML report
    path = report.generate(classified, pending, provider, date_str)
    if not args.no_open:
        subprocess.run(["open", str(path)], check=False)  # open in the browser on macOS

    # 4) System notification: remind about pending important items
    if pending:
        first = pending[0]
        notify.notify(
            title=f"📬 {date_str} daily digest: {len(pending)} pending items",
            message=f"Top priority: {first['action'] or first['subject'][:40]}",
        )
    else:
        notify.notify(title=f"📬 {date_str} daily digest is ready",
                      message="No pending important items today ✅")
    logger.info("====== Done. Report: %s ======", path)


if __name__ == "__main__":
    setup_logging()
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        logger.exception("Run failed")
        notify.notify(title="❌ Daily digest failed", message="See logs/run.log for details")
        sys.exit(1)
