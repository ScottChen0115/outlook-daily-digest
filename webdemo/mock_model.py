"""Deterministic offline stand-in for the LLM.

It lets the demo and the automated tests run without an API key. It is a
keyword heuristic, not a language model: its results only exercise the
pipeline and say nothing about how well a real model classifies email.
"""
import json
import re

URGENT_WORDS = (
    "urgent", "asap", "immediately", "right away", "today", "tonight", "tomorrow", "eod",
    "end of day", "outage", "is down", "went down", "deadline", "overdue", "final notice",
    "within 24 hours", "by noon", "action required", "expires", "紧急", "今天", "明天", "尽快",
)
IMPORTANT_WORDS = (
    "client", "customer", "contract", "approval", "approve", "budget", "invoice", "payment",
    "production", "outage", "incident", "security", "review", "interview", "offer", "manager",
    "director", "ceo", "board", "project", "proposal", "deliverable", "grade", "exam", "assignment",
    "客户", "合同", "审批", "项目", "老板",
)
LOW_WORDS = (
    "newsletter", "unsubscribe", "promotion", "% off", "sale", "webinar", "digest", "sports day",
    "lunch menu", "fyi only", "no action", "announcement", "survey", "广告", "通知",
)
ACTION_WORDS = (
    "please", "could you", "can you", "need you", "reply", "respond", "confirm", "submit",
    "review", "approve", "sign", "send", "fill in", "register", "rsvp", "call me", "请", "回复", "确认",
)
DEADLINE_RE = re.compile(
    r"\b(?:by|before|due|until)\s+((?:today|tomorrow|tonight|eod|end of day|noon|"
    r"(?:mon|tues|wednes|thurs|fri|satur|sun)day|\d{1,2}(?::\d{2})?\s*(?:am|pm)?|"
    r"\d{4}-\d{2}-\d{2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})"
    r"(?:\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?)",
    re.IGNORECASE,
)


def _has(text, words):
    return any(w in text for w in words)


def _first_sentence(body, limit=110):
    s = re.split(r"(?<=[.!?。！？])\s", body.strip(), maxsplit=1)[0]
    return s if len(s) <= limit else s[:limit - 1].rstrip() + "…"


def _action(subject, body):
    for sent in re.split(r"(?<=[.!?。！？])\s+", body):
        if _has(sent.lower(), ACTION_WORDS):
            return _first_sentence(sent, 120)
    return f"Follow up on: {subject}"


def classify_one(m):
    text = f"{m.get('subject', '')} {m.get('body', '')}".lower()
    low = _has(text, LOW_WORDS)
    urgent = _has(text, URGENT_WORDS) and not low
    important = _has(text, IMPORTANT_WORDS) and not low
    if urgent and important:
        cat = "Q1"
    elif important:
        cat = "Q2"
    elif urgent:
        cat = "Q3"
    else:
        cat = "Q4"
    action_needed = cat != "Q4" and _has(text, ACTION_WORDS)
    dl = DEADLINE_RE.search(m.get("body", "") + " " + m.get("subject", ""))
    return {
        "summary": _first_sentence(m.get("body", "")) or m.get("subject", ""),
        "category": cat,
        "action_needed": action_needed,
        "action": _action(m.get("subject", ""), m.get("body", "")) if action_needed else "",
        "deadline": dl.group(1).strip() if dl and action_needed else "",
    }


def classify_json(batch):
    """Mock reply to the classification prompt, in the same JSON shape the LLM must return."""
    return json.dumps({"results": [dict(idx=i, **classify_one(m)) for i, m in enumerate(batch, 1)]})


def answer(question, items):
    """Mock reply to an inbox question. Only answers from the supplied digest items."""
    q = question.lower()
    if not items:
        return "There is no digest loaded yet. Generate a digest first, then ask about it."

    def line(it):
        extra = f" (due {it['deadline']})" if it.get("deadline") else ""
        return f"- [{it['category']}] {it['subject']} — {it['from']}{extra}"

    pending = [it for it in items if it.get("action_needed") and it["category"] in ("Q1", "Q2")]
    if _has(q, ("todo", "to-do", "to do", "need to do", "action", "pending", "待办", "要做")):
        if not pending:
            return "Nothing important is waiting on you in this digest."
        return "Important items that need action:\n" + "\n".join(
            f"- {it['action']} (from: {it['subject']}{', due ' + it['deadline'] if it['deadline'] else ''})"
            for it in pending)
    if _has(q, ("urgent", "first", "priority", "紧急", "先")):
        q1 = [it for it in items if it["category"] == "Q1"]
        return ("Handle these first (Important & Urgent):\n" + "\n".join(map(line, q1))
                if q1 else "No email in this digest is both important and urgent.")
    if _has(q, ("deadline", "due", "截止")):
        due = [it for it in items if it.get("deadline")]
        return ("Emails with a stated deadline:\n" + "\n".join(map(line, due))
                if due else "None of these emails states an explicit deadline.")
    if _has(q, ("ignore", "skip", "unimportant", "not important", "newsletter", "可以忽略")):
        q4 = [it for it in items if it["category"] == "Q4"]
        return ("These look safe to skip:\n" + "\n".join(map(line, q4))
                if q4 else "Every email in this digest has at least some importance or urgency.")
    m = re.search(r"\bfrom\s+([\w.@-]+)", q)
    if m:
        who = m.group(1)
        hits = [it for it in items if who in it["from"].lower()]
        return ("Emails from that sender:\n" + "\n".join(map(line, hits))
                if hits else f"I found no email from '{who}' in this digest.")
    if _has(q, ("summary", "summarize", "overview", "how many", "总结", "概况")):
        counts = {k: sum(1 for it in items if it["category"] == k) for k in ("Q1", "Q2", "Q3", "Q4")}
        return (f"{len(items)} emails: {counts['Q1']} important & urgent, {counts['Q2']} important, "
                f"{counts['Q3']} urgent but minor, {counts['Q4']} skippable. "
                f"{len(pending)} important item(s) need action.")
    return ("I can only answer questions about the emails in this digest — for example: "
            "\"What do I need to do?\", \"What is urgent?\", \"Any deadlines?\", "
            "\"What can I ignore?\" or \"Anything from alice?\"")
