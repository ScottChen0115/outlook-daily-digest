# Team handover: Email Digest Agent web demo

> **Demo link: https://email-digest-agent-eo4s.onrender.com** (after a period of inactivity, the first load can take about a minute)
> Deadline: **Sunday 8 November, 23:59**, submit in FeedbackFruits.
> Code: repo `ScottChen0115/outlook-daily-digest`, branch `cursor/web-demo-agent`, folder `webdemo/` ([PR #1](https://github.com/ScottChen0115/outlook-daily-digest/pull/1)).

## 1. The three things to submit

| Item | File / content | Status |
|---|---|---|
| Demo link | https://email-digest-agent-eo4s.onrender.com | ✅ Live and verified |
| Test log (~300 words) | [`webdemo/docs/submission/test-log.md`](submission/test-log.md) (Chinese reference: [`test-log.zh.md`](submission/test-log.zh.md)) | 📝 Awaiting final team review |
| Sample scenarios (3–5) | [`webdemo/docs/submission/sample-scenarios.md`](submission/sample-scenarios.md) | 📝 Awaiting final team review |

**Each person** must also give their own peer feedback to 2 other teams.

## 2. What it is

The original project only read email from the macOS Mail app. The web version takes **pasted emails** instead and runs on a server, so reviewers can use it from a link.

Features:
- Sorts a day's emails into the **Eisenhower matrix**: Important & Urgent, Important, Urgent, or Neither.
- Writes a one-line summary of each email and extracts the **to-do and deadline**.
- Pins important to-dos at the top. Each one can be dismissed or restored, and that state survives a reload.
- **Chat panel**: ask questions about the loaded inbox ("What do I need to do today?", "What can I ignore?"). It answers only from the emails and does not make things up.
- Three built-in sample inboxes: office worker, student, and edge cases. The edge cases cover prompt injection, HTML, Chinese text, an empty subject, and a duplicate.

AI calls use a single provider, the **DeepSeek** API (model `deepseek-flash`). Without a key the app falls back to an offline mock model and shows a yellow banner. The deployed site always uses the real model and **never** shows the mock.

## 3. Current status

| Item | Status |
|---|---|
| Web demo code | ✅ Done |
| Automated tests | ✅ 27/27 pass |
| Labelled set (24 emails, scored by `eval.py`) | ✅ Quadrant 23/24, action flag 24/24 (live DeepSeek) |
| Three sample scenarios | ✅ 18/18 checks, both locally and on the live site |
| Prompt injection (3 runs) | ✅ Not fooled in any run |
| Chat completeness (2 questions × 3 runs) | ✅ 6/6, both locally and on the live site |
| Render deployment | ✅ Live, using the real model |

The expected labels in the labelled set were drafted with AI assistance, then reviewed and adopted by the team.

## 4. Issues found in testing

Fixed:
- "What is urgent?" listed only one of three urgent emails. The rewritten prompt fixed it.
- Chat answers showed raw Markdown asterisks; they are now plain text.
- A model reply of the string `"false"` created fake to-dos.
- Emails the model skipped were silently put in the "ignore" quadrant; they are now flagged "needs manual check".
- Duplicate emails were listed twice; they are now merged.
- Oversized input dropped the connection (seen on macOS only); it now shows a "too large" message.

Chose not to fix:
- The Client B contract due Friday: across runs it is sometimes Important & Urgent and sometimes Important. Both are defensible.
- After a new digest is generated, the old chat messages stay on screen. This is cosmetic.
- Our test emails are synthetic and few; real long email threads are untested.

## 5. Run locally

```bash
git checkout cursor/web-demo-agent
cd webdemo
cp .env.example .env                       # add DEEPSEEK_API_KEY and set LLM_MODE=live
python3 server.py                          # open http://localhost:8000
python3 -m unittest discover -s tests      # automated tests
python3 eval.py                            # score against the labelled set
```

You only need Python 3.10 or newer; there are no packages to install. **The API key is not in the repo**; ask Scott if you need it.

## 6. Deployment notes

- Hosted on Render's free tier and auto-deployed from the `cursor/web-demo-agent` branch. Pushing to that branch updates the live site within a few minutes.
- The key is stored only on the service's **Environment** page in the Render dashboard. If the key has a problem, the page shows "the AI service is not configured correctly".
- The service sleeps after 15 minutes of inactivity. **During the review window, open the link once each day.**
- Every digest uses DeepSeek balance. The balance is currently healthy, and Scott checks it regularly.

## 7. Remaining tasks

| # | Task | Owner | Due |
|---|---|---|---|
| 1 | Review `submission/test-log.md` and `submission/sample-scenarios.md`, including whether to keep the closing AI-use note | All | 7 Nov |
| 2 | Check the redacted part of the AI-use rule in the assignment screenshot against the course page | | 7 Nov |
| 3 | Open the link on your own laptop and phone and try all 5 sample scenarios | All | 7 Nov |
| 4 | Submit the link, test log and scenarios in FeedbackFruits | | before 8 Nov |
| 5 | Each person gives their own peer feedback to 2 other teams | Everyone | 8 Nov 23:59 |
| 6 | Open the link once a day during the review window so it doesn't sleep | | review window |

## 8. File guide

| File | Purpose |
|---|---|
| `webdemo/docs/submission/` | **The test log and sample scenarios to submit** |
| `webdemo/server.py` | Web server and API |
| `webdemo/digest.py` | Core logic: email parsing, classification, chat |
| `webdemo/llm.py` | DeepSeek calls and the mock switch |
| `webdemo/mock_model.py` | Offline mock model, used only for demos and tests without a key |
| `webdemo/static/` | Front-end page |
| `webdemo/samples/sample_inboxes.json` | The 3 sample inboxes |
| `webdemo/samples/eval_set.json` | 24 labelled emails (labels adopted after team review) |
| `webdemo/tests/test_agent.py` | Automated tests |
| `webdemo/eval.py` | Accuracy evaluation script |
| `webdemo/docs/sample-scenarios.md` | Early scenario draft and manual test plan (superseded by `submission/`) |
| `webdemo/docs/simulated-test-log.md` | Early mock-model dry run; **do not submit** |
| `render.yaml` | Render deployment config |
