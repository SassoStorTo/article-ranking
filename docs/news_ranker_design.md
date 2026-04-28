# News Article Ranking Library — Design Document

> A scoring library that takes *k* articles about the same news event and ranks them from most to least representative, using structured fact decomposition, embedding centrality, and information coverage.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Scope & Assumptions](#2-scope--assumptions)
3. [Library Layout](#3-library-layout)
4. [Module-by-Module Plan](#4-module-by-module-plan)
5. [Pipeline Workflow](#5-pipeline-workflow)
6. [Implementation Order (Milestones)](#6-implementation-order-milestones)
7. [Decision Formulas](#7-decision-formulas)
8. [Public API](#8-public-api)
9. [Configuration Choices](#9-configuration-choices)
10. [Sanity-Check Identities](#10-sanity-check-identities)

---

## 1. Overview

The system takes a set of *k* news articles covering the same event and produces a ranking from best (most representative and complete) to worst. The core insight is to **strip authorial style by converting each article into a structured "what happened" document** before embedding, so similarity reflects *content*, not *prose style*.

The ranking combines four signals:

- **Centrality** — how close the article's content is to the consensus centroid in embedding space.
- **Coverage** — what fraction of the corpus's unique facts the article contains.
- **Density** — how much unique information per entry the article carries (penalizes padding).
- **Entity coverage** — whether the article mentions all the key actors (optional / diagnostic).

---

## 2. Scope & Assumptions

**Input contract.** A list of *k* articles, each a dict with at minimum `{"id": str, "title": str, "body": str}`. Optionally `{"source": str, "published_at": str}`.

**Output contract.** A ranked list of `{"id": str, "score": float, "components": {...}, "rank": int}`, sorted descending by score.

**Out of scope (for v1):**
- Article scraping or URL deduplication.
- Multilingual handling beyond what the embedder natively supports.
- External fact-checking against ground-truth sources.
- Detecting scoops vs. errors among rare facts (see [§7.2.2](#722-rarity-weighting-smoothed-idf-style--rewards-scoops)).

**Stack:**
- Python 3.11+
- `pydantic` — schema validation
- `anthropic` — decomposition LLM
- `sentence-transformers` *or* OpenAI embeddings API
- `numpy` + `scikit-learn` — PCA, clustering, distances
- `pytest` — tests

---

## 3. Library Layout

```
news_ranker/
├── __init__.py
├── schemas.py          # Pydantic models for the structured doc
├── decompose.py        # LLM call → structured JSON
├── embed.py            # Text → vectors
├── cluster.py          # Semantic fact deduplication
├── score.py            # Centrality, coverage, density, entity coverage
├── pipeline.py         # Orchestrator (the public API)
├── config.py           # Thresholds, weights, model names
└── prompts.py          # The decomposition system prompt
tests/
└── ...
```

---

## 4. Module-by-Module Plan

### 4.1 `schemas.py` — the structured document

Pydantic models matching the JSON schema used for decomposition: `Entity`, `Event`, `Claim`, `StructuredArticle`. Strict validation so a malformed LLM response fails fast and can be retried.

```python
class Event(BaseModel):
    id: str
    when: str | None
    who: list[str]
    what: str
    where: str | None
    why: str | None
    how: str | None
    depends_on: list[str] = []

class Claim(BaseModel):
    id: str
    statement: str
    type: Literal["fact", "quote", "estimate", "prediction"]
    attributed_to: str | None

class StructuredArticle(BaseModel):
    article_id: str
    headline_neutral: str
    topic: str
    entities: Entities
    events: list[Event]
    claims: list[Claim]
    context: list[str]
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

A single function `decompose(article) -> StructuredArticle`. Calls the LLM with the system prompt + article body, parses JSON, validates against the schema. Includes one retry on validation failure with the error message fed back to the model. **Caches results on disk keyed by hash of the article body** — decomposition is the slowest and most expensive step.

### 4.4 `embed.py` — text → vectors

Two functions:

- `embed_facts(list[str]) -> np.ndarray` — for individual events/claims.
- `embed_article(StructuredArticle) -> np.ndarray` — article-level vector, computed as the **mean of its fact embeddings** (the "fact-only, style-stripped" representation).

Batches API calls. Caches embeddings on disk.

### 4.5 `cluster.py` — semantic fact deduplication

Takes all facts from all *k* articles and clusters them by cosine similarity. Implementation: single-link agglomerative clustering using either a cosine similarity threshold $\tau_{sim}=0.85$ or the equivalent cosine distance threshold $\tau_{dist}=0.15$. Returns a `FactUniverse` object holding:

- the canonical facts,
- the cluster assignments,
- a `coverage_matrix` of shape `(k, n_facts)` where `[i, j] = 1` if article *i* covers fact *j*.

### 4.6 `score.py` — the four scoring components

Pure-numpy functions, each returning a vector of length *k* normalized to [0, 1]:

- `centrality(article_embeddings)` — L2-normalize article embeddings, center them, return normalized $-\|\hat e_i - \mu\|$.
- `coverage(coverage_matrix, mode="consensus")` — weighted recall against the fact universe. Supports `consensus` and `rarity` modes.
- `density(structured_articles, coverage_matrix)` — unique facts ÷ total entries per article.
- `entity_coverage(structured_articles)` — same logic as `coverage` but on entities; diagnostic by default, optionally folded in.

A `combine(components, weights)` function does the final weighted sum.

### 4.7 `pipeline.py` — public API

One class, `NewsRanker`, with one main method:

```python
ranker = NewsRanker(config=...)
results = ranker.rank(articles)
```

Orchestrates: **decompose → embed → cluster → score → combine → sort**. Returns the ranked list plus optional diagnostics (per-component scores, fact universe, cluster sizes, rare-facts report).

### 4.8 `config.py` — knobs in one place

Default values for: similarity threshold $\tau_{sim}$, optional distance threshold $\tau_{dist}=1-\tau_{sim}$, weighting mode (`consensus` vs `rarity`), final weights (α, β, γ, δ), embedding model name, LLM model name, cache directory.

---

## 5. Pipeline Workflow

```
                    ┌─────────────────────────┐
                    │  Input: k articles      │
                    │  [{id, title, body}]    │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  1. DECOMPOSE           │
                    │  for each article:      │
                    │    LLM → StructuredDoc  │
                    │    (cached by hash)     │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┼────────────────────┐
            │                   │                    │
  ┌─────────▼────────┐ ┌────────▼─────────┐ ┌────────▼────────┐
  │  2a. EMBED       │ │  2b. EMBED       │ │  2c. EXTRACT    │
  │  each fact       │ │  each article    │ │  entity sets    │
  │  individually    │ │  (mean of facts) │ │  per article    │
  └─────────┬────────┘ └────────┬─────────┘ └────────┬────────┘
            │                   │                    │
  ┌─────────▼────────┐          │                    │
  │  3. CLUSTER      │          │                    │
  │  facts → fact    │          │                    │
  │  universe F      │          │                    │
  │  build coverage  │          │                    │
  │  matrix (k × n)  │          │                    │
  └─────────┬────────┘          │                    │
            │                   │                    │
            └─────────┬─────────┴────────────────────┘
                      │
            ┌─────────▼──────────┐
            │  4. SCORE          │
            │  - centrality      │ ← article embeddings (centroid distance)
            │  - coverage        │ ← coverage matrix + weights
            │  - density         │ ← entries vs unique facts
            │  - entity_coverage │ ← entity sets
            │  normalize each    │
            │  to [0, 1]         │
            └─────────┬──────────┘
                      │
            ┌─────────▼──────────┐
            │  5. COMBINE        │
            │  α·c + β·cov +     │
            │  γ·dens (+ δ·ent)  │
            └─────────┬──────────┘
                      │
            ┌─────────▼──────────┐
            │  6. SORT & RETURN  │
            │  ranked list +     │
            │  diagnostics       │
            └────────────────────┘
```

### Step descriptions

1. **Decompose.** Each article goes through the LLM with the decomposition prompt. Output: a validated `StructuredArticle`. Cached by article-body hash.
2. **Embed (parallel).**
   - **2a.** Embed every individual fact (event/claim) from every article.
   - **2b.** Compute each article's vector as the mean of its fact embeddings.
   - **2c.** Extract the entity set per article (no embedding needed; canonical names from step 1).
3. **Cluster.** Run agglomerative clustering on all fact embeddings to produce the fact universe **F** and the coverage matrix **C ∈ {0,1}^(k×n)**.
4. **Score.** Compute the four raw component scores, then min-max normalize each across the *k* articles.
5. **Combine.** Weighted sum into a final composite score.
6. **Sort & return.** Descending by score, with rank and per-component breakdown.

---

## 6. Implementation Order (Milestones)

| # | Milestone | Effort | Checkpoint |
|---|---|---|---|
| 1 | **Skeleton** — package layout, Pydantic schemas, system prompt | ½ day | All schemas import cleanly |
| 2 | **Decomposition end-to-end** — LLM call, JSON parsing, validation, retry | 1 day | `decompose(article)` returns valid `StructuredArticle` on 3–5 real articles |
| 3 | **Embedding + caching** — choose provider, batch calls, disk cache | ½ day | `embed_article(...)` returns stable vectors |
| 4 | **Fact clustering** — agglomerative with cosine, threshold tuning | 1 day | Visual inspection of clusters on a 5-article test corpus looks right |
| 5 | **Scoring components** — all four functions with unit tests | 1 day | Synthetic-matrix tests pass (e.g. all-1s matrix → coverage = 1.0) |
| 6 | **Pipeline orchestration** — glue + verbose mode | ½ day | End-to-end run on a real corpus produces a ranked list |
| 7 | **End-to-end test** — real corpus, weight tuning | 1 day | Sanity-check rankings by hand, tune α/β/γ |

**Total: ~5–6 working days for a clean v1.**

---

## 7. Decision Formulas

This section contains all formulas in the order the pipeline computes them, with explanations and implementation guards for edge cases.

### Notation

| Symbol | Meaning |
|---|---|
| **k** | number of articles |
| **i ∈ {1, ..., k}** | article index |
| **F = {f₁, ..., fₙ}** | fact universe (canonical, deduplicated) |
| **Fᵢ ⊆ F** | facts covered by article *i* |
| **eᵢ ∈ ℝᵈ** | embedding of article *i* (mean of fact embeddings) |
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

#### 7.1.2 Fact clustering (single-link via connected components)

Create an edge between two facts when either of the equivalent conditions holds:

$$
\text{sim}(f_a, f_b) \geq \tau_{sim}
$$

or:

$$
\text{dist}_{cos}(f_a, f_b) = 1 - \text{sim}(f_a, f_b) \leq \tau_{dist}
$$

Each connected component under those edges becomes one fact cluster. Each cluster collapses to one canonical fact. The fact universe **F** is the set of canonical facts.

> **Why:** Different articles describe the same fact with different words ("300 protesters gathered" vs "hundreds rallied"). Clustering merges these so we count the underlying fact once. Single-link clustering chains paraphrases together: if A ≈ B and B ≈ C, then A, B, C land in the same cluster even if A and C have lower direct similarity. The threshold is the main knob: too low merges distinct facts, too high over-counts the same fact as multiple.
>
> **Implementation note:** Choose either `similarity_threshold=0.85` or `distance_threshold=0.15` in code, not both as separate independent knobs. They represent the same boundary.

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

All components are computed raw (denoted with $\tilde{\,\cdot\,}$), then normalized to [0, 1] across the *k* articles in [§7.4](#74-step-4--min-max-normalization).

#### 7.3.1 Centrality

First L2-normalize each article embedding:

$$
\hat{e}_i = \frac{e_i}{\lVert e_i \rVert}
$$

Mean embedding (centroid):

$$
\mu = \frac{1}{k} \sum_{i=1}^{k} \hat{e}_i
$$

Centrality (raw):

$$
\tilde{c}_i = -\lVert \hat{e}_i - \mu \rVert
$$

> **Why the centroid:** the centroid is the average of all article representations. The article closest to it is the one whose content is closest to the consensus across all sources — the "most representative" article in pure embedding terms. This is the same idea as centroid-based extractive summarization in classical NLP.
>
> **Why L2-normalize first:** fact clustering uses cosine similarity, which is magnitude-invariant. Normalizing article embeddings before centrality keeps the geometry consistent: the ranking is based on direction/content, not embedding magnitude. If the embedding provider already returns normalized vectors, this step is effectively a no-op.
>
> **Why the minus sign:** distances are positive; we want "more central" → "higher score." Negating distance flips the order so that minimum distance becomes maximum centrality.
>
> **Why no PCA:** with *k* articles, the centered embeddings span at most a (k−1)-dimensional subspace, so any PCA projection with d ≥ k−1 components leaves distances unchanged — it's a pure rotation. Truncating to d < k−1 would change the ranking, but only by *discarding information* about dimensions where articles genuinely differ. There's no principled reason those discarded dimensions are "noise" rather than meaningful sub-topic variation. Working in the full embedding space is simpler and avoids an arbitrary hyperparameter.
>
> **Implementation guard:** if an article has no extracted facts, do not compute the mean of an empty list. Either fall back to an embedding of the neutral headline/body, or mark the article as invalid for scoring and return diagnostics.

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
> **Why tied components become 1:** if all articles are identical or tied on a valid component, they are equally good on that component. Returning 1 preserves the sanity check that identical articles are maximally central and fully covered. Returning 0 should be reserved for missing or undefined components, such as no extracted entities.

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

### 7.6 Step 6 — Final Ranking

$$
\text{rank}(i) = \text{position of } i \text{ in } \underset{i}{\operatorname{argsort\,desc}}(\text{score}(i))
$$

The article with the highest $\text{score}(i)$ is ranked 1 (best).

> **Why descending:** higher score = better article (since each component is "higher = better" by construction).

---

### Summary Table

| Symbol | Meaning | Range | Direction |
|---|---|---|---|
| $c_i$ | Centrality | [0, 1] | higher = closer to centroid |
| $\text{cov}_i$ | Fact coverage | [0, 1] | higher = covers more weighted facts |
| $\text{dens}_i$ | Information density | [0, 1] | higher = less repetition |
| $\text{ent}_i$ | Entity coverage | [0, 1] | higher = mentions more key entities |
| $\text{score}(i)$ | Final composite | [0, 1] | higher = better article |

---

## 8. Public API

```python
from news_ranker import NewsRanker, RankerConfig

config = RankerConfig(
    similarity_threshold=0.85,
    coverage_weighting="consensus", # or "rarity"
    weights={
        "centrality": 0.4,
        "coverage": 0.5,
        "density": 0.1,
        "entity_coverage": 0.0,
    },
)

ranker = NewsRanker(config)

articles = [
    {"id": "art1", "title": "...", "body": "..."},
    {"id": "art2", "title": "...", "body": "..."},
    # ...
]

results = ranker.rank(articles, return_diagnostics=True)

# results.ranking → [
#   {"id": "art3", "score": 0.87, "rank": 1, "components": {...}},
#   ...
# ]
# results.fact_universe → list of canonical facts and their support
# results.coverage_matrix → numpy array (k × n_facts)
# results.rare_facts_report → facts in only 1–2 articles, with relatedness scores
```

---

## 9. Configuration Choices

A few decisions to make before coding:

- **Embedding provider.** Local `sentence-transformers/all-mpnet-base-v2` (free, fast, ~768 dim) vs. hosted (e.g. OpenAI `text-embedding-3-small`, better quality but costs money and adds latency). For Italian/English mixed corpora, `paraphrase-multilingual-mpnet-base-v2` is a strong local default.
- **LLM for decomposition.** Claude Haiku (fast, cheap) for prototyping; Claude Sonnet (higher quality structure) for production runs. Decomposition quality dominates downstream quality, so it's worth paying for the better model once.
- **Language.** If the corpus is monolingual, use a monolingual embedder. For mixed corpora, use a multilingual model.
- **Thresholds.** Use $\tau_{sim}=0.85$ for cosine similarity, equivalently $\tau_{dist}=0.15$ for cosine distance. Pick one representation in code and **tune by inspection** on a small dev corpus before committing. Print clusters and eyeball.

---

## 10. Sanity-Check Identities

A few things to verify once the implementation is in place:

**Identity 1 — Identical articles.** If all articles are identical and extraction succeeds, all raw centrality values are tied at the centroid, all raw coverages are 1.0, and the ranking is degenerate. The tied-component normalization rule should return 1.0 for each meaningful component, not 0 and not NaN.

**Identity 2 — Full coverage.** With consensus weighting, an article that covers every fact in F gets $\text{cov}_i = 1.0$ regardless of how the weights are distributed.

**Identity 3 — Smoothed rarity safety.** With smoothed rarity weighting, facts covered by all articles still receive positive weight, so the coverage denominator remains valid even when every article covers the same fact universe.

**Identity 4 — Reduction to original idea.** If you set α = 1 and β = γ = δ = 0, the ranking reduces to the original "most centered article wins" idea.

**Identity 5 — Density bound.** $U_i \leq E_i + L_i$ always holds when $E_i + L_i > 0$, so raw density is already in [0, 1] before normalization. If $E_i + L_i = 0$, density should be set to 0 and flagged diagnostically.

---

*End of design document.*
