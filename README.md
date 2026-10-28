# HyperContext

A small Python reference implementation of provider-native prompt caching and
token-usage accounting for text conversations. Runtime uses only the Python
standard library. This is an educational project, not a production agent platform.

## What this project demonstrates

- An explicit cache breakpoint on an Anthropic system prompt.
- Stable system instructions at the beginning of OpenAI Chat Completions requests;
  actual cache reuse is managed by the provider.
- Provider-specific token accounting and optional cost estimates using rates you supply.
- Complete preservation of submitted message history, including old code blocks.

Cache reuse depends on the model, exact matching prefix, cache lifetime, request
length and provider routing. This client cannot guarantee cache hits or savings.
Caching does not shrink the context window or prevent context overflow.

## Why the scope changed in 0.2.0

An audit found that the previous code-block pruning policy could remove relevant
information and claim that code had been committed without checking any files or
Git state. That functionality has been removed, including the `ContextPruner` API.
The old simulated savings table, static passing-test badge, performance guarantees,
and unverified local-inference compatibility claims have also been removed.

The historical benchmark did not measure API bills, latency, task completion or
answer quality. Its results must not be presented as measured production savings.
See [the audit and validation record](docs/AUDIT.md).

## Run locally

Requires Python 3.9 or newer. Local validation was performed with Python 3.11;
the repository CI defines additional version checks.

```bash
git clone https://github.com/eduardotoffol8-a11y/hypercontext.git
cd hypercontext
python -m unittest discover -s tests -p "test_*.py"
python example_agent.py
python benchmarks.py
```

The example and cost simulation run offline and do not require credentials.
The file `benchmarks.py` is retained for command compatibility: it is an arithmetic
scenario illustration, not an empirical performance benchmark.

## Calling a provider

Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in your environment. Select a model
currently available to your account; the client has no hardcoded model default.

```python
import os
from caching_client import CloudAgentClient

client = CloudAgentClient(provider="anthropic", model=os.environ["ANTHROPIC_MODEL"])
answer, usage = client.execute_turn(
    system_prompt="You review code and preserve user requirements.",
    history=[{"role": "user", "content": "All exported dates must use UTC."}],
    user_message="Explain the requirement you must preserve.",
)
print(answer)
print(usage.prompt_tokens, usage.cache_read_tokens)
```

This sends your supplied system prompt, history and current message to the selected
provider. Use only data you are authorized to send. The library does not log API keys,
persist conversations, execute generated code, edit files or make Git commits.
Provider retention and privacy terms still apply; caching is not a security boundary.

## Accounting and limitations

- Anthropic: total prompt tokens are `input_tokens + cache_read_input_tokens +
  cache_creation_input_tokens`. The uncached input bucket must not have cache
  tokens subtracted a second time.
- OpenAI Chat Completions: `prompt_tokens` includes cached tokens. The client
  subtracts the cached subset to determine regular input. It does not implement
  Responses API or explicit OpenAI cache breakpoints. If cache-write usage is
  reported, monetary estimates are left unknown because newer write/TTL pricing
  is outside this adapter's supported accounting scope.
- Pass `pricing_per_mtok` with `input`, `output`, `cache_read`, and `cache_write`
  rates in USD per million tokens to enable supported cost estimates. Check the
  provider's current model, tier and cache-lifetime rates yourself. No guessed rates
  are used. Omitted usage information can make estimates unavailable (`None`).
- The baseline is the *same request and output* billed at the supplied regular
  rates, without cache discounts. It is a hypothetical comparison, not a measured
  second run. Savings can be negative, especially on a cold cache write.
- Text-only, synchronous requests. Tool calls, multimodal inputs, streaming,
  durable memory and automatic retries are outside scope. Unsupported history
  formats and incomplete responses raise errors rather than silently losing content.
- `enable_prompt_cache=False` removes the explicit Anthropic breakpoint. OpenAI's
  automatic cache cannot be disabled with this flag.
- Full history continues to grow. Callers must handle context limits; this project
  does not promise bounded memory, preserved model reasoning or prompt-injection protection.
- Unit tests replace network I/O with fixtures. They verify this client's behavior,
  not provider uptime, real cache hits, model availability or production readiness.

## Established techniques and primary sources

Prompt caching is a documented provider feature. Anthropic also describes context
compaction in Claude Code, with explicit warnings about losing critical details.
Those references validate the techniques; they do not establish adoption or
endorsement of this repository.

- [Anthropic prompt caching and usage fields](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Anthropic context engineering and compaction tradeoffs](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)

MIT license. See [LICENSE](LICENSE).
