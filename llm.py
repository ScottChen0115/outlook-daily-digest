"""LLM provider layer: Zhipu BigModel (primary) + DeepSeek (fallback) with automatic failover. Standard library only."""
import json
import logging
import time
import urllib.error
import urllib.request

import config

logger = logging.getLogger(__name__)


def _providers():
    """Available providers by priority: [(name, url, key, model, style), ...]"""
    provs = []
    if config.ZHIPU_API_KEY:
        url = config.ZHIPU_ANTHROPIC_URL if config.ZHIPU_STYLE == "anthropic" else config.ZHIPU_URL
        provs.append(("Zhipu", url, config.ZHIPU_API_KEY, config.ZHIPU_MODEL, config.ZHIPU_STYLE))
    if config.DEEPSEEK_API_KEY:
        provs.append(("DeepSeek", config.DEEPSEEK_URL, config.DEEPSEEK_API_KEY, config.DEEPSEEK_MODEL, "openai"))
    return provs


def _post_chat(url, key, model, messages):
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.2,     # classification tasks need stability
        "max_tokens": 4096,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    })
    with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _post_chat_anthropic(url, key, model, messages):
    """Anthropic-compatible endpoint (Zhipu GLM Coding Plan channel): converts messages and parses the reply."""
    system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
    msgs = [m for m in messages if m.get("role") != "system"]
    payload = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "messages": msgs,
        "temperature": 0.2,
        "thinking": {"type": "disabled"},   # skip deep thinking, output the result directly
        **({"system": system} if system else {}),
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "x-api-key": key,
        "Authorization": f"Bearer {key}",
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as r:
        data = json.loads(r.read().decode("utf-8"))
    # The reply is a list of content blocks (possibly including thinking blocks); keep text blocks only
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    if not text:
        raise ValueError("endpoint returned no text content (possibly thinking blocks only)")
    return text


def chat(messages):
    """Call the LLM: Zhipu first; retry on failure, then fall back to DeepSeek. Returns (reply text, provider name)."""
    providers = _providers()
    if not providers:
        raise RuntimeError("No LLM API key configured; set ZHIPU_API_KEY or DEEPSEEK_API_KEY in .env")
    last_err = "unknown"
    for name, url, key, model, style in providers:
        for attempt in range(1, config.LLM_RETRIES + 1):
            try:
                logger.info("Calling %s (%s), attempt %d", name, model, attempt)
                fn = _post_chat_anthropic if style == "anthropic" else _post_chat
                return fn(url, key, model, messages), name
            except (urllib.error.URLError, urllib.error.HTTPError,
                    KeyError, IndexError, ValueError, OSError) as e:
                last_err = f"{name}: {e}"
                logger.warning("Call to %s failed: %s", name, e)
                if attempt < config.LLM_RETRIES:
                    time.sleep(3 * attempt)  # back off, then retry
        logger.warning("⚠️ Provider switch: %s unavailable, trying the next provider", name)
    raise RuntimeError(f"All LLM providers failed ({last_err})")
