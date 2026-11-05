"""LLM layer: DeepSeek chat API, plus an offline mock. Standard library only."""
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


class LLMConfigError(LLMError):
    """The key is missing, invalid or out of balance; retrying will not help."""


def has_key():
    return bool(config.DEEPSEEK_API_KEY)


def mode():
    """Effective mode: 'live' or 'mock'."""
    if config.LLM_MODE in ("live", "mock"):
        return config.LLM_MODE
    return "live" if has_key() else "mock"


def _chat_deepseek(messages):
    payload = json.dumps({
        "model": config.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 4096,
    }).encode("utf-8")
    req = urllib.request.Request(config.DEEPSEEK_URL, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
    })
    with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def chat(messages, offline):
    """Send a chat request. `offline` is a zero-argument callable producing the mock reply.

    Returns (reply_text, provider_name). In live mode a failed request raises
    LLMError after the retries rather than quietly using the mock.
    """
    if mode() == "mock":
        return offline(), MOCK_NAME
    if not has_key():
        raise LLMConfigError("LLM_MODE=live but DEEPSEEK_API_KEY is not set")
    errors = []
    for attempt in range(config.LLM_RETRIES + 1):
        try:
            return _chat_deepseek(messages), f"DeepSeek ({config.DEEPSEEK_MODEL})"
        except urllib.error.HTTPError as e:
            detail = f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:200]}"
            if e.code in (400, 401, 402, 403):
                raise LLMConfigError(f"DeepSeek rejected the request ({detail})") from e
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
            detail = str(e)
        logger.warning("DeepSeek attempt %d failed: %s", attempt + 1, detail)
        errors.append(detail)
        if attempt < config.LLM_RETRIES:
            time.sleep(1.5 * (attempt + 1))
    raise LLMError("DeepSeek failed: " + " | ".join(errors))
