"""Configuration loading: reads .env, standard library only, zero third-party dependencies."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_env():
    """Minimal .env parser (key=value, supports comments and blank lines)."""
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


load_env()

# ===== Email source: the macOS Mail app =====
# The mailbox address to watch (an Exchange account already added under
# System Settings -> Internet Accounts)
MAIL_ACCOUNT = os.environ.get("MAIL_ACCOUNT", "")

# ===== Timezone and batch tuning =====
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Shanghai")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "15"))        # emails per LLM call
MAX_EMAILS = int(os.environ.get("MAX_EMAILS", "100"))      # max emails per day
MAX_EMAIL_CHARS = int(os.environ.get("MAX_EMAIL_CHARS", "1200"))  # body truncation length
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))
LLM_RETRIES = int(os.environ.get("LLM_RETRIES", "2"))      # retries per provider

# ===== Language of the AI summaries =====
# "en" -> English, "zh" -> Simplified Chinese; any other value is passed
# through to the model as a language name.
_SUMMARY_LANGS = {"en": "English", "zh": "Simplified Chinese"}
SUMMARY_LANG = os.environ.get("SUMMARY_LANG", "en").strip().lower() or "en"
SUMMARY_LANGUAGE_NAME = _SUMMARY_LANGS.get(SUMMARY_LANG, SUMMARY_LANG)

# ===== Zhipu BigModel (primary provider) =====
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
ZHIPU_MODEL = os.environ.get("ZHIPU_MODEL", "glm-5.3-flash")
ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# ===== DeepSeek (fallback provider) =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# ===== Output directories =====
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
for _d in (REPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ===== Eisenhower quadrants (color-coded) =====
CATEGORIES = {
    "Q1": {"name": "Important & Urgent", "color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca", "emoji": "🔴"},
    "Q2": {"name": "Important, Not Urgent", "color": "#d97706", "bg": "#fffbeb", "border": "#fde68a", "emoji": "🟡"},
    "Q3": {"name": "Urgent, Not Important", "color": "#2563eb", "bg": "#eff6ff", "border": "#bfdbfe", "emoji": "🔵"},
    "Q4": {"name": "Neither Urgent nor Important", "color": "#6b7280", "bg": "#f9fafb", "border": "#e5e7eb", "emoji": "⚪"},
}
CATEGORY_ORDER = ("Q1", "Q2", "Q3", "Q4")
