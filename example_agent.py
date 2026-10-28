"""Offline request demonstration. No credentials, API call or generated code execution."""
import io
import json
from unittest.mock import patch

from caching_client import CloudAgentClient


def demonstrate():
    history = [{"role": "user", "content": "Preserve all requirements."},
               {"role": "assistant", "content": "```python\n" + "x = 1\n" * 30 + "```"}]
    fixture = {"content": [{"type": "text", "text": "Offline fixture response."}],
               "stop_reason": "end_turn",
               "usage": {"input_tokens": 100, "output_tokens": 5,
                         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}

    def offline_transport(request, **kwargs):
        body = json.loads(request.data)
        assert body["messages"][:-1] == history, "History was modified"
        print("All history retained:", len(history), "messages")
        print("Explicit cache request:", body["system"][0]["cache_control"])
        return io.BytesIO(json.dumps(fixture).encode())

    client = CloudAgentClient(api_key="offline-placeholder", model="fixture-model")
    with patch("urllib.request.urlopen", side_effect=offline_transport):
        answer, telemetry = client.execute_turn("Stable review instructions.", history, "Continue.")
    print(answer)
    print("Estimated cost without supplied rates:", telemetry.estimated_cost_usd)
    print("This demonstrates request construction, not an actual cache hit.")


if __name__ == "__main__":
    demonstrate()
