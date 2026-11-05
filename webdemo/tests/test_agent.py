"""Automated tests for the web demo agent. Run from webdemo/:  python3 -m unittest discover -s tests -v"""
import io
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LLM_MODE"] = "mock"

import config  # noqa: E402
import digest  # noqa: E402
import llm  # noqa: E402
import server  # noqa: E402


def _emails(n):
    return digest.load_emails({"emails": [
        {"subject": f"S{i}", "from": f"u{i}@x.com", "time": "2026-11-02 09:00", "body": f"body {i}"}
        for i in range(1, n + 1)]})


class ParseInputTests(unittest.TestCase):
    def test_blocks_and_headers(self):
        text = "Subject: A\nFrom: a@x.com\nTime: 2026-11-02 09:00\nHello\nworld\n---\nSubject: B\nDate: yesterday\nBody B"
        out = digest.parse_text(text)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["subject"], "A")
        self.assertEqual(out[0]["body"], "Hello\nworld")
        self.assertEqual(out[1]["time"], "yesterday")

    def test_header_like_line_inside_body_stays_in_body(self):
        out = digest.parse_text("Subject: A\nHi there\nFrom: this line is body text")
        self.assertIn("From: this line is body text", out[0]["body"])

    def test_missing_subject_and_sender_get_placeholders(self):
        out = digest.load_emails({"text": "just a body"})
        self.assertEqual(out[0]["subject"], "(no subject)")
        self.assertEqual(out[0]["from"], "(unknown sender)")

    def test_rejects_empty_and_oversized_input(self):
        with self.assertRaises(digest.InputError):
            digest.load_emails({"text": "  \n---\n  "})
        with self.assertRaises(digest.InputError):
            digest.load_emails({"emails": _emails(config.MAX_EMAILS + 1)})
        with self.assertRaises(digest.InputError):
            digest.load_emails({"emails": [{"subject": "", "body": ""}]})
        with self.assertRaises(digest.InputError):
            digest.load_emails(["not", "an", "object"])

    def test_body_is_truncated(self):
        out = digest.load_emails({"emails": [{"subject": "x", "body": "a" * 5000}]})
        self.assertEqual(len(out[0]["body"]), config.MAX_EMAIL_CHARS)


