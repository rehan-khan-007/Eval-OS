# EvalOS

LLM Evaluation & Benchmarking Framework.

A reproducible evaluation and benchmarking framework for RAG and LLM systems, supporting retrieval evaluation, claim-level hallucination analysis, LLM-as-a-Judge, latency/cost profiling, and automated regression testing.

## Architecture

```
evalos/
├── src/evalos/    — Core framework
│   ├── retrieval/     — BM25, dense, hybrid, reranking
│   ├── evaluation/    — Retrieval, generation, groundedness, hallucination, judge
│   ├── benchmarking/  — Runner, experiment, comparison, regression
│   ├── tracking/      — Run metadata, versioning, database
│   └── utils/         — Config, logging
├── configs/       — Reproducible experiment configs
├── experiments/   — Experiment artifacts
├── results/       — Benchmark outputs
├── scripts/       — CLI entry points
├── tests/         — Unit, integration, regression
├── notebooks/     — Analysis & visualization
└── docs/          — Methodology & protocols
```

## Status

🚧 Active development.