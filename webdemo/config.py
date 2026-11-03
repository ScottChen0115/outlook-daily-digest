"""Web demo configuration: reads environment variables (and an optional webdemo/.env). Standard library only."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_env():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_env()

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# auto = use a live provider when a key is configured, otherwise the offline mock model
# live = live providers only (errors are reported, never silently replaced)
# mock = offline deterministic mock model only
LLM_MODE = os.environ.get("LLM_MODE", "auto").strip().lower()

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "15"))
MAX_EMAILS = int(os.environ.get("MAX_EMAILS", "60"))
MAX_EMAIL_CHARS = int(os.environ.get("MAX_EMAIL_CHARS", "1200"))
MAX_REQUEST_BYTES = int(os.environ.get("MAX_REQUEST_BYTES", str(256 * 1024)))
MAX_QUESTION_CHARS = int(os.environ.get("MAX_QUESTION_CHARS", "500"))
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "90"))
LLM_RETRIES = int(os.environ.get("LLM_RETRIES", "1"))

_SUMMARY_LANGS = {"en": "English", "zh": "Simplified Chinese"}
SUMMARY_LANG = os.environ.get("SUMMARY_LANG", "en").strip().lower() or "en"
SUMMARY_LANGUAGE_NAME = _SUMMARY_LANGS.get(SUMMARY_LANG, SUMMARY_LANG)

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
ZHIPU_MODEL = os.environ.get("ZHIPU_MODEL", "glm-5.3-flash")
ZHIPU_STYLE = os.environ.get("ZHIPU_STYLE", "openai")
ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_ANTHROPIC_URL = "https://open.bigmodel.cn/api/anthropic/v1/messages"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

CATEGORIES = {
    "Q1": {"name": "Important & Urgent", "color": "#dc2626", "emoji": "🔴"},
    "Q2": {"name": "Important, Not Urgent", "color": "#d97706", "emoji": "🟡"},
    "Q3": {"name": "Urgent, Not Important", "color": "#2563eb", "emoji": "🔵"},
    "Q4": {"name": "Neither Urgent nor Important", "color": "#6b7280", "emoji": "⚪"},
}
CATEGORY_ORDER = ("Q1", "Q2", "Q3", "Q4")
