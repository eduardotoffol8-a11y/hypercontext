"""Build or send one Messages API request with native cache/context controls.

Default: preview JSON locally. --send is the only mode that accesses the network.
This recipe does not execute tools or alter/rewrite historical message content.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, Tuple
import urllib.error
import urllib.request


POLICY = {
    "edits": [{
        "type": "clear_tool_uses_20250919",
        "trigger": {"type": "input_tokens", "value": 30000},
        "keep": {"type": "tool_uses", "value": 3},
        "clear_at_least": {"type": "input_tokens", "value": 5000},
        "exclude_tools": ["read_requirements"],
        "clear_tool_inputs": False,
    }]
}


def build_request(source: Dict[str, Any], *, model: str, cache: bool = True,
                  prune: bool = False) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Copy a native request and add explicit controls, preserving tool history.

    The pruning preset is for disposable, retrievable tool results only. The
    application must retain authoritative state before enabling it.
    """
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Select a model available to your Anthropic account")
    if not isinstance(source, dict):
        raise ValueError("Input must be a Messages API JSON object")
    body = copy.deepcopy(source)
    system = body.get("system")
    if not isinstance(system, str) or not system.strip():
        raise ValueError("This recipe requires a non-empty system string")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    if any(not isinstance(m, dict) or m.get("role") not in ("user", "assistant")
           or "content" not in m for m in messages):
        raise ValueError("Messages must have a native user/assistant role and content")
    if type(body.get("max_tokens")) is not int or body["max_tokens"] <= 0:
        raise ValueError("max_tokens must be a positive integer")
    if body.get("stream"):
        raise ValueError("Streaming is outside this single-request recipe")
    if "context_management" in body:
        raise ValueError("Remove existing context_management before applying this recipe")
    body["model"] = model
    if cache:
        body["system"] = [{"type": "text", "text": system,
                           "cache_control": {"type": "ephemeral"}}]
    headers = {"anthropic-version": "2023-06-01", "content-type": "application/json"}
    if prune:
        body["context_management"] = copy.deepcopy(POLICY)
        headers["anthropic-beta"] = "context-management-2025-06-27"
    return body, headers


def send_request(body: Dict[str, Any], headers: Dict[str, str], *, api_key: str,
                 timeout: float = 30.0) -> Dict[str, Any]:
    """Send once; return full native response, including usage and applied edits.

    A tool_use stop is a request for the caller's tool loop, not a completed task.
    Network/API errors propagate; no automatic retry or tool execution occurs.
    """
    if not api_key:
        raise ValueError("Set ANTHROPIC_API_KEY for --send")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={**headers, "x-api-key": api_key},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("request.example.json"))
    parser.add_argument("--model", default=os.getenv("ANTHROPIC_MODEL"))
    parser.add_argument("--prune-tools", action="store_true", help="Enable native beta tool-result clearing")
    parser.add_argument("--no-cache", action="store_true", help="Omit the explicit system cache breakpoint")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preview", action="store_true", help="Print request JSON locally (default)")
    mode.add_argument("--send", action="store_true", help="Send one billable API request")
    args = parser.parse_args()
    try:
        if args.send and not args.model:
            raise ValueError("Set ANTHROPIC_MODEL or pass --model for --send")
        source = json.loads(args.input.read_text(encoding="utf-8-sig"))
        body, headers = build_request(source, model=args.model or "SELECT_AN_AVAILABLE_MODEL",
                                      cache=not args.no_cache, prune=args.prune_tools)
        if args.send:
            result = send_request(body, headers, api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        else:
            result = {"mode": "preview", "headers": headers, "body": body}
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, urllib.error.URLError) as error:
        print(f"Request failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
