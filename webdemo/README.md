# Email Digest Agent — web demo

A browser version of `outlook-daily-digest` that anyone can try from a link. Paste a day's emails
(or load a sample inbox) and the agent:

- classifies every email into the **Eisenhower matrix** (Important & Urgent / Important / Urgent / Neither),
- writes a one-line summary and extracts the **to-do and deadline**,
- pins the **important to-dos** at the top (one-click dismiss, remembered per digest),
- answers **questions about that inbox** in a chat panel ("What do I need to do today?", "What can I ignore?").

It reuses the original prompt, Zhipu → DeepSeek failover and quadrant rules, but replaces the macOS
Mail/AppleScript input with pasted text so it runs on any server. Python standard library only.

## Run locally

```bash
cd webdemo
cp .env.example .env        # optional: add ZHIPU_API_KEY and/or DEEPSEEK_API_KEY
python3 server.py           # http://localhost:8000
```

Without a key the app runs on the **offline mock model** (keyword rules) and says so in a yellow
banner. The mock exists so the pipeline can be demonstrated and tested; its classifications are not
evidence of AI quality. Set `LLM_MODE=live` for reviewer-facing deployments so a missing or broken
key shows an error instead of silently falling back.

## Deploy (public demo link)

- **Render**: "New → Blueprint", pick this repo; `render.yaml` at the repo root deploys `webdemo/`.
  Add `ZHIPU_API_KEY` (and optionally `DEEPSEEK_API_KEY`) in the dashboard.
- **Any Docker host** (Fly.io, Railway, Hugging Face Spaces, a VPS): `docker build -t digest webdemo && docker run -p 8000:8000 -e ZHIPU_API_KEY=... digest`

Free tiers sleep when idle; open the link once before reviewers start so the first request is not slow.

## Input format

Separate emails with a line containing only `---`. Header lines `Subject:`, `From:`, `Time:` are
optional; everything after the first non-header line is the body.

```
Subject: Budget approval needed
From: Maria Lopez <maria@company.com>
Time: 2026-11-02 09:15
Please approve the Q1 budget by tomorrow noon.
---
Subject: Tech Weekly Newsletter
From: news@techweekly.io
This week: 10 productivity tools...
```

The JSON API accepts the same data: `POST /api/digest {"text": "..."}` or `{"emails": [{subject, from, time, body}]}`,
and `POST /api/ask {"question": "...", "items": <digest items>}`.

## Tests

```bash
cd webdemo
python3 -m unittest discover -s tests -v   # 21 automated tests (parsing, model-reply handling, API, safety)
python3 eval.py                             # score against samples/eval_set.json
```

`samples/eval_set.json` holds **draft** labels. Re-label it by hand before quoting any accuracy number,
and run `eval.py` with a live key — a score from the mock model only measures the keyword rules.

## Changes vs. the original agent

| Issue in the original | Behaviour now |
|---|---|
| `bool("false")` is `True`, so a model replying `"action_needed": "false"` created a fake to-do | String booleans are parsed properly |
| An email the model skipped, or gave an invalid category, was silently filed under Q4 ("ignore") | It is placed in Q2 with a **needs manual check** flag and a warning |
| Code-fence stripping used `lstrip("json")` (strips characters, not a prefix) | Fences are matched with a regex and the first JSON object is decoded |
| Instructions hidden inside an email could steer the classification | The prompt marks email text as untrusted (still needs testing on a live model) |
| Exact duplicate emails appeared twice | Merged, with a warning |
