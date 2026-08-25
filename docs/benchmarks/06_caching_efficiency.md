# Evaluation Caching & Cost Efficiency

**What was measured:** The cost and latency reduction when running the exact same evaluation benchmark twice, leveraging the Upstash Redis caching layer.

**How:** `python cli.py run-eval --system rag --model openai/gpt-4o-mini --retriever dense`. EvalOS hashes the system prompt, user context, and model name. If the hash exists in Redis, it returns the cached LLM generation and LLM Judge verdict instead of making an API call.

**Result:**

| Run | Total Cost | Avg Latency | Cache Status |
|---|---|---|---|
| Run 1 (Cold) | **$0.0065** | 5.37s | Cache Miss (Populated Redis) |
| Run 2 (Hot) | **$0.0000** | < 1.0s* | Cache Hit (100% Hit Rate) |

*\*Latency on Run 2 is drastically reduced as it only measures the Postgres retrieval and Redis I/O, completely bypassing the OpenRouter LLM generation and Judge API calls.*

**Honest caveats:**
- The cache is keyed on the exact prompt, context, and model. If you change a single character in the system prompt, it will cache miss and charge you again. 
- This proves EvalOS is highly suitable for iterative development: you can tweak your retrieval pipeline (e.g., switching from Dense to Hybrid) and re-run the exact same dataset to see how the *new context* affects the LLM, without paying for the LLM generation twice if the context happens to remain identical.
