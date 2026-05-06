# Execution Specific Forms Plan

## Goal

Replace the shared switchable execution parameter form on the Articles Sets page
with locked rank, select, and compare profile forms that show only mode-relevant
parameters.

## Steps

1. Add task context and plan artifacts for the Articles Sets form split.
2. Refactor `ParameterForm` so the opened `draft.mode` selects a locked form and
   the execution kind switch is removed.
3. Narrow the rank form to one selected profile and its Profile Weights section.
4. Narrow the select form to profile, M, selection behavior, and a defaults
   dropdown that reloads default selection values.
5. Narrow the compare profile form to profile selection and weights for selected
   profiles only.
6. Run frontend/backend checks, inspect the diff, and update this plan if the
   implementation needs to diverge.

## Verification

- Run `npm run build` from `frontend/`.
- Run `uv run python -m pytest tests` from `livedemo/`.
- Run `make check` from the parent repository root before final handoff.
