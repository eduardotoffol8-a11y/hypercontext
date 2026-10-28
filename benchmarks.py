"""Offline arithmetic scenarios, NOT an empirical benchmark or current price list."""
from caching_client import CloudAgentClient


def run_multi_turn_simulation():
    # Illustrative rates, deliberately independent of any current model price.
    client = CloudAgentClient(api_key="offline-placeholder", model="illustrative-model",
        pricing_per_mtok={"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75})
    print("ILLUSTRATIVE INPUT-ONLY COST SCENARIOS (no API, no latency/quality measurement)")
    print("Assumptions: 2500-token prefix, 100-token suffix, zero output; arbitrary USD/MTok rates.")
    print("All requests contain the same total number of tokens. Nothing is pruned.")
    scenarios = [
        ("No caching", {"input_tokens": 2600, "output_tokens": 0}),
        ("Cold cache write", {"input_tokens": 100, "output_tokens": 0,
                              "cache_creation_input_tokens": 2500}),
        ("Warm cache read", {"input_tokens": 100, "output_tokens": 0,
                             "cache_read_input_tokens": 2500}),
        ("Expired cache rewrite", {"input_tokens": 100, "output_tokens": 0,
                                   "cache_creation_input_tokens": 2500}),
    ]
    for label, usage in scenarios:
        result = client._telemetry(usage)
        print(f"{label}: total={result.prompt_tokens}, cost=${result.estimated_cost_usd:.6f}, "
              f"difference from uncached={result.cost_savings_percent:.1f}%")
    print("Actual savings require observed cache usage and current rates; they are not guaranteed.")


if __name__ == "__main__":
    run_multi_turn_simulation()
