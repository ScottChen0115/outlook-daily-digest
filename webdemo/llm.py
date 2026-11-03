"""LLM provider layer: Zhipu (primary) + DeepSeek (fallback), plus an offline mock. Standard library only."""
import json
import logging
import time
import urllib.error
import urllib.request

import config

logger = logging.getLogger(__name__)

MOCK_NAME = "Offline mock model"


class LLMError(RuntimeError):
    pass


def live_providers():
    """Configured live providers by priority: [(name, url, key, model, style), ...]"""
    provs = []
    if config.ZHIPU_API_KEY:
        url = config.ZHIPU_ANTHROPIC_URL if config.ZHIPU_STYLE == "anthropic" else config.ZHIPU_URL
        provs.append(("Zhipu", url, config.ZHIPU_API_KEY, config.ZHIPU_MODEL, config.ZHIPU_STYLE))
    if config.DEEPSEEK_API_KEY:
        provs.append(("DeepSeek", config.DEEPSEEK_URL, config.DEEPSEEK_API_KEY, config.DEEPSEEK_MODEL, "openai"))
    return provs


def mode():
    """Effective mode: 'live' or 'mock'."""
    if config.LLM_MODE == "mock":
        return "mock"
    if config.LLM_MODE == "live":
        return "live"
    return "live" if live_providers() else "mock"


def _post(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _chat_openai(url, key, model, messages):
    data = _post(url, {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 4096},
                 {"Authorization": f"Bearer {key}"})
    return data["choices"][0]["message"]["content"]


def _chat_anthropic(url, key, model, messages):
    system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
    msgs = [m for m in messages if m.get("role") != "system"]
    payload = {"model": model, "max_tokens": 4096, "messages": msgs, "temperature": 0.2,
               "thinking": {"type": "disabled"}, **({"system": system} if system else {})}
    data = _post(url, payload, {"x-api-key": key, "Authorization": f"Bearer {key}",
                                "anthropic-version": "2023-06-01"})
    texts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    if not texts:
        raise LLMError("Anthropic-style reply contained no text block")
    return "".join(texts)


def chat(messages, offline):
    """Send a chat request. `offline` is a zero-argument callable producing the mock reply.

    Returns (reply_text, provider_name). In live mode every provider is tried in
    order; if all fail an LLMError is raised rather than quietly using the mock.
    """
    if mode() == "mock":
        return offline(), MOCK_NAME
    provs = live_providers()
    if not provs:
        raise LLMError("LLM_MODE=live but no ZHIPU_API_KEY / DEEPSEEK_API_KEY is configured")
    errors = []
    for name, url, key, model, style in provs:
        fn = _chat_anthropic if style == "anthropic" else _chat_openai
        for attempt in range(config.LLM_RETRIES + 1):
            try:
                return fn(url, key, model, messages), f"{name} ({model})"
            except (urllib.error.URLError, TimeoutError, KeyError, ValueError, LLMError) as e:
                detail = e
                if isinstance(e, urllib.error.HTTPError):
                    detail = f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:200]}"
                logger.warning("%s attempt %d failed: %s", name, attempt + 1, detail)
                errors.append(f"{name}: {detail}")
                if attempt < config.LLM_RETRIES:
                    time.sleep(1.5 * (attempt + 1))
    raise LLMError("All providers failed: " + " | ".join(errors))
