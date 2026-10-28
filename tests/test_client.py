import copy
import io
import json
import unittest
from unittest.mock import patch

from caching_client import CloudAgentClient


RATES = {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75}


class ClientTests(unittest.TestCase):
    def call(self, provider, usage, history=None, **options):
        client = CloudAgentClient(provider=provider, api_key="test-key", model="test-model", **options)
        if provider == "anthropic":
            payload = {"content": [{"type": "text", "text": "answer"}], "usage": usage,
                       "stop_reason": "end_turn"}
        else:
            payload = {"choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}],
                       "usage": usage}
        requests = []

        def transport(request, **kwargs):
            requests.append((json.loads(request.data), kwargs))
            return io.BytesIO(json.dumps(payload).encode())

        with patch("urllib.request.urlopen", side_effect=transport):
            answer, telemetry = client.execute_turn("stable system", history or [], "next")
        self.assertEqual(answer, "answer")
        return requests[0], telemetry

    def test_anthropic_counts_separate_input_buckets(self):
        _, result = self.call("anthropic", {"input_tokens": 100, "output_tokens": 10,
            "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 200},
            pricing_per_mtok=RATES)
        self.assertEqual(result.prompt_tokens, 1300)
        self.assertAlmostEqual(result.estimated_cost_usd, 0.0015)
        self.assertAlmostEqual(result.estimated_baseline_cost_usd, 0.00405)

    def test_openai_cached_input_is_subset_of_total(self):
        _, result = self.call("openai", {"prompt_tokens": 1100, "completion_tokens": 10,
            "prompt_tokens_details": {"cached_tokens": 1000}}, pricing_per_mtok=RATES)
        self.assertEqual(result.prompt_tokens, 1100)
        self.assertAlmostEqual(result.estimated_cost_usd, 0.00075)

    def test_no_prices_does_not_invent_cost(self):
        _, result = self.call("anthropic", {"input_tokens": 10, "output_tokens": 2})
        self.assertIsNone(result.estimated_cost_usd)
        self.assertIsNone(result.cost_savings_percent)

    def test_cache_write_can_cost_more_than_baseline(self):
        _, result = self.call("anthropic", {"input_tokens": 0, "output_tokens": 0,
            "cache_creation_input_tokens": 1000}, pricing_per_mtok=RATES)
        self.assertAlmostEqual(result.cost_savings_usd, -0.00075)
        self.assertAlmostEqual(result.cost_savings_percent, -25.0)

    def test_history_is_preserved_including_old_code(self):
        code = "```python\n" + "x = 1\n" * 100 + "```"
        history = [{"role": "user", "content": code}, {"role": "assistant", "content": code},
                   {"role": "user", "content": "keep requirements"},
                   {"role": "assistant", "content": "ok"}]
        original = copy.deepcopy(history)
        (body, kwargs), _ = self.call("anthropic", {"input_tokens": 1, "output_tokens": 1}, history)
        self.assertEqual(body["messages"][:-1], original)
        self.assertEqual(history, original)
        self.assertEqual(kwargs["timeout"], 30.0)

    def test_rejects_unimplemented_local_provider(self):
        with self.assertRaises(ValueError):
            CloudAgentClient(provider="local", api_key="x", model="x")

    def test_missing_usage_is_unknown_not_zero(self):
        _, result = self.call("openai", {})
        self.assertIsNone(result.prompt_tokens)
        self.assertIsNone(result.estimated_cost_usd)

    def test_tools_rejected_before_network(self):
        client = CloudAgentClient(provider="openai", model="test", api_key="x")
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network must not be used")):
            with self.assertRaises(ValueError):
                client.execute_turn("sys", [{"role": "tool", "content": "result"}], "next")

    def test_invalid_rates_rejected(self):
        with self.assertRaises(ValueError):
            CloudAgentClient(model="test", api_key="x", pricing_per_mtok={**RATES, "input": -1})

    def test_openai_write_usage_is_not_silently_underpriced(self):
        _, result = self.call("openai", {"prompt_tokens": 1100, "completion_tokens": 10,
            "prompt_tokens_details": {"cached_tokens": 100, "cache_write_tokens": 1000}},
            pricing_per_mtok=RATES)
        self.assertEqual(result.cache_write_tokens, 1000)
        self.assertIsNone(result.estimated_cost_usd)

    def test_incomplete_response_is_not_reported_as_success(self):
        client = CloudAgentClient(provider="openai", model="test", api_key="x")
        payload = {"choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            with self.assertRaises(ValueError):
                client.execute_turn("sys", [], "next")

    def test_cache_flag_changes_anthropic_request_without_changing_history(self):
        client = CloudAgentClient(model="test", api_key="x")
        payload = {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
        bodies = []
        def transport(request, **kwargs):
            bodies.append(json.loads(request.data))
            return io.BytesIO(json.dumps(payload).encode())
        with patch("urllib.request.urlopen", side_effect=transport):
            client.execute_turn("stable", [], "next", enable_prompt_cache=True)
            client.execute_turn("stable", [], "next", enable_prompt_cache=False)
        self.assertEqual(bodies[0]["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(bodies[1]["system"], "stable")
        self.assertEqual(bodies[0]["messages"], bodies[1]["messages"])

    def test_network_error_propagates_without_retry(self):
        client = CloudAgentClient(model="test", api_key="x")
        attempts = []
        def transport(*args, **kwargs):
            attempts.append(1)
            raise TimeoutError("test timeout")
        with patch("urllib.request.urlopen", side_effect=transport):
            with self.assertRaises(TimeoutError):
                client.execute_turn("sys", [], "next")
        self.assertEqual(len(attempts), 1)


if __name__ == "__main__":
    unittest.main()
