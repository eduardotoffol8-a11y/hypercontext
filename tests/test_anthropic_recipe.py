import copy
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from recipes.anthropic.request import build_request, send_request


ROOT = Path(__file__).resolve().parents[1]


class AnthropicRecipeTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads((ROOT / "recipes/anthropic/request.example.json").read_text())

    def test_cache_keeps_history_and_tools_identical(self):
        original = copy.deepcopy(self.source)
        body, headers = build_request(self.source, model="account-model")
        self.assertEqual(body["messages"], original["messages"])
        self.assertEqual(body["tools"], original["tools"])
        self.assertEqual(body["system"][0]["text"], original["system"])
        self.assertEqual(body["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertNotIn("context_management", body)
        self.assertNotIn("anthropic-beta", headers)
        self.assertEqual(self.source, original)

    def test_pruning_uses_native_tool_result_policy_and_beta_header(self):
        body, headers = build_request(self.source, model="account-model", prune=True)
        edit = body["context_management"]["edits"][0]
        self.assertEqual(edit["type"], "clear_tool_uses_20250919")
        self.assertFalse(edit["clear_tool_inputs"])
        self.assertEqual(edit["exclude_tools"], ["read_requirements"])
        self.assertEqual(edit["keep"], {"type": "tool_uses", "value": 3})
        self.assertEqual(headers["anthropic-beta"], "context-management-2025-06-27")
        self.assertEqual(body["messages"], self.source["messages"])

    def test_cache_can_be_disabled_independently_of_pruning(self):
        body, _ = build_request(self.source, model="account-model", cache=False, prune=True)
        self.assertEqual(body["system"], self.source["system"])
        self.assertIn("context_management", body)

    def test_existing_context_policy_is_not_silently_overwritten(self):
        self.source["context_management"] = {"edits": []}
        with self.assertRaises(ValueError):
            build_request(self.source, model="account-model", prune=True)

    def test_send_preserves_native_response_and_uses_timeout(self):
        body, headers = build_request(self.source, model="account-model", prune=True)
        fixture = {"content": [{"type": "tool_use", "id": "tool_next", "name": "read_document",
                                "input": {"path": "contract.md"}}], "stop_reason": "tool_use",
                   "usage": {"input_tokens": 100, "cache_read_input_tokens": 5000},
                   "context_management": {"applied_edits": [{"cleared_tool_uses": 2}]}}
        observed = []
        def transport(request, **kwargs):
            observed.append((request, kwargs))
            return io.BytesIO(json.dumps(fixture).encode())
        with patch("urllib.request.urlopen", side_effect=transport):
            result = send_request(body, headers, api_key="fixture-key", timeout=12)
        self.assertEqual(result, fixture)
        self.assertEqual(observed[0][0].full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(observed[0][1]["timeout"], 12)

    def test_live_send_requires_credentials_before_network(self):
        body, headers = build_request(self.source, model="account-model")
        with patch("urllib.request.urlopen", side_effect=AssertionError("No network expected")):
            with self.assertRaises(ValueError):
                send_request(body, headers, api_key="")

    def test_invalid_requests_fail_locally(self):
        for update in ({"stream": True}, {"messages": []}, {"system": ""}, {"max_tokens": 0}):
            with self.subTest(update=update):
                with self.assertRaises(ValueError):
                    build_request({**self.source, **update}, model="account-model")


if __name__ == "__main__":
    unittest.main()
