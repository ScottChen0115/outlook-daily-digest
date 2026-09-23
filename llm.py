"""LLM provider layer: Zhipu BigModel (primary) + DeepSeek (fallback) with automatic failover. Standard library only."""
import json
import logging
import time
import urllib.error
import urllib.request

import config

logger = logging.getLogger(__name__)


def _providers():
    """Available providers by priority: [(name, url, key, model), ...]"""
    provs = []
    if config.ZHIPU_API_KEY:
        provs.append(("Zhipu", config.ZHIPU_URL, config.ZHIPU_API_KEY, config.ZHIPU_MODEL))
    if config.DEEPSEEK_API_KEY:
        provs.append(("DeepSeek", config.DEEPSEEK_URL, config.DEEPSEEK_API_KEY, config.DEEPSEEK_MODEL))
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


def chat(messages):
    """Call the LLM: Zhipu first; retry on failure, then fall back to DeepSeek. Returns (reply text, provider name)."""
    providers = _providers()
    if not providers:
        raise RuntimeError("No LLM API key configured; set ZHIPU_API_KEY or DEEPSEEK_API_KEY in .env")
    last_err = "unknown"
    for name, url, key, model in providers:
        for attempt in range(1, config.LLM_RETRIES + 1):
            try:
                logger.info("Calling %s (%s), attempt %d", name, model, attempt)
                return _post_chat(url, key, model, messages), name
            except (urllib.error.URLError, urllib.error.HTTPError,
                    KeyError, IndexError, ValueError, OSError) as e:
                last_err = f"{name}: {e}"
                logger.warning("Call to %s failed: %s", name, e)
                if attempt < config.LLM_RETRIES:
                    time.sleep(3 * attempt)  # back off, then retry
        logger.warning("⚠️ Provider switch: %s unavailable, trying the next provider", name)
    raise RuntimeError(f"All LLM providers failed ({last_err})")
