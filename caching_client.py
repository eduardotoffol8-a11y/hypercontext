"""Educational text client: provider-native caching without history removal."""
from __future__ import annotations

import copy
import json
import math
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ExecutionTelemetry:
    provider: str
    model: str
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    cache_read_tokens: Optional[int]
    cache_write_tokens: Optional[int]
    estimated_cost_usd: Optional[float]
    estimated_baseline_cost_usd: Optional[float]

    @property
    def cost_savings_usd(self) -> Optional[float]:
        if self.estimated_cost_usd is None or self.estimated_baseline_cost_usd is None:
            return None
        return self.estimated_baseline_cost_usd - self.estimated_cost_usd

    @property
    def cost_savings_percent(self) -> Optional[float]:
        savings = self.cost_savings_usd
        if savings is None or not self.estimated_baseline_cost_usd:
            return None
        return 100 * savings / self.estimated_baseline_cost_usd


class CloudAgentClient:
    """Synchronous Anthropic Messages / OpenAI Chat Completions text adapter.

    Select an available model explicitly. Optional rates are caller-supplied
    USD per million tokens for that model and billing tier. No automatic retries.
    """

    def __init__(self, provider: str = "anthropic", api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 pricing_per_mtok: Optional[Mapping[str, float]] = None,
                 timeout: float = 30.0) -> None:
        if provider not in ("anthropic", "openai"):
            raise ValueError("Supported providers: anthropic, openai")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Specify a model available to your provider account")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY", "")
        if not self.api_key:
            raise ValueError(f"Set {provider.upper()}_API_KEY or pass api_key")
        self.timeout = timeout
        self.rates = None
        if pricing_per_mtok is not None:
            if set(pricing_per_mtok) != {"input", "output", "cache_read", "cache_write"}:
                raise ValueError("Rates must contain input, output, cache_read, cache_write")
            if any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) or v < 0 for v in pricing_per_mtok.values()):
                raise ValueError("Rates must be finite non-negative numbers")
            self.rates = dict(pricing_per_mtok)

    def execute_turn(self, system_prompt: str, history: Sequence[Dict[str, Any]],
                     user_message: str, enable_prompt_cache: bool = True
                     ) -> Tuple[str, ExecutionTelemetry]:
        """Send full history. The flag controls Anthropic's system breakpoint.

        OpenAI caching is provider-managed; this flag cannot disable it.
        Tool calls, structured inputs and incomplete responses are unsupported.
        Network and provider errors propagate, without automatic resubmission.
        """
        if not isinstance(system_prompt, str) or not isinstance(user_message, str):
            raise ValueError("system_prompt and user_message must be strings")
        messages = copy.deepcopy(list(history))
        for message in messages:
            if (not isinstance(message, dict)
                    or set(message) != {"role", "content"}
                    or message["role"] not in ("user", "assistant")
                    or not isinstance(message["content"], str)):
                raise ValueError("History supports only user/assistant text messages (role, content)")
        messages.append({"role": "user", "content": user_message})
        if self.provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
            system = ([{"type": "text", "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}}]
                      if enable_prompt_cache else system_prompt)
            body = {"model": self.model, "max_tokens": 4096,
                    "system": system, "messages": messages}
        else:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            body = {"model": self.model, "messages":
                    [{"role": "system", "content": system_prompt}] + messages}
        headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if self.provider == "anthropic":
            if data.get("stop_reason") != "end_turn":
                raise ValueError("Incomplete or unsupported Anthropic response")
            blocks = data.get("content", [])
            if not blocks or any(b.get("type") != "text" for b in blocks):
                raise ValueError("Only text responses are supported")
            text = "".join(b["text"] for b in blocks)
        else:
            choice = data["choices"][0]
            if (choice.get("finish_reason") != "stop"
                    or choice["message"].get("tool_calls")
                    or not isinstance(choice["message"].get("content"), str)):
                raise ValueError("Incomplete or unsupported OpenAI response")
            text = choice["message"]["content"]
        return text, self._telemetry(data.get("usage", {}))

    def _telemetry(self, usage: Dict[str, Any]) -> ExecutionTelemetry:
        if self.provider == "anthropic":
            regular = usage.get("input_tokens")
            read = usage.get("cache_read_input_tokens", 0)
            write = usage.get("cache_creation_input_tokens", 0)
            output = usage.get("output_tokens")
            total = regular + read + write if regular is not None else None
        else:
            total = usage.get("prompt_tokens")
            read = usage.get("prompt_tokens_details", {}).get("cached_tokens")
            write = usage.get("prompt_tokens_details", {}).get("cache_write_tokens", 0)
            output = usage.get("completion_tokens")
            regular = total - read - write if total is not None and read is not None else None
        counts = (regular, read, write, output)
        if any(v is not None and (type(v) is not int or v < 0) for v in counts):
            raise ValueError("Invalid provider token accounting")
        cost = baseline = None
        supported_pricing = self.provider == "anthropic" or write == 0
        if self.rates is not None and supported_pricing and all(v is not None for v in counts):
            r = self.rates
            cost = (regular * r["input"] + read * r["cache_read"]
                    + write * r["cache_write"] + output * r["output"]) / 1_000_000
            baseline = (total * r["input"] + output * r["output"]) / 1_000_000
        return ExecutionTelemetry(self.provider, self.model, total, output, read, write, cost, baseline)
