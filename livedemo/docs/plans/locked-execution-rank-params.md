# Locked Execution Rank Parameters Plan

## Goal

Bring back the missing Article Sets -> Run Rank -> Locked Execution parameters
from `feat/livedemo-scoring-library` in a way that fits the newer
mode-specific form architecture.

## Steps

1. Add the Similarity control to the locked Rank form and keep it wired to
   `similarity_threshold`.
2. Add the Linkage control and keep it wired to `linkage`.
3. Add the Coverage control and keep it wired to `coverage_weighting`.
4. Add the Selection mode control and keep it wired to `selection_mode`.
5. Add the Selection lambda control and keep it wired to `selection_lambda`.
6. Add the Top M control and keep it synchronized with `config.top_m` for rank
   executions and replay drafts.
7. Add read-only Metadata fields for LLM model name, prompt version, schema
   version, and embedding model name.

## Verification

- Run frontend type/build checks through the repository check target.
- Run `make check` before declaring the work complete.
