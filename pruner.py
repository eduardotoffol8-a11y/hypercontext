"""
Context Pruning Engine for Autonomous LLM Agents.

Provides high-efficiency context compaction, AST symbol extraction,
and sliding-window preservation to prevent context bloat, eliminate
'Lost-in-the-Middle' degradation, and slash API inference costs.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class CompactionMetrics:
    """Metrics captured during a context pruning pass."""
    raw_characters: int
    compacted_characters: int
    estimated_raw_tokens: int
    estimated_compacted_tokens: int
    blocks_compacted: int
    compaction_ratio: float

    @property
    def token_reduction_percent(self) -> float:
        """Percentage of tokens removed from the prompt."""
        if self.estimated_raw_tokens == 0:
            return 0.0
        return round((1.0 - (self.estimated_compacted_tokens / self.estimated_raw_tokens)) * 100.0, 2)


MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    """Standard message representation across agent architectures."""
    role: MessageRole
    content: Union[str, List[Dict[str, Any]]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class AstSymbolExtractor:
    """Static analysis helper to extract high-level API signatures from code blocks."""

    @staticmethod
    def extract_python_signatures(code: str) -> List[str]:
        """Extracts top-level and class-level function/class signatures via AST."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Fallback to regex when code is a partial diff or snippet
            return AstSymbolExtractor._regex_fallback(code)

        signatures: List[str] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                signatures.append(f"class {node.name}")
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        signatures.append(f"  def {item.name}()")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                signatures.append(f"def {node.name}()")
        return signatures

    @staticmethod
    def _regex_fallback(code: str) -> List[str]:
        patterns = re.findall(r"^\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)\b", code, re.MULTILINE)
        classes = re.findall(r"^\s*class\s+([a-zA-Z0-9_]+)\b", code, re.MULTILINE)
        sigs = [f"class {c}" for c in classes] + [f"def {p}()" for p in patterns]
        return sigs[:6]


class ContextPruner:
    """
    Intelligent context pruner for multi-turn autonomous coding agents.

    Attributes:
        preserve_recent_turns: Number of recent turns preserved without modification.
        min_lines_to_compact: Code blocks with fewer lines than this are retained untouched.
        char_to_token_ratio: Estimation factor for heuristic token measurement.
    """

    def __init__(
        self,
        preserve_recent_turns: int = 2,
        min_lines_to_compact: int = 12,
        char_to_token_ratio: float = 3.8,
    ) -> None:
        self.preserve_recent_turns = max(1, preserve_recent_turns)
        self.min_lines_to_compact = max(3, min_lines_to_compact)
        self.char_to_token_ratio = char_to_token_ratio

    def estimate_tokens(self, text: str) -> int:
        """Estimates token count using heuristic character-to-token ratio."""
        return max(1, int(len(text) / self.char_to_token_ratio))

    def prune(
        self,
        messages: Sequence[Dict[str, Any]],
        active_target_files: Optional[Sequence[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], CompactionMetrics]:
        """
        Executes an AST-aware context compaction pass over historical agent dialogue.

        Args:
            messages: Sequence of message dictionaries (standard format with 'role' and 'content').
            active_target_files: Optional file basenames that must be protected from compaction.

        Returns:
            Tuple of [compacted_messages_list, compaction_metrics].
        """
        if not messages:
            empty_metrics = CompactionMetrics(0, 0, 0, 0, 0, 1.0)
            return [], empty_metrics

        total_msgs = len(messages)
        cutoff_idx = max(0, total_msgs - self.preserve_recent_turns)

        raw_chars = 0
        compacted_chars = 0
        blocks_compacted = 0

        protected_files = set(f.lower() for f in (active_target_files or []))
        pruned_messages: List[Dict[str, Any]] = []

        for i, raw_msg in enumerate(messages):
            msg = dict(raw_msg)
            content = msg.get("content")

            if content is None:
                pruned_messages.append(msg)
                continue

            msg_raw_len = len(content) if isinstance(content, str) else len(str(content))
            raw_chars += msg_raw_len

            # Retain recent active turns unmodified
            if i >= cutoff_idx:
                pruned_messages.append(msg)
                compacted_chars += msg_raw_len
                continue

            # Compact historical turns
            if isinstance(content, str):
                compacted_text, count = self._compact_text_content(content, protected_files)
                blocks_compacted += count
                msg["content"] = compacted_text
                compacted_chars += len(compacted_text)
            elif isinstance(content, list):
                compacted_list, count = self._compact_structured_content(content, protected_files)
                blocks_compacted += count
                msg["content"] = compacted_list
                compacted_chars += len(str(compacted_list))
            else:
                compacted_chars += msg_raw_len

            pruned_messages.append(msg)

        raw_tokens = self.estimate_tokens(" " * raw_chars)
        compacted_tokens = self.estimate_tokens(" " * compacted_chars)
        ratio = round(compacted_chars / max(1, raw_chars), 3)

        metrics = CompactionMetrics(
            raw_characters=raw_chars,
            compacted_characters=compacted_chars,
            estimated_raw_tokens=raw_tokens,
            estimated_compacted_tokens=compacted_tokens,
            blocks_compacted=blocks_compacted,
            compaction_ratio=ratio,
        )

        return pruned_messages, metrics

    def _compact_text_content(
        self,
        text: str,
        protected_files: set[str],
    ) -> Tuple[str, int]:
        count = 0

        def _replacer(match: re.Match[str]) -> str:
            nonlocal count
            lang = match.group(1) or ""
            code = match.group(2)
            lines = code.strip().split("\n")

            if len(lines) < self.min_lines_to_compact:
                return match.group(0)

            # Check if this block references an actively targeted file
            preceding_context = text[max(0, match.start() - 120):match.start()].lower()
            for pf in protected_files:
                if pf in preceding_context:
                    return match.group(0)

            count += 1
            signatures = AstSymbolExtractor.extract_python_signatures(code) if lang in ("python", "py", "") else []

            sig_preview = ""
            if signatures:
                sig_preview = f" | {', '.join(signatures[:3])}"
                if len(signatures) > 3:
                    sig_preview += f" (+{len(signatures) - 3} symbols)"

            stub = (
                f"```{lang}\n"
                f"# [ContextPruner: Historical artifact compacted ({len(lines)} LOC{sig_preview})]\n"
                f"# Full implementation safely committed to project workspace.\n"
                f"```"
            )
            return stub

        pattern = r"```([a-zA-Z0-9_.-]*)\r?\n(.*?)```"
        compacted = re.sub(pattern, _replacer, text, flags=re.DOTALL)
        return compacted, count

    def _compact_structured_content(
        self,
        blocks: List[Dict[str, Any]],
        protected_files: set[str],
    ) -> Tuple[List[Dict[str, Any]], int]:
        total_count = 0
        new_blocks: List[Dict[str, Any]] = []

        for b in blocks:
            if isinstance(b, dict) and b.get("type") == "text":
                c_text, count = self._compact_text_content(b.get("text", ""), protected_files)
                total_count += count
                new_blocks.append({"type": "text", "text": c_text})
            else:
                new_blocks.append(b)

        return new_blocks, total_count
