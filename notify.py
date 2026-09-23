"""macOS system notifications (osascript)."""
import logging
import subprocess

logger = logging.getLogger(__name__)


def _quote(s):
    return str(s or "").replace("\\", "\\\\").replace('"', '\\"')


def notify(title, message, sound="Glass"):
    """Post a notification to the macOS Notification Center."""
    script = (f'display notification "{_quote(message)}" '
              f'with title "{_quote(title)}" sound name "{sound}"')
    try:
        subprocess.run(["osascript", "-e", script], timeout=15, check=False)
    except OSError as e:  # non-macOS fallback
        logger.warning("Failed to send system notification: %s", e)
