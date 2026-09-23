"""LLM-powered one-line summaries + Eisenhower quadrant classification + to-do extraction."""
import json
import logging

import config
import llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a professional email assistant organizing the user's daily mail. For every email you must:\n"
    "1. Write a one-sentence, concise summary of its core content;\n"
    "2. Classify it into one Eisenhower quadrant:\n"
    "   Q1 = Important & Urgent: boss/client requests, approvals, incidents/outages, or a clear deadline today or tomorrow;\n"
    "   Q2 = Important, Not Urgent: important project updates, weekly reports, long-term planning, no pressing deadline;\n"
    "   Q3 = Urgent, Not Important: routine trivia that still needs a quick reply/forward, e.g. confirmations, routine CC matters;\n"
    "   Q4 = Neither: newsletters, announcements, ads, pure FYI.\n"
    "Criteria: important = directly related to the user's responsibilities, projects, KPIs or key people;\n"
    "urgent = has a clear near-term deadline, or the sender asks for a fast response.\n"
    "3. Decide whether the user needs to take action; if so, extract the concrete to-do item,\n"
    "and the deadline too when one is stated (otherwise an empty string).\n"
    f"Write all human-readable text (summary, action, deadline) in {config.SUMMARY_LANGUAGE_NAME}."
)


def _build_user_prompt(batch):
    lines = ["Below is the email list ([n] = index):", ""]
    for i, m in enumerate(batch, 1):
        lines.append(
            f"[{i}] From: {m['from']} | Time: {m['time']} | System importance: {m['importance']}\n"
            f"Subject: {m['subject']}\n"
            f"Body: {m['body']}\n"
        )
    lines.append(
        "For every email above, output JSON only, in exactly this format:\n"
        '{"results":[{"idx":1,"summary":"one-sentence summary","category":"Q1",'
        '"action_needed":true,"action":"concrete to-do","deadline":"deadline or empty string"}]}\n'
        "Rules: idx matches the input index; every email must appear in the results; "
        "category must be one of Q1/Q2/Q3/Q4."
    )
    return "\n".join(lines)


def _parse_json(text):
    """Robust parsing: strip markdown code fences, then take the outermost {...}."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM did not return JSON: {text[:200]}")
    return json.loads(text[start:end + 1])


def summarize_emails(emails):
    """Call the LLM in batches. Returns (classified items, pending important items, provider used)."""
    classified, provider_used = [], "none"
    for i in range(0, len(emails), config.BATCH_SIZE):
        batch = emails[i:i + config.BATCH_SIZE]
        text, provider = llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(batch)},
        ])
        provider_used = provider
        results = {r.get("idx"): r for r in _parse_json(text).get("results", [])}
        for j, m in enumerate(batch, 1):
            r = results.get(j) or {}
            cat = r.get("category", "Q4")
            if cat not in config.CATEGORIES:
                cat = "Q4"
            item = dict(m)
            item.update({
                "summary": r.get("summary", "") or m["body"][:80],
                "category": cat,
                "action_needed": bool(r.get("action_needed")),
                "action": r.get("action", "") or "",
                "deadline": r.get("deadline", "") or "",
            })
            classified.append(item)
        logger.info("Summarized %d/%d email(s) (provider: %s)",
                    min(i + config.BATCH_SIZE, len(emails)), len(emails), provider)
    # Pending important items = action-needed items in Q1/Q2
    pending = [c for c in classified
               if c["action_needed"] and c["category"] in ("Q1", "Q2")]
    return classified, pending, provider_used
