# Locked Execution Rank Parameters Context

## Scope

Restore the missing controls on the Article Sets -> Run Rank -> Locked
Execution form without undoing the newer mode-specific form split.

## Current Behavior

- `frontend/src/main.tsx` renders three locked forms:
  `RankParameterForm`, `SelectParameterForm`, and
  `CompareProfilesParameterForm`.
- The current locked Rank form only exposes profile selection and profile
  weights, then submits `runRankExecution()` with the full normalized
  `RankerConfigPayload`.
- `normalizeConfigDraft()` and `frontend/src/api/client.ts` still carry default
  values for similarity threshold, linkage, coverage weighting, selection
  mode, selection lambda, top M, and metadata.
- The older `feat/livedemo-scoring-library` branch exposed these controls in a
  shared parameter form. Metadata values were displayed as read-only inputs.

## Constraints

- Preserve locked execution forms; do not reintroduce the execution-kind
  switcher removed by `execution-specific-forms`.
- Keep API payload shapes unchanged.
- The Rank form should keep submitting the same effective config object, with
  `top_m` synchronized when the Top M input changes.
- Metadata should be visible but read-only: LLM model name, prompt version,
  schema version, and embedding model name.
