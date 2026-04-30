# Implementation Context Map

## Purpose

This map links implementation source files to the context artifacts that cover their behavior. Context artifacts are intentionally feature/flow oriented, not one-source-file-per-context, so some files have multiple relevant contexts.

Generated files such as `news_ranker/__pycache__/*.pyc` are not implementation source and are excluded.

## Coverage map

| Source file | Primary context | Secondary context(s) | Notes |
| --- | --- | --- | --- |
| `news_ranker/__init__.py` | `docs/context/ranking-pipeline-public-api.md` | `docs/context/config-knobs.md`, `docs/context/decomposition-embedding.md`, `docs/context/mistral-llm-provider.md` | Root public export boundary and `health()`; Mistral client intentionally submodule-only. |
| `news_ranker/cluster.py` | `docs/context/fact-clustering.md` | `docs/context/ranking-pipeline-public-api.md`, `docs/context/scoring.md`, `docs/context/ranking-evaluation-helpers.md`, `docs/context/config-knobs.md` | Fact flattening, clustering, coverage matrix, diagnostics inputs. |
| `news_ranker/config.py` | `docs/context/config-knobs.md` | `docs/context/ranking-pipeline-public-api.md`, `docs/context/mistral-llm-provider.md`, `docs/context/scoring.md`, `docs/context/fact-clustering.md`, `docs/context/decomposition-embedding.md` | `RankerConfig`, defaults, validation, consumer knobs, Mistral LLM model metadata. |
| `news_ranker/decompose.py` | `docs/context/decomposition-embedding.md` | `docs/context/mistral-llm-provider.md`, `docs/context/ranking-pipeline-public-api.md`, `docs/context/config-knobs.md` | Provider-agnostic decomposition, retry, cache behavior, Mistral default model name. |
| `news_ranker/embed.py` | `docs/context/decomposition-embedding.md` | `docs/context/fact-clustering.md`, `docs/context/scoring.md`, `docs/context/ranking-pipeline-public-api.md` | Fact embeddings, local embedder boundary, article vector construction. |
| `news_ranker/evaluate.py` | `docs/context/ranking-evaluation-helpers.md` | `docs/context/fact-clustering.md`, `docs/context/scoring.md`, `docs/context/ranking-pipeline-public-api.md` | Downstream comparison, inspection, and study-bundle helpers. |
| `news_ranker/mistral.py` | `docs/context/mistral-llm-provider.md` | `docs/context/decomposition-embedding.md`, `docs/context/ranking-pipeline-public-api.md`, `docs/context/config-knobs.md` | Mistral-specific decomposition client adapter; submodule-only provider integration. |
| `news_ranker/pipeline.py` | `docs/context/ranking-pipeline-public-api.md` | `docs/context/decomposition-embedding.md`, `docs/context/mistral-llm-provider.md`, `docs/context/fact-clustering.md`, `docs/context/scoring.md`, `docs/context/config-knobs.md`, `docs/context/ranking-evaluation-helpers.md` | Public orchestration across loading, embedding, clustering, scoring, ranking, selection; raw-dict decomposer hook used by provider adapters. |
| `news_ranker/prompts.py` | `docs/context/decomposition-embedding.md` | — | Prompt constants and raw-article user prompt construction. |
| `news_ranker/results.py` | `docs/context/ranking-pipeline-public-api.md` | `docs/context/ranking-evaluation-helpers.md`, `docs/context/scoring.md`, `docs/context/fact-clustering.md` | Frozen result records produced by pipeline and consumed by helpers. |
| `news_ranker/schemas.py` | `docs/context/decomposition-embedding.md` | `docs/context/fact-clustering.md`, `docs/context/scoring.md`, `docs/context/ranking-pipeline-public-api.md` | Structured article schema, fixture loading, fact text/item ordering. |
| `news_ranker/score.py` | `docs/context/scoring.md` | `docs/context/ranking-pipeline-public-api.md`, `docs/context/config-knobs.md`, `docs/context/ranking-evaluation-helpers.md` | Component formulas, normalization, weighted combination. |
| `news_ranker/select.py` | `docs/context/ranking-pipeline-public-api.md` | `docs/context/config-knobs.md`, `docs/context/scoring.md` | Top-score and MMR selection helpers used by pipeline. |

## Maintenance rule

When adding or renaming implementation files under `news_ranker/`, update this index in the same change as the relevant feature context artifact. If a new file belongs to a new behavior area, create or update a feature/flow context rather than forcing a one-to-one file context.
