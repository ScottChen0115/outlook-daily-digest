# 📬 Daily Email Digest (outlook-daily-digest)

Automatically summarizes the previous day's email from the macOS **Mail** app every morning at 8:00:

- Classifies messages into the **Eisenhower matrix** (🔴 Important & Urgent / 🟡 Important, Not Urgent / 🔵 Urgent, Not Important / ⚪ Neither)
- Generates a color-coded HTML report (opens in your browser automatically)
- Pins **pending important items** at the top and fires a macOS notification
- **One-click dismissal** of any item inside the report (hover to reveal the ✕ button) — survives refresh, undoable, restorable in one click
- Dual AI providers: **Zhipu BigModel (primary) + DeepSeek (fallback)** with automatic failover
- Zero third-party dependencies — Python standard library only
- **Zero Microsoft authorization**: email is read locally from the macOS Mail app; no Azure registration, no IT admin consent

## How it works

AppleScript asks the system Mail app for messages received "yesterday" in the configured account's inbox, hands them to an LLM for summarization and classification, then writes a local HTML report. All data only flows to the LLM provider you configure — no other third-party servers.

## Project layout

```
outlook-daily-digest/
├── main.py          # Entry point (supports backfilling any date)
├── config.py        # Configuration loader (reads .env)
├── fetch_emails.py  # Reads mail from the Mail app via AppleScript
├── llm.py           # Provider layer: Zhipu (primary) + DeepSeek (fallback)
├── summarize.py     # AI summary + quadrant classification + to-do extraction
├── report.py        # Color-coded HTML report (with one-click dismissal)
├── notify.py        # macOS system notifications
├── run_daily.sh     # Scheduled / manual run script
├── selftest.py      # Dev self-test (python3 selftest.py)
├── com.cline.outlook-digest.plist  # launchd schedule definition
├── .env.example     # Configuration template (copy to .env)
├── .env             # Your secrets (never commit; excluded by .gitignore)
├── reports/         # Generated reports (not committed)
└── logs/            # Run logs (not committed)
```

## First-time setup (3 steps, about 10 minutes)

### Step 1: add your account to the macOS Mail app (one time)

1. Open **System Settings → Internet Accounts → Add Account → Microsoft Exchange**
2. Enter your email address and password and complete the sign-in
   (if your organization redirects to a single sign-on page, just sign in as usual)
3. Make sure the **Mail** toggle is enabled for the account
4. Open the Mail app and confirm the account's **inbox** is visible and syncing

### Step 2: fill in the configuration

Copy the template and fill in your own values:

```bash
cp .env.example .env
```

Then edit `.env`:

```ini
MAIL_ACCOUNT=your.address@example.com
ZHIPU_API_KEY=your-zhipu-key   # get one at https://open.bigmodel.cn
DEEPSEEK_API_KEY=your-deepseek-key   # optional fallback, may stay empty
```

> `MAIL_ACCOUNT` must exactly match the account address shown in the Mail app.
> If you have several mailboxes, the tool reads only this one account's inbox.

### Step 3: first run + authorization

```bash
cd ~/program/outlook-daily-digest
python3 main.py --force
```

**On the first run macOS will ask**: "Terminal wants to control Mail" → click **OK**.
This is a one-time grant; afterwards the scheduled job reads mail silently.

## Schedule it daily at 8:00

```bash
cd ~/program/outlook-daily-digest
# First edit com.cline.outlook-digest.plist: replace both /Users/YOUR_USERNAME/...
# paths with your actual project directory
cp com.cline.outlook-digest.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cline.outlook-digest.plist
```

- Check the job: `launchctl list | grep outlook`
- Unload it: `launchctl unload ~/Library/LaunchAgents/com.cline.outlook-digest.plist`

> ⚠️ The Mac must be **powered on and awake** at 8:00 for the job to fire;
> if it was asleep, backfill manually after waking: `bash run_daily.sh` (summarizes yesterday by default).
> You can also schedule a wake-up under System Settings → Battery / Energy Saver.

## Common commands

```bash
python3 main.py                     # summarize yesterday (opens the existing report if present)
python3 main.py --date 2026-09-21   # backfill a specific date
python3 main.py --force             # regenerate even if the report already exists
python3 main.py --no-open           # do not open the browser
tail -f logs/run.log                # follow the run log
```

## Troubleshooting

- **Report says "AI summary failed"**: check whether the keys in `.env` are valid; logs are in `logs/run.log`
- **"No automation permission"**: System Settings → Privacy & Security → Automation, enable Terminal → Mail;
  or run `tccutil reset AppleEvents`, then run manually once to trigger the prompt again
- **"Account not found"**: make sure `MAIL_ACCOUNT` in `.env` matches the account address in the Mail app
- **Inbox only**: the tool reads only the selected account's inbox — no subfolders, no sent mail
- **Switch models**: change `ZHIPU_MODEL` in `.env` (e.g. the free `glm-5.3-flash` or the stronger `glm-4.6`)
- **GLM Coding Plan subscriber**: plan quota is billed separately from the pay-as-you-go API balance —
  set `ZHIPU_STYLE=anthropic` (and `ZHIPU_MODEL=glm-4.6`) in `.env` to route requests through the Coding Plan channel
- **Too many/too few emails**: tune `MAX_EMAILS` and `BATCH_SIZE` in `.env`
- **Summary language**: set `SUMMARY_LANG=en` or `SUMMARY_LANG=zh` in `.env` (default: `en`)
