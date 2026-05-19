# News Article Ranking & Selection Library — Design Document

> A scoring library that takes *k* articles about the same news event, ranks them from best to worst, selects the best *M*, and compares alternative definitions of "best" using structured fact decomposition, embedding centrality, information coverage, and optional diversity.

---

## Table of Contents

1. [Overview](#overview)
2. [Scope & Assumptions](#scope-assumptions)
3. [Library Layout](#library-layout)
4. [Module-by-Module Plan](#module-plan)
5. [Pipeline Workflow](#pipeline-workflow)
6. [Implementation Order (Milestones)](#milestones)
7. [Decision Formulas](#decision-formulas)
8. [Public API](#public-api)
9. [Configuration Choices](#configuration-choices)
10. [Sanity-Check Identities](#sanity-check-identities)
11. [Evaluation & Comparison Plan](#evaluation-comparison-plan)

---

<a id="overview"></a>

## 1. Overview

The system takes a set of *k* news articles covering the same event and produces: (1) a full ranking, (2) an optional best-*M* selection, and (3) side-by-side comparisons across scoring profiles. The core insight is to **strip authorial style by converting each article into a structured "what happened" document** before embedding, so similarity reflects *content*, not *prose style*.

The default ranking combines four signals:

- **Centrality** — how close article content is to the consensus centroid in embedding space.
- **Coverage** — what fraction of the corpus's unique facts the article contains.
- **Density** — how much unique information per extracted entry the article carries (penalizes padding).
- **Entity coverage** — whether the article mentions key actors (optional / diagnostic).

For best-*M* selection, the library can add a **diversity** criterion so the selected set avoids near-duplicate articles. Different scoring profiles make "best" explicit: representative, comprehensive, concise, plus optional diversity-aware selection.

---

<a id="scope-assumptions"></a>

## 2. Scope & Assumptions

**Input contract.** A non-empty list of *k* articles, each a dict with at minimum `{"id": str, "title": str, "body": str}`. Optionally `{"source": str, "published_at": str, "url": str}`. The caller may also pass `top_m` where $1 \leq M \leq k$ and a scoring `profile`.

**Output contract.** A ranked list of `{"id": str, "score": float, "components": {...}, "rank": int}`, sorted descending by score; optional `selected` list of the best *M* articles; optional diagnostics for fact clusters, rare facts, and profile comparisons.

**Out of scope (for v1):**
- Article scraping or URL deduplication.
- Multilingual handling beyond what the embedder natively supports.
- External fact-checking against ground-truth sources.
- Detecting scoops vs. errors among rare facts (see [§7.2.2](#rarity-weighting)).

**Stack:**
- Python 3.11+
- `pydantic` v2 — schema validation
- `anthropic` or another chat-completions client — decomposition LLM
- `sentence-transformers` *or* OpenAI embeddings API
- `numpy` + `scikit-learn` — clustering, distances, pairwise similarity
- `pytest` — tests

---

<a id="library-layout"></a>

## 3. Library Layout

```
news_ranker/
├── __init__.py
├── schemas.py          # Pydantic models for the structured doc
├── decompose.py        # LLM call → structured JSON
├── embed.py            # Text → vectors
├── cluster.py          # Semantic fact deduplication
├── score.py            # Centrality, coverage, density, entity coverage
├── select.py           # Best-M selection, optional diversity/MMR
├── evaluate.py         # Criteria comparison helpers + user-study export
├── pipeline.py         # Orchestrator (the public API)
├── config.py           # Thresholds, weights, model names, profiles
└── prompts.py          # The decomposition system prompt
tests/
└── ...
```

---

<a id="module-plan"></a>

## 4. Module-by-Module Plan

### 4.1 `schemas.py` — the structured document

Pydantic models matching the JSON schema used for decomposition: `Entity`, `Event`, `Claim`, `StructuredArticle`. Strict validation so a malformed LLM response fails fast and can be retried.

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Entity(StrictModel):
    canonical_name: str
    type: Literal["person", "organization", "location", "event", "other"]
    aliases: list[str] = Field(default_factory=list)


class Entities(StrictModel):
    people: list[Entity] = Field(default_factory=list)
    organizations: list[Entity] = Field(default_factory=list)
    locations: list[Entity] = Field(default_factory=list)
    events: list[Entity] = Field(default_factory=list)
    other: list[Entity] = Field(default_factory=list)


class Event(StrictModel):
    id: str
    when: str | None = None
    who: list[str] = Field(default_factory=list)
    what: str
    where: str | None = None
    why: str | None = None
    how: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class Claim(StrictModel):
    id: str
    statement: str
    type: Literal["fact", "quote", "estimate", "prediction"]
    attributed_to: str | None = None


class StructuredArticle(StrictModel):
    article_id: str
    headline_neutral: str
    topic: str
    entities: Entities = Field(default_factory=Entities)
    events: list[Event] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    context: list[str] = Field(default_factory=list)
```

### 4.2 `prompts.py` — the decomposition rules

Holds the system prompt verbatim. Rules:

1. **Atomicity** — each event/claim is one fact.
2. **Neutrality** — strip adjectives/adverbs and rhetorical framing.
3. **Chronology** — order events by world-time, not article-time.
4. **Attribution** — every non-observable claim must have a source.
5. **No inference** — never add facts not in the article; use `null` for unknowns.
6. **Canonical entities** — resolve coreferences to one canonical name.
7. **Separation** — keep events, claims, and background context distinct.
8. **Output** — JSON only, matching the schema.

Keeping the prompt in one file makes prompt iteration clean.

### 4.3 `decompose.py` — article → structured doc

A single function `decompose(article) -> StructuredArticle`. Calls the LLM with the system prompt + title/body/source metadata, parses JSON, validates against the schema, and retries once on validation failure with the validation error fed back to the model. **Caches results on disk keyed by hash of the article text plus prompt version, schema version, and model name** — otherwise prompt/model changes can silently reuse stale decompositions.

### 4.4 `embed.py` — text → vectors

Two functions:

- `embed_facts(list[str]) -> np.ndarray` — for individual events/claims.
- `embed_article_from_clusters(article_id, coverage_matrix, cluster_vectors) -> np.ndarray` — article-level vector, computed as the **mean of unique canonical fact-cluster vectors** the article covers.

Compute article vectors after clustering, not before. This avoids letting repeated extracted facts skew centrality. Batch API calls. Cache embeddings on disk keyed by normalized text plus embedding model/provider/version.

### 4.5 `cluster.py` — semantic fact deduplication

Takes all facts from all *k* articles and clusters them by cosine similarity. Default implementation: agglomerative clustering with cosine distance and **average linkage** using either a cosine similarity threshold $\tau_{sim}=0.85$ or the equivalent cosine distance threshold $\tau_{dist}=0.15$. Single-link/connected-components can be enabled for recall, but average linkage is safer because it reduces accidental chaining. Returns a `FactUniverse` object holding:

- canonical facts (cluster medoids or concise generated labels),
- cluster vectors,
- cluster assignments,
- a `coverage_matrix` of shape `(k, n_facts)` where `[i, j] = 1` if article *i* covers fact *j*.

### 4.6 `score.py` — the four scoring components

Pure-numpy functions. Each returns both a raw vector and a normalized vector of length *k*:

- `centrality(article_embeddings)` — L2-normalize article embeddings and return normalized $-\|\hat e_i - \mu\|$.
- `coverage(coverage_matrix, mode="consensus")` — weighted recall against the fact universe. Supports `consensus` and `rarity` modes.
- `density(structured_articles, coverage_matrix)` — unique facts ÷ total extracted fact entries per article.
- `entity_coverage(structured_articles)` — same logic as `coverage` but on entities; diagnostic by default, optionally folded in.

A `combine(components, weights)` function does the final weighted sum. Scores are relative to one event corpus; do not compare raw final scores across unrelated events without calibration.

### 4.7 `pipeline.py` — public API

One class, `NewsRanker`, with three public methods:

```python
ranker = NewsRanker(config=...)
ranking = ranker.rank(articles, profile="representative")
selection = ranker.select(articles, m=5, profile="representative")
comparison = ranker.compare_profiles(articles)
```

Orchestrates: **decompose → embed facts → cluster → build article vectors → score → combine → sort/select**. Returns ranked lists plus optional diagnostics (per-component scores, fact universe, cluster sizes, rare-facts report, profile comparisons).

### 4.8 `config.py` — knobs in one place

Default values for: similarity threshold $\tau_{sim}$, optional distance threshold $\tau_{dist}=1-\tau_{sim}$, linkage mode, weighting mode (`consensus` vs `rarity`), final weights (α, β, γ, δ), scoring profiles, `top_m`, diversity/selection mode, embedding model name, LLM model name, prompt/schema versions, and cache directory. Validate that profile weights are non-negative and sum to 1, and that `top_m` satisfies $1 \leq M \leq k$ at call time.

### 4.9 `select.py` — best-*M* selection

Functions for turning article-level scores into a selected reading set:

- `select_top_score(ranking, m)` — first *M* articles by score.
- `select_mmr(scores, normalized_article_embeddings, m, lambda_)` — quality/diversity trade-off using maximal marginal relevance.

### 4.10 `evaluate.py` — comparison helpers

Utilities for comparing profiles and preparing user-study materials:

- top-*M* overlap,
- Kendall/Spearman rank correlation,
- component-score tables,
- cluster-inspection export,
- anonymized user-study bundles.

---

<a id="pipeline-workflow"></a>

## 5. Pipeline Workflow

```
┌─────────────────────────┐        ┌─────────────────────────┐
│ Input 1: k articles     │        │ Input 2: k decomposed   │
│ article.txt file        │        │ articles (JSON)         │
└───────────┬─────────────┘        │ StructuredDocs          │
            │                      └───────────┬─────────────┘
            ▼                                  │
┌─────────────────────────┐                    │
│ 1. DECOMPOSE            │                    │
│ LLM → StructuredDocs    │                    │
│ cache by text+versions  │                    │
└───────────┬─────────────┘                    │
            │                                  │
            ▼                                  ▼
        ┌─────────────────────────────────────────┐
        │ 2. EMBED FACTS                          │
        │ event/claim vec                         │
        └────────────────────┬────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────┐
        │ 3. CLUSTER                              │
        │ facts → universe                        │
        │ cluster vectors                         │
        │ coverage matrix                         │
        └────────────────────┬────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────┐
        │ 4. ARTICLE VECS                         │
        │ mean unique                             │
        │ cluster vectors                         │
        └────────────────────┬────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────┐
        │ 5. SCORE                                │
        │ centrality/coverage                     │
        │ density/entities                        │
        │ normalize [0, 1]                        │
        └────────────────────┬────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────┐
        │ 6. RANK / SELECT                        │
        │ weighted score                          │
        │ optional MMR top-M                      │
        └────────────────────┬────────────────────┘
                             │
                             ▼
        ┌─────────────────────────────────────────┐
        │ 7. RETURN                               │
        │ ranking + selected                      │
        │ diagnostics/compare                     │
        └─────────────────────────────────────────┘
```

### Step descriptions

1. **Decompose.** Each article goes through the LLM with the decomposition prompt. Output: a validated `StructuredArticle`. Cached by article text plus prompt/schema/model versions.
2. **Embed facts + extract entities.** Embed every individual event/claim from every article. Extract canonical entity sets from the structured docs.
3. **Cluster.** Run agglomerative clustering on all fact embeddings to produce the fact universe **F**, cluster vectors, and coverage matrix **C ∈ {0,1}^(k×n)**.
4. **Build article vectors.** Compute each article vector from the unique cluster vectors it covers, not from duplicate raw entries.
5. **Score.** Compute raw component scores, then min-max normalize each across the *k* articles.
6. **Rank / select.** Combine components into a final composite score. Sort all articles by score; optionally choose best *M* with a diversity-aware selector.
7. **Return.** Ranked list, selected list, rank/component breakdowns, diagnostics, and optional cross-profile comparison.

---

<a id="milestones"></a>

## 6. Implementation Order (Milestones)

| # | Milestone | Effort | Checkpoint |
|---|---|---|---|
| 1 | **Skeleton** — package layout, Pydantic schemas, system prompt | ½ day | All schemas import cleanly |
| 2 | **Decomposition end-to-end** — LLM call, JSON parsing, validation, retry | 1 day | `decompose(article)` returns valid `StructuredArticle` on 3–5 real articles |
| 3 | **Embedding + caching** — choose provider, batch fact calls, disk cache | ½ day | Fact embeddings are stable and cache keys include model/version |
| 4 | **Fact clustering** — agglomerative with cosine, threshold/linkage tuning | 1 day | Visual inspection of clusters on a 5-article test corpus looks right |
| 5 | **Scoring components** — all four functions with unit tests | 1 day | Synthetic-matrix tests pass (e.g. all-1s matrix → coverage = 1.0) |
| 6 | **Pipeline orchestration** — glue + verbose mode | ½ day | End-to-end run on a real corpus produces a ranked list |
| 7 | **Top-M selection + profiles** — MMR selector, representative/comprehensive/concise profiles | ½ day | `select(..., m)` returns non-duplicate top articles when diversity is enabled |
| 8 | **End-to-end evaluation** — real corpus, weight tuning, comparison export | 1 day | Sanity-check rankings by hand, tune α/β/γ/δ and profile weights |

**Total: ~6–7 working days for a clean v1.**

---

<a id="decision-formulas"></a>

## 7. Decision Formulas

This section contains all formulas in the order the pipeline computes them, with explanations and implementation guards for edge cases.

### Notation

| Symbol | Meaning |
|---|---|
| **k** | number of articles |
| **M** | number of articles to select, where $1 \leq M \leq k$ |
| **i ∈ {1, ..., k}** | article index |
| **F = {f₁, ..., fₙ}** | fact universe (canonical, deduplicated) |
| **Fᵢ ⊆ F** | facts covered by article *i* |
| **qⱼ ∈ ℝᵈ** | vector for canonical fact cluster *j* |
| **eᵢ ∈ ℝᵈ** | embedding of article *i* (mean of unique canonical fact-cluster vectors it covers) |
| **êᵢ ∈ ℝᵈ** | L2-normalized article embedding |
| **$\tau_{sim}$** | cosine similarity threshold for fact deduplication (default 0.85) |
| **$\tau_{dist}$** | cosine distance threshold, where $\tau_{dist}=1-\tau_{sim}$ (default 0.15) |
| **dfⱼ** | document frequency of fact *j*, i.e. number of articles covering it |
| **‖·‖** | Euclidean (L2) norm |
| **⟨·,·⟩** | dot product |
| **ε** | small numerical guard, e.g. $10^{-9}$ |

---

### 7.1 Step 1 — Fact Universe Construction

#### 7.1.1 Cosine similarity between two fact embeddings

$$
\text{sim}(f_a, f_b) = \frac{\langle v_a, v_b \rangle}{\lVert v_a \rVert \cdot \lVert v_b \rVert}
$$

where $v_a, v_b$ are the embeddings of facts $f_a$ and $f_b$.

> **Why:** Cosine similarity ignores vector magnitude and measures only directional alignment, which is the standard choice for embedding-space semantic similarity. Two paraphrases of the same fact should point in nearly the same direction even if their embeddings have different norms.

#### 7.1.2 Fact clustering (average-link agglomerative)

Define cosine distance:

$$
\text{dist}_{cos}(f_a, f_b) = 1 - \text{sim}(f_a, f_b)
$$

For two candidate clusters $A$ and $B$, define average-link distance:

$$
d_{avg}(A, B) = \frac{1}{|A||B|}\sum_{a \in A}\sum_{b \in B}\text{dist}_{cos}(f_a, f_b)
$$

Agglomerative clustering repeatedly merges the pair with the smallest $d_{avg}$ while:

$$
d_{avg}(A, B) \leq \tau_{dist}
$$

Equivalently, for singleton facts, the merge boundary is:

$$
\text{sim}(f_a, f_b) \geq \tau_{sim}, \quad \tau_{dist}=1-\tau_{sim}
$$

Each final cluster collapses to one canonical fact. Pick the canonical text as the medoid fact (fact closest to the cluster centroid) or a short generated label. The fact universe **F** is the set of canonical facts.

> **Why:** Different articles describe the same fact with different words ("300 protesters gathered" vs "hundreds rallied"). Clustering merges these so we count the underlying fact once. Average linkage is safer than single-link because it reduces transitive chaining, where A ≈ B and B ≈ C but A and C are actually different facts. The threshold is the main knob: too low merges distinct facts, too high over-counts the same fact as multiple.
>
> **Implementation note:** Choose either `similarity_threshold=0.85` or `distance_threshold=0.15` in code, not both as separate independent knobs. They represent the same boundary. Expose `linkage="single"` only as an optional high-recall mode.

#### 7.1.3 Coverage matrix

$$
C \in \{0, 1\}^{k \times n}, \quad C_{ij} = \begin{cases} 1 & \text{if article } i \text{ contains a fact in cluster } j \\ 0 & \text{otherwise} \end{cases}
$$

> **Why:** This is the central data structure for everything downstream. It compresses the question "which articles cover which facts" into a single binary matrix. Coverage, density, and consensus weighting are all simple operations on C.

---

### 7.2 Step 2 — Fact Importance Weights

This is a **policy choice**, not a detection mechanism. The frequency of a fact alone cannot distinguish a scoop from an outlier; the two weighting modes encode two different definitions of "important."

Let:

$$
df_j = \sum_{i=1}^{k} C_{ij}
$$

Since **F** is built from observed facts, normally $1 \leq df_j \leq k$ for every fact $j$.

#### 7.2.1 Consensus weighting (default — rewards covering the agreed story)

$$
w_j^{\text{cons}} = \frac{df_j}{k}
$$

> **Why:** Each fact is weighted by the fraction of articles that mention it. A fact in 9 of 10 articles has weight 0.9 — clearly central to the story. A fact in 1 of 10 has weight 0.1 — likely peripheral or unverified. This is the **conservative, robust choice**: it rewards articles that tell the agreed-upon story well and won't accidentally promote outliers or hallucinations.

<a id="rarity-weighting"></a>

#### 7.2.2 Rarity weighting (smoothed IDF style — rewards scoops)

$$
w_j^{\text{rare}} = \log\!\left(\frac{k+1}{df_j+1}\right) + 1
$$

> **Why:** This is a smoothed inverse-document-frequency style weight. A fact mentioned by only one article receives a higher weight, while a fact mentioned by every article still receives weight 1 instead of 0. That avoids the zero-denominator failure case where all facts are shared by all articles.
>
> **Caveat:** rarity weighting is risky because rarity ≠ correctness — a unique fact could be a scoop, a minor detail, or an error. Use this mode only when you have additional signals (source quality, attribution, semantic relatedness to the core story) to validate rare facts.

> **Recommended default:** consensus weighting. Switch to rarity only after evaluating on a labeled corpus.

---

### 7.3 Step 3 — The Four Scoring Components

All components are computed raw (denoted with $\tilde{\,\cdot\,}$), then normalized to [0, 1] across the *k* articles in [§7.4](#min-max-normalization).

#### 7.3.1 Centrality

Build each article embedding from unique canonical facts it covers:

$$
U_i = \sum_{j=1}^{n} C_{ij}
$$

$$
e_i = \begin{cases}
\frac{1}{U_i}\sum_{j=1}^{n} C_{ij} q_j & \text{if } U_i > 0 \\
\text{fallback\_embed}(i) & \text{if } U_i = 0
\end{cases}
$$

Then L2-normalize each article embedding:

$$
\hat{e}_i = \frac{e_i}{\max(\lVert e_i \rVert, \varepsilon)}
$$

Mean embedding (centroid):

$$
\mu = \frac{1}{k} \sum_{i=1}^{k} \hat{e}_i
$$

Centrality (raw):

$$
\tilde{c}_i = -\lVert \hat{e}_i - \mu \rVert
$$

> **Why unique canonical facts:** centrality should represent article content, not extraction duplicates. Averaging raw fact entries lets repetition pull the article vector toward repeated facts. Averaging cluster vectors counts each covered fact once.
>
> **Why the centroid:** the centroid is the average of all article representations. The article closest to it is the one whose content is closest to the consensus across all sources — the "most representative" article in pure embedding terms. This is the same idea as centroid-based extractive summarization in classical NLP.
>
> **Why L2-normalize first:** fact clustering uses cosine similarity, which is magnitude-invariant. Normalizing article embeddings before centrality keeps the geometry consistent: ranking is based on direction/content, not embedding magnitude. If the embedding provider already returns normalized vectors, this step is effectively a no-op.
>
> **Why the minus sign:** distances are positive; we want "more central" → "higher score." Negating distance flips the order so minimum distance becomes maximum centrality.
>
> **Why no PCA:** with *k* articles, centered embeddings span at most a (k−1)-dimensional subspace, so any PCA projection with d ≥ k−1 components leaves distances unchanged — it is a pure rotation. Truncating to d < k−1 changes the ranking by discarding information about dimensions where articles differ. Working in full embedding space is simpler and avoids an arbitrary hyperparameter.
>
> **Implementation guard:** if an article has no extracted facts, do not compute the mean of an empty list. Either fall back to an embedding of the neutral headline/body, or mark the article as invalid for scoring and return diagnostics. With $k=2$, centroid distance is tied by geometry, so centrality should be treated as non-discriminative and coverage/density should drive the ranking.

#### 7.3.2 Coverage (weighted recall against the fact universe)

$$
\tilde{\text{cov}}_i = \frac{\sum_{j=1}^{n} w_j \cdot C_{ij}}{\sum_{j=1}^{n} w_j}
$$

where $w_j$ is either $w_j^{\text{cons}}$ or $w_j^{\text{rare}}$ depending on the chosen mode.

> **Why:** This is **recall against the corpus**, weighted by fact importance. The numerator sums the importance of facts the article covers; the denominator is the total importance available. Result: the fraction of weighted corpus information the article has captured. Under consensus weighting, an article that covers all the high-consensus facts scores near 1.0 even if it misses some peripheral ones.
>
> **Implementation guard:** if $n=0$ or $\sum_j w_j \leq \varepsilon$, set coverage to 0 for all articles and raise a diagnostic warning. With normal observed facts and the smoothed rarity formula above, the denominator should be positive.

#### 7.3.3 Density (information per entry)

Let $E_i$ = number of events in article *i* and $L_i$ = number of claims in article *i*. Let $U_i$ = number of distinct fact clusters article *i* covers, i.e.

$$
U_i = \sum_{j=1}^{n} C_{ij}
$$

Then:

$$
\tilde{\text{dens}}_i = \begin{cases}
\frac{U_i}{E_i + L_i} & \text{if } E_i + L_i > 0 \\
0 & \text{if } E_i + L_i = 0
\end{cases}
$$

> **Why:** Coverage alone can be gamed by **long, repetitive articles** that mention many facts but say each one three times in different paragraphs. Density measures the ratio of *unique facts covered* to *total entries extracted*. An article with 30 entries but only 8 unique facts has density ≈ 0.27 (lots of repetition or padding). A tight article with 10 entries all unique has density 1.0. By construction $U_i \leq E_i + L_i$, so this is already in [0, 1] before normalization — but we still rescale across the corpus for consistency with the other components.

#### 7.3.4 Entity coverage (diagnostic / optional fourth term)

Let **G = {g₁, ..., gₘ}** be the union of all canonical entities across the *k* articles, and let **Gᵢ ⊆ G** be the entities mentioned in article *i*. Define the entity coverage matrix:

$$
D \in \{0, 1\}^{k \times m}, \quad D_{ij} = \begin{cases} 1 & \text{if article } i \text{ mentions entity } j \\ 0 & \text{otherwise} \end{cases}
$$

With consensus weighting on entities:

$$
w_j^{\text{ent}} = \frac{\sum_{i=1}^{k} D_{ij}}{k}
$$

$$
\tilde{\text{ent}}_i = \frac{\sum_{j=1}^{m} w_j^{\text{ent}} \cdot D_{ij}}{\sum_{j=1}^{m} w_j^{\text{ent}}}
$$

> **Why:** Same logic as fact coverage, but applied to actors (people, organizations, locations). An article that mentions all the relevant actors is usually more complete than one that omits half of them. Useful as both a **diagnostic signal** (does the article identify the people involved?) and an **optional fourth scoring term**. Kept separate from fact coverage because entities and facts are conceptually distinct: an article could list every entity but report nothing they did, or vice versa.
>
> **Implementation guard:** if $m=0$ or $\sum_j w_j^{ent} \leq \varepsilon$, set entity coverage to 0 and either keep $\delta=0$ or renormalize the remaining final weights. Do not reward an article for an entity signal that was never extracted.

---

<a id="min-max-normalization"></a>

### 7.4 Step 4 — Min-Max Normalization

For each meaningful component $x \in \{\tilde{c}, \widetilde{\text{cov}}, \widetilde{\text{dens}}, \widetilde{\text{ent}}\}$, compute:

$$
r_x = \max_j \tilde{x}_j - \min_j \tilde{x}_j
$$

Then normalize as:

$$
x_i = \begin{cases}
1 & \text{if } r_x < \varepsilon \text{ and the component is defined but tied} \\
0 & \text{if the component is undefined or empty} \\
\frac{\tilde{x}_i - \min_j \tilde{x}_j}{r_x} & \text{otherwise}
\end{cases}
$$

After this step: $c_i, \text{cov}_i, \text{dens}_i, \text{ent}_i \in [0, 1]$.

> **Why:** The four components live on different scales. Centrality is a negative distance (could be −0.3 to −1.2); coverage is a fraction in [0, 1]; density is also in [0, 1] but rarely uses the full range. Min-max normalization rescales each to [0, 1] across the k articles so the weighted sum is meaningful.
>
> **Why tied components become 1:** if all articles are identical or tied on a valid component, they are equally good on that component. Returning 1 preserves the sanity check that identical articles are maximally central and fully covered. Returning 0 should be reserved for missing or undefined components, such as no extracted entities. For density, pass `defined=False` when every article has `E_i + L_i = 0`; do not turn an all-empty extraction into perfect density.

Recommended implementation:

```python
def minmax_normalize(x, *, defined=True, eps=1e-9):
    if not defined:
        return np.zeros_like(x, dtype=float)

    lo = np.min(x)
    hi = np.max(x)
    if hi - lo < eps:
        return np.ones_like(x, dtype=float)

    return (x - lo) / (hi - lo)
```

---

### 7.5 Step 5 — Final Composite Score

$$
\text{score}(i) = \alpha \cdot c_i + \beta \cdot \text{cov}_i + \gamma \cdot \text{dens}_i + \delta \cdot \text{ent}_i
$$

with weights satisfying:

$$
\alpha + \beta + \gamma + \delta = 1, \quad \alpha, \beta, \gamma, \delta \geq 0
$$

**Recommended defaults** (entity coverage as diagnostic only):

$$
\alpha = 0.4, \quad \beta = 0.5, \quad \gamma = 0.1, \quad \delta = 0.0
$$

**Defaults if folding in entity coverage:**

$$
\alpha = 0.35, \quad \beta = 0.45, \quad \gamma = 0.1, \quad \delta = 0.1
$$

If a weighted component is undefined, either set its weight to 0 and renormalize the remaining weights, or explicitly set the component vector to 0 and keep the original weights. Renormalizing is usually preferable because it avoids lowering every article's final score because of a missing diagnostic signal.

> **Why these defaults:** Coverage (β) carries the most weight because it's the most direct signal of "this article tells you the most about what happened." Centrality (α) is a strong secondary signal — it captures *semantic* representativeness that coverage might miss when the LLM extraction is imperfect. Density (γ) is a small corrective term that mostly serves to demote padded articles; it shouldn't dominate. Entity coverage (δ) is set to 0 by default because in most cases entities are already captured by fact coverage; turn it on only when your corpus has articles that diverge specifically on which actors they cover.

---

### 7.6 Step 6 — Final Ranking and Best-*M* Selection

Full ranking:

$$
\text{rank}(i) = \text{position of } i \text{ in } \underset{i}{\operatorname{argsort\,desc}}(\text{score}(i))
$$

The article with the highest $\text{score}(i)$ is ranked 1 (best).

If `selection_mode="top_score"`, selected set $S$ is the first *M* articles in the ranking.

If `selection_mode="mmr"`, use maximal marginal relevance to trade off article quality and diversity:

$$
S_0 = \varnothing
$$

$$
i_t = \underset{i \notin S_{t-1}}{\operatorname{argmax}}\left[\lambda \cdot \text{score}(i) - (1-\lambda) \cdot \max_{s \in S_{t-1}} \max(0, \langle \hat e_i, \hat e_s \rangle)\right]
$$

$$
S_t = S_{t-1} \cup \{i_t\}, \quad t=1,\dots,M
$$

For $t=1$, the diversity penalty is 0, so the first selected article is the highest-scoring article. Recommended default: $\lambda=0.8$.

> **Why descending:** higher score = better article because each component is "higher = better" by construction.
>
> **Why MMR:** the top-ranked articles can be near duplicates from wire-service rewrites. MMR keeps score as the main objective while discouraging redundant selections. Clamping similarity at 0 avoids rewarding articles merely because their embeddings are negatively correlated.

---

### Summary Table

| Symbol | Meaning | Range | Direction |
|---|---|---|---|
| $c_i$ | Centrality | [0, 1] | higher = closer to centroid |
| $\text{cov}_i$ | Fact coverage | [0, 1] | higher = covers more weighted facts |
| $\text{dens}_i$ | Information density | [0, 1] | higher = less repetition |
| $\text{ent}_i$ | Entity coverage | [0, 1] | higher = mentions more key entities |
| $\text{score}(i)$ | Final composite | [0, 1] | higher = better article |
| $S$ | Selected top-*M* set | article ids | high score, optionally diverse |

---

<a id="public-api"></a>

## 8. Public API

```python
from news_ranker import NewsRanker, RankerConfig

config = RankerConfig(
    similarity_threshold=0.85,
    linkage="average",
    coverage_weighting="consensus",  # or "rarity"
    profiles={
        "representative": {
            "centrality": 0.4,
            "coverage": 0.5,
            "density": 0.1,
            "entity_coverage": 0.0,
        },
        "comprehensive": {
            "centrality": 0.2,
            "coverage": 0.7,
            "density": 0.1,
            "entity_coverage": 0.0,
        },
        "concise": {
            "centrality": 0.2,
            "coverage": 0.4,
            "density": 0.4,
            "entity_coverage": 0.0,
        },
    },
    selection_mode="mmr",
    selection_lambda=0.8,
)

ranker = NewsRanker(config)

articles = [
    {"id": "art1", "title": "...", "body": "..."},
    {"id": "art2", "title": "...", "body": "..."},
    # ...
]

results = ranker.rank(articles, profile="representative", return_diagnostics=True)
selected = ranker.select(articles, m=5, profile="representative")
comparison = ranker.compare_profiles(
    articles, profiles=["representative", "comprehensive", "concise"]
)

# results.ranking → [
#   {"id": "art3", "score": 0.87, "rank": 1, "components": {...}},
#   ...
# ]
# selected.selected → top-M article ids plus MMR/diversity diagnostics
# comparison.rankings → per-profile rankings
# results.fact_universe → list of canonical facts and their support
# results.coverage_matrix → numpy array (k × n_facts)
# results.rare_facts_report → rare facts with support sources
```

---

<a id="configuration-choices"></a>

## 9. Configuration Choices

A few decisions to make before coding:

- **Embedding provider.** Local `sentence-transformers/all-mpnet-base-v2` (free, fast, ~768 dim) vs. hosted (e.g. OpenAI `text-embedding-3-small`, better quality but costs money and adds latency). For Italian/English mixed corpora, `paraphrase-multilingual-mpnet-base-v2` is a strong local default.
- **LLM for decomposition.** Claude Haiku (fast, cheap) for prototyping; Claude Sonnet (higher quality structure) for production runs. Decomposition quality dominates downstream quality, so it's worth paying for the better model once.
- **Language.** If the corpus is monolingual, use a monolingual embedder. For mixed corpora, use a multilingual model.
- **Thresholds + linkage.** Use $\tau_{sim}=0.85$ for cosine similarity, equivalently $\tau_{dist}=0.15$ for cosine distance. Pick one representation in code and **tune by inspection** on a small dev corpus before committing. Default to average linkage; print clusters and eyeball false merges/splits.
- **Scoring profiles.** Ship at least three named profiles for comparison: `representative` (centrality + coverage), `comprehensive` (coverage-heavy), and `concise` (density-heavy). Keep `rarity` as an explicit experimental profile, not the default.
- **Top-M selection.** Use `top_score` when duplicates are acceptable. Use `mmr` with $\lambda \approx 0.8$ when selected articles should be both strong and non-redundant.

---

<a id="sanity-check-identities"></a>

## 10. Sanity-Check Identities

A few things to verify once the implementation is in place:

**Identity 1 — Identical articles.** If all articles are identical and extraction succeeds, all raw centrality values are tied at the centroid, all raw coverages are 1.0, and the ranking is degenerate. The tied-component normalization rule should return 1.0 for each meaningful component, not 0 and not NaN.

**Identity 2 — Full coverage.** With consensus weighting, an article that covers every fact in F gets $\text{cov}_i = 1.0$ regardless of how the weights are distributed.

**Identity 3 — Smoothed rarity safety.** With smoothed rarity weighting, facts covered by all articles still receive positive weight, so the coverage denominator remains valid even when every article covers the same fact universe.

**Identity 4 — Reduction to original idea.** If you set α = 1 and β = γ = δ = 0, the ranking reduces to the original "most centered article wins" idea.

**Identity 5 — Density bound.** $U_i \leq E_i + L_i$ always holds when $E_i + L_i > 0$, so raw density is already in [0, 1] before normalization. If $E_i + L_i = 0$, density should be set to 0 and flagged diagnostically.

**Identity 6 — Top-M equivalence.** With `selection_mode="top_score"`, `select(m)` must equal the first *M* ids from `rank()`.

**Identity 7 — MMR first pick.** With MMR, the first selected article must be the highest-scoring article because the diversity penalty is zero for an empty set.

---

<a id="evaluation-comparison-plan"></a>

## 11. Evaluation & Comparison Plan

To match the project brief, evaluate more than one definition of "best":

1. **Run multiple profiles.** At minimum compare `representative`, `comprehensive`, and `concise`; optionally include a `rarity` profile and an MMR-selected diverse set.
2. **Report ranking differences.** Compute top-*M* overlap, Kendall/Spearman rank correlation, and per-component score distributions.
3. **Inspect fact clusters.** Sample clusters with high support and rare clusters. Count obvious false merges and false splits.
4. **Minimal user study.** Ask 5–10 readers which selected set they prefer for each event. Show article titles/snippets or summaries, randomize order, and collect preference plus short reason.
5. **Decision output.** Document which profile best matches the chosen product goal: representative single article, comprehensive reading list, concise summary source, or diverse source set.

---

*End of design document.*