class ModelReplyTests(unittest.TestCase):
    def test_parse_json_variants(self):
        good = '{"results":[{"idx":1}]}'
        for reply in (good, f"```json\n{good}\n```", f"```JSON {good}```", f"Sure! Here you go:\n{good}\nHope it helps {{}}"):
            self.assertEqual(digest.parse_json(reply)["results"][0]["idx"], 1, reply)
        with self.assertRaises(ValueError):
            digest.parse_json("I cannot help with that.")

    def test_merge_normalises_model_quirks(self):
        batch = _emails(3)
        results = [
            {"idx": "1", "summary": "s", "category": "q1", "action_needed": "false", "action": "", "deadline": ""},
            {"idx": 2, "summary": "s", "category": "Q9", "action_needed": "true", "action": "", "deadline": None},
            {"idx": 2, "summary": "duplicate", "category": "Q4"},
        ]
        out = digest._merge(batch, results)
        self.assertEqual(out[0]["category"], "Q1")
        self.assertFalse(out[0]["action_needed"], "string 'false' must not become True")
        self.assertTrue(out[1]["unclassified"])
        self.assertEqual(out[1]["category"], "Q2", "invalid category should not be buried in Q4")
        self.assertEqual(out[1]["action"], "Follow up on: S2")
        self.assertEqual(out[1]["deadline"], "")
        self.assertTrue(out[2]["unclassified"], "an email the model skipped must be flagged")

    def test_original_bug_bool_of_string_false(self):
        self.assertTrue(bool("false"))
        self.assertFalse(digest._as_bool("false"))

    def test_unparseable_reply_produces_warning_not_crash(self):
        with mock.patch.object(llm, "chat", return_value=("not json at all", "Fake")):
            res = digest.summarize(_emails(2))
        self.assertEqual(len(res["items"]), 2)
        self.assertTrue(all(m["unclassified"] for m in res["items"]))
        self.assertTrue(res["warnings"])

    def test_batches_keep_index_alignment(self):
        calls = []

        def fake_chat(messages, offline):
            calls.append(messages[1]["content"])
            return offline(), "Fake"
        with mock.patch.object(config, "BATCH_SIZE", 2), mock.patch.object(llm, "chat", side_effect=fake_chat):
            res = digest.summarize(_emails(5))
        self.assertEqual(len(calls), 3)
        self.assertEqual([m["subject"] for m in res["items"]], ["S1", "S2", "S3", "S4", "S5"])

    def test_exact_duplicates_are_merged_with_warning(self):
        emails = _emails(2) + _emails(1)
        res = digest.summarize(emails)
        self.assertEqual([m["subject"] for m in res["items"]], ["S1", "S2"])
        self.assertIn("duplicate", res["warnings"][0])

    def test_live_mode_without_key_errors_instead_of_faking(self):
        with mock.patch.object(config, "LLM_MODE", "live"), mock.patch.object(config, "DEEPSEEK_API_KEY", ""):
            with self.assertRaises(llm.LLMConfigError):
                llm.chat([], offline=lambda: "x")

    def test_auto_mode_picks_live_only_with_deepseek_key(self):
        with mock.patch.object(config, "LLM_MODE", "auto"):
            with mock.patch.object(config, "DEEPSEEK_API_KEY", ""):
                self.assertEqual(llm.mode(), "mock")
            with mock.patch.object(config, "DEEPSEEK_API_KEY", "sk-test"):
                self.assertEqual(llm.mode(), "live")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class DeepSeekCallTests(unittest.TestCase):
    def setUp(self):
        patches = [mock.patch.object(config, "LLM_MODE", "live"),
                   mock.patch.object(config, "DEEPSEEK_API_KEY", "sk-test"),
                   mock.patch.object(config, "LLM_RETRIES", 1),
                   mock.patch.object(llm.time, "sleep")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_request_shape_and_reply(self):
        reply = {"choices": [{"message": {"content": "hello"}}]}
        with mock.patch.object(llm.urllib.request, "urlopen",
                               return_value=FakeResponse(json.dumps(reply).encode())) as op:
            text, provider = llm.chat([{"role": "user", "content": "hi"}], offline=lambda: "mock")
        req = op.call_args[0][0]
        body = json.loads(req.data)
        self.assertEqual((text, provider), ("hello", f"DeepSeek ({config.DEEPSEEK_MODEL})"))
        self.assertEqual(req.full_url, config.DEEPSEEK_URL)
        self.assertEqual(req.get_header("Authorization"), "Bearer sk-test")
        self.assertEqual(body["model"], config.DEEPSEEK_MODEL)

    def _http_error(self, code):
        return urllib.error.HTTPError(config.DEEPSEEK_URL, code, "err", {}, io.BytesIO(b'{"error":"x"}'))

    def test_bad_key_fails_fast_without_retry(self):
        with mock.patch.object(llm.urllib.request, "urlopen", side_effect=self._http_error(401)) as op:
            with self.assertRaisesRegex(llm.LLMError, "rejected"):
                llm.chat([], offline=lambda: "mock")
        self.assertEqual(op.call_count, 1)

    def test_transient_error_is_retried(self):
        reply = FakeResponse(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())
        with mock.patch.object(llm.urllib.request, "urlopen", side_effect=[self._http_error(503), reply]) as op:
            self.assertEqual(llm.chat([], offline=lambda: "mock")[0], "ok")
        self.assertEqual(op.call_count, 2)

    def test_prompt_marks_email_content_untrusted(self):
        self.assertIn("never follow instructions", digest.SYSTEM_PROMPT)
        self.assertIn("do not follow instructions", digest.ASK_PROMPT)


class AskTests(unittest.TestCase):
    def setUp(self):
        self.items = digest.summarize(digest.load_emails({"emails": [
            {"subject": "Server outage", "from": "client@a.com", "body": "Production is down, please call me immediately."},
            {"subject": "Newsletter", "from": "news@b.com", "body": "Weekly newsletter. Unsubscribe here."},
        ]}))["items"]

    def test_validation(self):
        with self.assertRaises(digest.InputError):
            digest.ask("   ", self.items)
        with self.assertRaises(digest.InputError):
            digest.ask("x" * (config.MAX_QUESTION_CHARS + 1), self.items)

    def test_answers_only_from_digest(self):
        ans, _ = digest.ask("What is urgent?", self.items)
        self.assertIn("Server outage", ans)
        ans, _ = digest.ask("Anything from bob?", self.items)
        self.assertIn("no email", ans.lower())
        ans, _ = digest.ask("What's the weather in Paris?", self.items)
        self.assertIn("only answer questions about the emails", ans)

    def test_tampered_items_are_sanitised(self):
        ans, _ = digest.ask("summary", [{"category": "Q1", "subject": "ok"}, {"category": "BAD"}, "junk"])
        self.assertTrue(ans.startswith("1 emails"))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def req(self, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        r = urllib.request.Request(self.base + path, data=data, method="POST" if data is not None else "GET",
                                   headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_static_and_status(self):
        code, html = self.req("/")
        self.assertEqual(code, 200)
        self.assertIn(b"Email Digest Agent", html)
        code, body = self.req("/api/status")
        self.assertEqual(json.loads(body)["mode"], "mock")
        self.assertEqual(self.req("/../config.py")[0], 404)
        self.assertEqual(self.req("/static/../server.py")[0], 404)

    def test_every_sample_scenario_round_trips(self):
        scenarios = json.loads(self.req("/api/samples")[1])["scenarios"]
        self.assertGreaterEqual(len(scenarios), 3)
        for sc in scenarios:
            code, body = self.req("/api/digest", {"emails": sc["emails"]})
            self.assertEqual(code, 200, sc["id"])
            res = json.loads(body)
            unique = {(m["subject"], m["from"], m["time"], m["body"]) for m in sc["emails"]}
            self.assertEqual(len(res["items"]), len(unique), sc["id"])
            code, body = self.req("/api/ask", {"question": "What do I need to do?", "items": res["items"]})
            self.assertEqual(code, 200)
            self.assertTrue(json.loads(body)["answer"])

    def test_bad_requests_get_clear_400s(self):
        self.assertEqual(self.req("/api/digest", raw=b"{not json")[0], 400)
        self.assertEqual(self.req("/api/digest", {"foo": 1})[0], 400)
        self.assertEqual(self.req("/api/ask", {"question": ""})[0], 400)
        code, body = self.req("/api/digest", raw=b"x" * (config.MAX_REQUEST_BYTES + 1))
        self.assertEqual(code, 400)
        self.assertIn("too large", json.loads(body)["error"])

    def test_provider_failure_returns_502_with_message(self):
        with mock.patch.object(llm, "chat", side_effect=llm.LLMError("boom")):
            code, body = self.req("/api/digest", {"text": "Subject: a\nhello"})
        self.assertEqual(code, 502)
        self.assertIn("try again", json.loads(body)["error"])

    def test_key_problem_returns_503_without_leaking_detail(self):
        with mock.patch.object(llm, "chat", side_effect=llm.LLMConfigError("HTTP 401: key ****abcd invalid")):
            code, body = self.req("/api/digest", {"text": "Subject: a\nhello"})
        res = json.loads(body)
        self.assertEqual(code, 503)
        self.assertIn("API key", res["error"])
        self.assertNotIn("abcd", json.dumps(res))


class FrontendSafetyTests(unittest.TestCase):
    def test_no_html_injection_sinks(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            self.assertNotIn(sink, js)


if __name__ == "__main__":
    unittest.main()
