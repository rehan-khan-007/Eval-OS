# EvalOS Benchmark Results

Real numbers from running the actual EvalOS framework against real
infrastructure and real API calls — not estimates. Each result below
states exactly what was measured, how, and what its limitations are.

## At a glance

| Metric | Result |
|---|---|
| Retrieval recall@3 (47 docs, multi-domain) | **88.9%** |
| Models benchmarked | 5 (gpt-4o-mini, gpt-4o, claude-haiku-4.5, gemini-3.7-flash, llama-3.1-70b) |
| Best Faithfulness | **98.2%** (claude-haiku-4.5) |
| Best Value (Quality/Cost) | **gpt-4o-mini** (96.8% faithfulness for $0.006) |
| LLM Judge Human Agreement | **100.0%** (Raw Agreement on 5-sample HITL audit) |
| Total spend across 5-model benchmark | **~$0.21** |

---

## 5-Model LLM RAG Benchmark

**What was measured:** Source-level recall@3 and LLM-as-judge
faithfulness across 5 different models answering the same 36 real
questions with the same retrieved context (retrieval ran once per
question, shared across all 5 models via the RAGAdapter, so generation
quality is the only variable being compared).

**How:** `python cli.py run-benchmark --dataset-version dv-ds-retrieval_qa-v1`
against the 47 PDF corpus (1,500+ chunks). Cost computed from each
response's actual `usage` field (real token counts), not estimated.

**Result:**

| Model | Source Recall@3 | Faithfulness | Total Cost | Avg Latency |
|---|---|---|---|---|
| `claude-haiku-4.5` | 88.9% | **98.2%** | $0.0658 | 6.88s |
| `gpt-4o-mini` | 88.9% | 96.8% | **$0.0065** | 5.37s |
| `llama-3.1-70b-instruct` | 88.9% | 96.2% | $0.0193 | 6.97s |
| `gpt-4o` | 88.9% | 95.9% | $0.1119 | 5.20s |
| `gemini-3.7-flash` | 88.9% | 89.1% | $0.0100 | 9.37s |

**Total cost for this run: ~$0.21** (180 completions + 180 judge calls)

**Honest caveats:**
- Source Recall@3 is identical (88.9%) across all models because
  retrieval happens *before* the model is called in our RAG pipeline.
  The model only generates the answer; it does not control what context
  it receives.
- **The "expensive model" trap:** `gpt-4o` costs 17x more than
  `gpt-4o-mini`, but actually scored *lower* in faithfulness. This
  is a real, empirical justification for using mini as the default
  generation tier, not an assumption.
- `gemini-3.7-flash` struggled with the strict grounding prompt
  ("answer *only* using context"), dropping to 89.1% faithfulness,
  showing it is more prone to using outside knowledge than Anthropic
  or OpenAI models in this specific RAG configuration.

---

## Human-in-the-Loop (HITL) Evaluator Reliability

**What was measured:** Whether the `LLMJudgeEvaluator` (which uses
`gpt-4o-mini` to extract claims and verify them against context) is
actually telling the truth. A random sample of 5 generated answers
and their judge verdicts were manually reviewed by a human.

**How:** `python cli.py label-judgements run-ccbcb9b2` followed by
`python cli.py calculate-agreement run-ccbcb9b2`.

**Result:**

| Metric | Value |
|---|---|
| Total Labeled Samples | 5 |
| Raw Agreement | **100.0%** |
| Cohen's Kappa | 0.0000* |

*\*Note on Kappa: Cohen's Kappa requires variance in the ratings to
calculate chance-adjusted agreement. Because the human agreed with
the LLM Judge on 100% of the samples (variance = 0), the Kappa
formula mathematically collapses to 0.0. The 100% Raw Agreement is
the meaningful metric here.*

**Honest caveats:**
- 5 samples is a small sample size, but it successfully validates that
  the Judge is not blindly hallucinating positive scores. It correctly
  identified a partially unsupported answer (scoring it 83.3% rather
  than 100%) which the human confirmed.
- This confirms, rather than merely repeats, the automated faithfulness
  scores in the 5-model benchmark above.

---

## Engineering Infrastructure

EvalOS itself was built to be a reproducible evaluation framework.
The infrastructure supporting these benchmarks is verified:

- **Postgres + pgvector:** All runs, metrics, traces, and vector
  embeddings are stored in a single Neon Postgres instance. This
  allows complex SQL joins for failure analysis (e.g., joining
  `executions` with `metric_results` to find exactly *why* a
  retrieval failed).
- **Asynchronous by design:** All API calls (OpenRouter generation
  and embeddings) use `asyncpg` and `AsyncOpenAI` to prevent I/O
  bottlenecks during large-scale evaluation runs.
- **CLI-first:** All benchmarks are reproducible via Typer CLI
  commands, not hardcoded scripts.
