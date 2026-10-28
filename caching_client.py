"""
Production Prompt Caching Client for Frontier & Local Agent Architectures.

Provides unified interface across:
- Anthropic Claude (Opus 3.5/5.5, Sonnet 3.5) via Ephemeral Prompt Caching
- OpenAI (GPT-4o) via Automatic Prefix Caching
- Local Inferences (vLLM, SGLang, llama.cpp) via Slot/Radix KV Cache
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Union

from pruner import CompactionMetrics, ContextPruner

ProviderType = Literal["anthropic", "openai", "local"]


@dataclass(frozen=True)
class ExecutionTelemetry:
    """Detailed telemetry and cost economics of an agent invocation."""
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    estimated_cost_usd: float
    estimated_baseline_cost_usd: float
    compaction: Optional[CompactionMetrics] = None

    @property
    def cost_savings_usd(self) -> float:
        """Net monetary savings achieved via Caching and Pruning."""
        return max(0.0, round(self.estimated_baseline_cost_usd - self.estimated_cost_usd, 5))

    @property
    def cost_savings_percent(self) -> float:
        """Percentage saved compared to un-optimized full-context invocation."""
        if self.estimated_baseline_cost_usd == 0:
            return 0.0
        return round((self.cost_savings_usd / self.estimated_baseline_cost_usd) * 100.0, 1)


class CloudAgentClient:
    """
    Unified client orchestrating Context Pruning and Prompt Caching.

    Ensures prompt stability to maximize cache hits, while stripping
    historical redundancies via the ContextPruner pipeline.
    """

    PRICING_PER_MTOK = {
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_write": 18.75},
        "gpt-4o": {"input": 2.50, "output": 10.00, "cache_read": 1.25, "cache_write": 2.50},
        "local": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0},
    }

    def __init__(
        self,
        provider: ProviderType = "anthropic",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        preserve_recent_turns: int = 2,
    ) -> None:
        self.provider: ProviderType = provider
        self.api_key: str = api_key or os.getenv(f"{self.provider.upper()}_API_KEY", "")
        self.model: str = model or self._default_model_for_provider()
        self.pruner = ContextPruner(preserve_recent_turns=preserve_recent_turns)

    def _default_model_for_provider(self) -> str:
        if self.provider == "anthropic":
            return "claude-3-5-sonnet-20241022"
        elif self.provider == "openai":
            return "gpt-4o"
        return "local-model"

    def execute_turn(
        self,
        system_prompt: str,
        history: Sequence[Dict[str, Any]],
        user_message: str,
        enable_prompt_cache: bool = True,
        enable_context_pruning: bool = True,
        active_target_files: Optional[Sequence[str]] = None,
    ) -> Tuple[str, ExecutionTelemetry]:
        """
        Executes a production-optimized agent turn.

        1. Performs Context Pruning on historical turns to truncate dead code.
        2. Configures Ephemeral Prompt Caching on the static System Prompt.
        3. Returns the LLM response alongside verified telemetry.
        """
        compacted_history: List[Dict[str, Any]]
        compaction_metrics: Optional[CompactionMetrics] = None

        if enable_context_pruning:
            compacted_history, compaction_metrics = self.pruner.prune(history, active_target_files)
        else:
            compacted_history = list(history)

        full_messages = list(compacted_history) + [{"role": "user", "content": user_message}]

        if self.provider == "anthropic":
            response_text, telemetry = self._call_anthropic(system_prompt, full_messages, enable_prompt_cache, compaction_metrics)
        elif self.provider == "openai":
            response_text, telemetry = self._call_openai(system_prompt, full_messages, compaction_metrics)
        elif self.provider == "local":
            response_text, telemetry = self._call_local(system_prompt, full_messages, compaction_metrics)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        return response_text, telemetry

    def _call_anthropic(
        self,
        system: str,
        messages: List[Dict[str, Any]],
        use_cache: bool,
        compaction: Optional[CompactionMetrics],
    ) -> Tuple[str, ExecutionTelemetry]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Structure system prompt with Anthropic cache_control
        system_payload: Any
        if use_cache:
            system_payload = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_payload = system

        body = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_payload,
            "messages": messages,
        }

        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        usage = data.get("usage", {})
        content = "".join([c.get("text", "") for c in data.get("content", []) if c.get("type") == "text"])

        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)

        cost, baseline = self._calculate_costs(self.model, in_tok, out_tok, cache_read, cache_write, compaction)

        telemetry = ExecutionTelemetry(
            provider="anthropic",
            model=self.model,
            prompt_tokens=in_tok,
            completion_tokens=out_tok,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            estimated_cost_usd=cost,
            estimated_baseline_cost_usd=baseline,
            compaction=compaction,
        )

        return content, telemetry

    def _call_openai(
        self,
        system: str,
        messages: List[Dict[str, Any]],
        compaction: Optional[CompactionMetrics],
    ) -> Tuple[str, ExecutionTelemetry]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        all_msgs = [{"role": "system", "content": system}] + messages
        body = {"model": self.model, "messages": all_msgs}

        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        choice = data["choices"][0]
        usage = data.get("usage", {})
        cached_tok = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)

        cost, baseline = self._calculate_costs(self.model, in_tok, out_tok, cached_tok, 0, compaction)

        telemetry = ExecutionTelemetry(
            provider="openai",
            model=self.model,
            prompt_tokens=in_tok,
            completion_tokens=out_tok,
            cache_read_tokens=cached_tok,
            cache_write_tokens=0,
            estimated_cost_usd=cost,
            estimated_baseline_cost_usd=baseline,
            compaction=compaction,
        )

        return choice["message"]["content"], telemetry

    def _call_local(
        self,
        system: str,
        messages: List[Dict[str, Any]],
        compaction: Optional[CompactionMetrics],
    ) -> Tuple[str, ExecutionTelemetry]:
        url = "http://127.0.0.1:18101/completion"
        prompt_text = f"<|im_start|>system\n{system}<|im_end|>\n"
        for m in messages:
            prompt_text += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
        prompt_text += "<|im_start|>assistant\n"

        body = {
            "prompt": prompt_text,
            "n_predict": 2048,
            "cache_prompt": True,
        }
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        out_tok = data.get("tokens_predicted", 0)
        telemetry = ExecutionTelemetry(
            provider="local",
            model="qwen3-8b",
            prompt_tokens=self.pruner.estimate_tokens(prompt_text),
            completion_tokens=out_tok,
            cache_read_tokens=0,
            cache_write_tokens=0,
            estimated_cost_usd=0.0,
            estimated_baseline_cost_usd=0.0,
            compaction=compaction,
        )
        return data.get("content", ""), telemetry

    def _calculate_costs(
        self,
        model: str,
        in_tokens: int,
        out_tokens: int,
        cache_read: int,
        cache_write: int,
        compaction: Optional[CompactionMetrics],
    ) -> Tuple[float, float]:
        rates = self.PRICING_PER_MTOK.get(model, self.PRICING_PER_MTOK["claude-3-5-sonnet-20241022"])

        # Cost under optimization:
        regular_in = max(0, in_tokens - cache_read - cache_write)
        cost = (
            (regular_in * rates["input"] / 1_000_000)
            + (cache_read * rates["cache_read"] / 1_000_000)
            + (cache_write * rates["cache_write"] / 1_000_000)
            + (out_tokens * rates["output"] / 1_000_000)
        )

        # Baseline cost without Caching or Pruning:
        baseline_in = in_tokens
        if compaction and compaction.estimated_raw_tokens > compaction.estimated_compacted_tokens:
            diff = compaction.estimated_raw_tokens - compaction.estimated_compacted_tokens
            baseline_in += diff

        baseline_cost = (baseline_in * rates["input"] / 1_000_000) + (out_tokens * rates["output"] / 1_000_000)
        return round(cost, 6), round(baseline_cost, 6)
