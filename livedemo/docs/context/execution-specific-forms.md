# Execution Specific Forms Context

## Scope

The Articles Sets page opens locked execution parameter forms from the Run Rank,
Run Select, and Compare Profiles buttons. Each form keeps mode-specific controls
while sharing the same ranking parameter and metadata sections.

## Current Behavior

- `frontend/src/pages/CorpusPanel.tsx` owns corpus workspace state, including
  execution draft selection and result polling.
- `frontend/src/components/ExecutionControls.tsx` owns the Run Rank, Run Select,
  and Compare Profiles buttons; each button opens a draft with a fixed mode.
- `frontend/src/forms/ParameterForm.tsx` dispatches to locked rank, select, or
  compare form components from `draft.mode`; users cannot switch execution type
  after a form opens.
- Rank exposes a selected profile, profile weights, shared `Ranking Parameters`,
  and read-only `Metadata`.
- Select exposes selection defaults, Top M, selection mode/lambda, a selected
  profile with weights, shared `Ranking Parameters`, and read-only `Metadata`.
- Compare Profiles exposes profile checkboxes, weights for selected profiles,
  shared `Ranking Parameters`, and read-only `Metadata`.
- New runs and replay drafts use the same `ParameterDraft` shape, so locked forms
  still honor stored mode/profile/config values from replay.

## Constraints

- The three Article Sets buttons must open three different forms, and the user
  must not be able to change the execution type after a form opens.
- Rank should expose only ranking controls: selected profile, profile weights,
  shared ranking parameters, and read-only metadata.
- Select should expose selection inputs and default selection loading, plus the
  same shared ranking parameters and read-only metadata.
- Compare Profiles should expose the profile set and profile weights needed for
  profile comparison, plus the same shared ranking parameters and read-only
  metadata.
- API payload shapes remain unchanged; the frontend can keep submitting effective
  `RankerConfigPayload` objects through the existing client helpers.
