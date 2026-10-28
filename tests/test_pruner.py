"""
Unit test suite for Context Pruning Engine.
"""

import unittest
from pruner import ContextPruner, AstSymbolExtractor


class TestContextPruner(unittest.TestCase):

    def setUp(self):
        self.pruner = ContextPruner(preserve_recent_turns=2, min_lines_to_compact=10)

    def test_empty_messages(self):
        pruned, metrics = self.pruner.prune([])
        self.assertEqual(len(pruned), 0)
        self.assertEqual(metrics.blocks_compacted, 0)
        self.assertEqual(metrics.compaction_ratio, 1.0)

    def test_short_messages_not_compacted(self):
        messages = [
            {"role": "user", "content": "Hello, write a function."},
            {"role": "assistant", "content": "```python\ndef add(a, b):\n    return a + b\n```"}
        ]
        pruned, metrics = self.pruner.prune(messages)
        self.assertEqual(len(pruned), 2)
        # Because lines < min_lines_to_compact and within recent turns:
        self.assertEqual(metrics.blocks_compacted, 0)
        self.assertIn("return a + b", pruned[1]["content"])

    def test_historical_large_code_compaction(self):
        long_code = "\n".join([f"def function_{i}(x: int) -> int:\n    return x * {i}" for i in range(20)])
        messages = [
            {"role": "user", "content": "Initial request"},
            {"role": "assistant", "content": f"### math_utils.py\n```python\n{long_code}\n```"},
            {"role": "user", "content": "Turn 2 question"},
            {"role": "assistant", "content": "Turn 2 answer"},
            {"role": "user", "content": "Turn 3 question (latest)"}
        ]

        pruned, metrics = self.pruner.prune(messages)
        self.assertEqual(len(pruned), 5)
        self.assertEqual(metrics.blocks_compacted, 1)
        self.assertTrue(metrics.token_reduction_percent > 30.0)

        # The historical assistant message should contain the compaction stub
        compacted_msg = pruned[1]["content"]
        self.assertIn("ContextPruner: Historical artifact compacted", compacted_msg)
        self.assertNotIn("function_19", compacted_msg)

        # Recent messages must remain untouched
        self.assertEqual(pruned[4]["content"], "Turn 3 question (latest)")

    def test_protected_active_files_not_compacted(self):
        long_code = "\n".join([f"val_{i} = {i}" for i in range(25)])
        messages = [
            {"role": "user", "content": "Check config.py"},
            {"role": "assistant", "content": f"Here is config.py:\n```python\n{long_code}\n```"},
            {"role": "user", "content": "Turn 2"},
            {"role": "assistant", "content": "Turn 2 ans"},
            {"role": "user", "content": "Latest"}
        ]

        # Protecting 'config.py' prevents compaction even in historical turn
        pruned, metrics = self.pruner.prune(messages, active_target_files=["config.py"])
        self.assertEqual(metrics.blocks_compacted, 0)
        self.assertIn("val_24", pruned[1]["content"])

    def test_ast_symbol_extractor(self):
        sample_code = """
class DataPipeline:
    def process(self):
        pass

    async def fetch_async(self):
        pass

def standalone_helper():
    pass
"""
        symbols = AstSymbolExtractor.extract_python_signatures(sample_code)
        self.assertIn("class DataPipeline", symbols)
        self.assertIn("  def process()", symbols)
        self.assertIn("  def fetch_async()", symbols)
        self.assertIn("def standalone_helper()", symbols)


if __name__ == "__main__":
    unittest.main()
