# Run Rank Section Placement Plan

## Goal

Fix `/corpora/:id` execution forms so `Ranking Parameters` and `Metadata` appear consistently for all three execution actions. Done means `Run Rank`, `Run Select`, and `Compare Profiles` each show their mode-specific controls plus the same shared `Ranking Parameters` section and read-only `Metadata` section, with all submitted payloads preserving current API shapes.

## Non-goals

- No backend API, request payload, or database changes.
- No new frontend dependencies or router/test harness.
- No changes to execution replay endpoint semantics.
- No changes to execution detail parameter display or persisted `config_json`.
- No redesign of corpus workspace navigation, article upload, or evaluation UI.
- No global corpus-level settings panel outside the existing execution forms.

## Approach

Treat issue as inconsistent shared configuration placement, not as need to hide the sections. Current `RankParameterForm` already renders `Ranking Parameters` and `Metadata`; select and compare lack the equivalent shared sections, making rank look like the only configurable action. Extract those repeated fieldsets into reusable form sections and render them in all three locked forms.

Keep mode-specific controls intact: rank still has one profile and profile weights; select still has selection defaults/top M/selection controls plus profile weights; compare still has profile checkboxes plus selected profile weights. Shared `Ranking Parameters` should own config keys common to ranker behavior: `similarity_threshold`, `linkage`, and `coverage_weighting`. Selection-specific keys (`selection_mode`, `selection_lambda`, `top_m`) stay in select’s `Selection` fieldset to avoid duplicated controls, but rank can keep submitting normalized/default selection values as before. `Metadata` stays read-only for every mode.

Reject adding a new corpus-level advanced configuration panel because it would create a second source of form state and exceed issue scope. Also reject copying the rank JSX into select/compare because duplicated controls increase drift risk; reusable section components keep labels/options consistent. Tradeoff: compare profiles will now expose clustering/coverage knobs even if users previously only saw profile weights, but those values already affect ranking internals and are part of the persisted config.

## Steps

1. **Extract shared form sections**
   - **Files touched**: `livedemo/frontend/src/forms/ParameterForm.tsx`
   - **Change summary**: Move rank’s `Ranking Parameters` fieldset into a reusable component that edits `similarity_threshold`, `linkage`, and `coverage_weighting`. Move rank’s read-only metadata fieldset into a reusable `MetadataSection` component for `llm_model_name`, `prompt_version`, `schema_version`, and `embedding_model_name`.
   - **Tests added or updated**: None — livedemo has no frontend test harness; TypeScript build verifies component props and config key types.
   - **Verification command**: `cd livedemo/frontend && npm run build`

2. **Render shared sections in Run Rank without changing behavior**
   - **Files touched**: `livedemo/frontend/src/forms/ParameterForm.tsx`
   - **Change summary**: Replace inline rank `Ranking Parameters` and `Metadata` JSX with the reusable components. Preserve existing rank submit behavior, including normalized config, selected profile, profile weights, and current `top_m` handling if still present.
   - **Tests added or updated**: None — frontend build verifies no behavior-breaking refactor at type level.
   - **Verification command**: `cd livedemo/frontend && npm run build`

3. **Add shared sections to Run Select**
   - **Files touched**: `livedemo/frontend/src/forms/ParameterForm.tsx`
   - **Change summary**: Render shared `Ranking Parameters` and read-only `Metadata` in `SelectParameterForm`, reusing the select form’s existing `config`/`setConfig` state. Keep the existing `Selection` fieldset as the only place for `selection_mode`, `selection_lambda`, `top_m`, and default-selection preset controls.
   - **Tests added or updated**: None — no frontend test harness exists; backend execution tests still validate select payload acceptance.
   - **Verification command**: `cd livedemo/frontend && npm run build && cd ../.. && uv run --project livedemo pytest livedemo/tests/test_executions.py`

4. **Add shared sections to Compare Profiles**
   - **Files touched**: `livedemo/frontend/src/forms/ParameterForm.tsx`
   - **Change summary**: Render shared `Ranking Parameters` and read-only `Metadata` in `CompareProfilesParameterForm`, reusing compare form `config`/`setConfig` state. Keep profile checkboxes and selected profile weights unchanged.
   - **Tests added or updated**: None — no frontend test harness exists; backend execution tests still validate compare payload acceptance.
   - **Verification command**: `cd livedemo/frontend && npm run build && cd ../.. && uv run --project livedemo pytest livedemo/tests/test_executions.py`

5. **Smoke corpus action-form consistency**
   - **Files touched**: `livedemo/frontend/src/pages/CorpusPanel.tsx`, `livedemo/frontend/src/components/ExecutionControls.tsx`, `livedemo/frontend/src/forms/ParameterForm.tsx`, `livedemo/frontend/src/styles.css`
   - **Change summary**: Review `/corpora/:id` form ordering and layout for all three buttons. Make only minimal CSS/copy adjustments if repeated sections crowd forms or stale copy implies rank-only settings; leave routing and button behavior unchanged.
   - **Tests added or updated**: None — no frontend test harness exists; build plus manual browser smoke verifies form rendering.
   - **Verification command**: `cd livedemo/frontend && npm run build`

6. **Final verification**
   - **Files touched**: No production files expected beyond previous steps.
   - **Change summary**: Run full project checks after frontend-only change to catch formatting, type, backend, and parent-package regressions.
   - **Tests added or updated**: None expected; this step runs existing suites.
   - **Verification command**: `make check`

7. **Sync livedemo context artifacts if implementation changes behavior notes**
   - **Files touched**: `livedemo/docs/context/execution-specific-forms.md`, `livedemo/docs/context/parameter-form-replay.md`, `livedemo/docs/context/frontend-module-split.md`
   - **Change summary**: Check `livedemo/docs/context` after implementation and update stale statements about select/compare lacking shared `Ranking Parameters` or `Metadata`, rank-only section placement, or parameter form ownership. If no context is stale, leave files unchanged.
   - **Tests added or updated**: None — context docs need no tests.
   - **Verification command**: `git diff -- livedemo/docs/context && cd livedemo/frontend && npm run build && cd ../.. && make check`

## Risks

1. Select form may appear to have duplicated selection-related controls if shared ranking section accidentally includes `selection_mode`, `selection_lambda`, or `top_m`; keep those only in `Selection`.
2. Compare profile form grows taller, which may affect corpus workspace layout on small screens.
3. Shared section extraction can accidentally change rank behavior if initial config updates or `top_m` handling are not preserved.
4. Replay drafts may include old config values; all shared sections must initialize from `normalizeConfigDraft()` so replay remains faithful.
5. No frontend tests means regressions in conditional form rendering rely on TypeScript build and manual smoke.

## Open questions

None. Implement shared `Ranking Parameters` and `Metadata` sections in all three execution forms.
