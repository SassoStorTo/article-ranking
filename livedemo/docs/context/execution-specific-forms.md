# Execution Specific Forms Context

## Scope

The Articles Sets page currently opens one shared execution parameter form from
the Run Rank, Run Select, and Compare Profiles buttons. This change narrows that
experience to three locked, mode-specific forms.

## Current Behavior

- `frontend/src/main.tsx` owns the compact React SPA, including
  `ExecutionControls`, `ParameterForm`, execution replay prefill, and result
  polling.
- `ParameterForm` stores `mode` in local state and renders a segmented control
  that lets users switch among rank, select, and compare after the form opens.
- The form shows every configurable section for every mode: profile/profile
  checkboxes, all profile weights, similarity/linkage/coverage controls,
  selection controls, top M, and read-only metadata.
- New runs and replay drafts use the same `ParameterDraft` shape, so a locked
  form still needs to honor stored mode/profile/config values from replay.

## Constraints

- The three Article Sets buttons must open three different forms, and the user
  must not be able to change the execution type after a form opens.
- Rank should expose only the controls needed for ranking, with a single Profile
  Weights section for the selected profile.
- Select should expose only selection inputs and include a dropdown that can load
  default selection values.
- Compare Profiles should expose only the profile set and profile weights needed
  for profile comparison.
- API payload shapes remain unchanged; the frontend can keep submitting effective
  `RankerConfigPayload` objects through the existing client helpers.
