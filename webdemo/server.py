"""Web demo server for the email digest agent. Standard library only.

Run:  python3 server.py            (then open http://localhost:8000)
"""
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import digest
import llm

logger = logging.getLogger("digest-web")

STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
SAMPLES_FILE = config.BASE_DIR / "samples" / "sample_inboxes.json"


class Handler(BaseHTTPRequestHandler):
    server_version = "DigestDemo/1.0"

    def log_message(self, fmt, *args):
        logger.info("%s %s", self.address_string(), fmt % args)

    def _send(self, status, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise digest.InputError("Invalid Content-Length")
        if length <= 0:
            raise digest.InputError("Empty request body")
        if length > config.MAX_REQUEST_BYTES:
            raise digest.InputError(f"Request too large (limit {config.MAX_REQUEST_BYTES // 1024} KB)")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise digest.InputError("Request body is not valid JSON")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in STATIC:
            name, ctype = STATIC[path]
            return self._send(200, (config.BASE_DIR / "static" / name).read_bytes(), ctype)
        if path == "/api/status":
            return self._send(200, {"mode": llm.mode(), "model": config.DEEPSEEK_MODEL,
                                    "key_configured": llm.has_key(), "max_emails": config.MAX_EMAILS})
        if path == "/api/samples":
            return self._send(200, SAMPLES_FILE.read_bytes())
        if path == "/healthz":
            return self._send(200, {"ok": True})
        self._send(404, {"error": "Not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            payload = self._read_json()
            if path == "/api/digest":
                result = digest.summarize(digest.load_emails(payload))
                return self._send(200, {"mode": llm.mode(), **result})
            if path == "/api/ask":
                if not isinstance(payload, dict):
                    raise digest.InputError("Request body must be a JSON object")
                answer, provider = digest.ask(payload.get("question"), payload.get("items"),
                                              payload.get("history"))
                return self._send(200, {"answer": answer, "provider": provider, "mode": llm.mode()})
            self._send(404, {"error": "Not found"})
        except digest.InputError as e:
            self._send(400, {"error": str(e)})
        except llm.LLMConfigError as e:
            logger.error("LLM configuration problem: %s", e)
            self._send(503, {"error": "The AI service is not configured correctly (DeepSeek API key missing, "
                                      "invalid or out of balance). Please tell the demo owner."})
        except llm.LLMError as e:
            logger.error("LLM failure: %s", e)
            self._send(502, {"error": "The AI provider failed to respond. Please try again in a moment."})
        except Exception:
            logger.exception("Unhandled error on %s", path)
            self._send(500, {"error": "Internal server error"})


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        stream=sys.stdout)
    srv = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    logger.info("Email digest demo on http://%s:%d (mode: %s)", config.HOST, config.PORT, llm.mode())
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
