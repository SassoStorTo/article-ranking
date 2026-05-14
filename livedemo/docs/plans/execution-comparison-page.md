# Execution Comparison Page Plan

## Goal

Add durable livedemo execution comparison view. From `/executions`, user clicks Compare on any succeeded rank/select/compare_profiles execution, lands on a deep-linkable comparison page, selects or arrives with two execution ids, then sees metadata, effective parameters, result tables, profile-expanded compare_profiles outputs, and non-mutating summary metrics side by side. Refresh keeps selected ids.

## Non-goals

- No changes to `news_ranker` ranking, selection, decomposition, or evaluation semantics.
- No new frontend router library, test framework, or dependencies.
- No artifact persistence as automatic side effect of opening comparison page.
- No scraping, URL dedupe, external fact-checking, auth, or multi-user behavior.
- No DB schema or migration changes.
- No removal of existing execution detail evaluation panel or replay flow.

## Approach

Add backend comparison read model instead of making page assemble every metric ad hoc from raw execution details. New non-mutating API will load two executions, normalize each execution into comparable result sections, expand `compare_profiles` into one section per profile, expose metadata/config JSON, and compute metrics per compatible section pair. Route shape should avoid conflict with `GET /api/executions/{id}`: `GET /api/executions/comparison?left_execution_id=...&right_execution_id=...`.

Section pairing: rank/select has one section; compare_profiles has N profile sections. compare_profiles vs compare_profiles pairs same profile names and reports unmatched profiles as unavailable sections. rank/select vs compare_profiles pairs single run against every profile section. Metrics include top-M overlap/shared count, rank correlation when common article ids allow it, cluster row count per side from diagnostics fact universe, and shared canonical cluster-text count. Incompatible or missing result shapes return warning objects, not server 500s.

Frontend adds URL route under existing URL state, not new router dependency. Use `/executions/compare`, `/executions/compare/:leftExecutionId`, and `/executions/compare/:leftExecutionId/:rightExecutionId`. Page owns two execution selectors and fetches comparison only when both ids exist. Existing `/executions` row Compare action should navigate to comparison page with left id prefilled; comparison page selects second id. Compare actions must allow `compare_profiles`, not hide it.

Rejected: reusing old compare modal as final UI because it is not durable/deep-linkable and only persists evaluation artifacts. Rejected query-string-only route because current navigation parses pathnames only; path segments keep implementation smaller. Rejected page-only metric computation because tests would be limited to build checks and duplication of payload parsing would grow in React components.

## Steps

1. **Backend comparison read model and API**
   - **Files touched**: `livedemo/app/schemas.py`, `livedemo/app/routers/executions.py`, `livedemo/app/services/execution_comparison.py`, `livedemo/tests/test_execution_comparison.py`
   - **Change summary**: Add Pydantic response models for comparison metadata, normalized result sections, section-pair metrics, and warnings. Add `GET /api/executions/comparison` before `/{execution_id}` route; implement service that loads two executions, expands rank/select/compare_profiles results, computes top-M overlap, rank correlation when possible, cluster row counts, and shared cluster counts without persisting artifacts.
   - **Tests added or updated**: `livedemo/tests/test_execution_comparison.py` asserts rank-vs-select comparison returns two metadata blocks, configs, result sections, top-M overlap, rank correlation, and cluster metrics; compare_profiles-vs-compare_profiles expands all profiles; rank/select-vs-compare_profiles pairs single section against each profile; missing/incompatible/unfinished executions return clear 404/422 or warning payloads, not 500.
   - **Verification command**: `cd livedemo && uv run python -m pytest tests/test_execution_comparison.py`

2. **Frontend API types and deep-link route support**
   - **Files touched**: `livedemo/frontend/src/api/client.ts`, `livedemo/frontend/src/app/navigation.ts`, `livedemo/frontend/src/app/App.tsx`
   - **Change summary**: Add TypeScript types and `getExecutionComparison()` client for comparison response. Extend route parsing/path generation for `/executions/compare`, `/executions/compare/:leftExecutionId`, and `/executions/compare/:leftExecutionId/:rightExecutionId`; keep top-nav selected state mapped to Executions.
   - **Tests added or updated**: No frontend test harness exists; validation is TypeScript build. Existing backend tests unaffected.
   - **Verification command**: `cd livedemo/frontend && npm run build`

3. **Comparison page UI**
   - **Files touched**: `livedemo/frontend/src/pages/ExecutionComparisonPage.tsx`, `livedemo/frontend/src/artifacts/ComparisonResultTables.tsx`, `livedemo/frontend/src/styles.css`, `livedemo/frontend/src/app/App.tsx`
   - **Change summary**: Add comparison page with two execution selectors, loading/error/empty states, side-by-side metadata cards, corpus/kind/status/profiles/timestamps/config JSON, metric summary cards, and side-by-side result tables for each section pair. Render compare_profiles as separate profile sections and show warnings for unmatched or incompatible sections.
   - **Tests added or updated**: No frontend test harness exists; build asserts types/JSX. Manual acceptance target: page renders with left-only URL, both-id URL, missing id, incompatible sections, and compare_profiles payload.
   - **Verification command**: `cd livedemo/frontend && npm run build`

4. **Wire `/executions` Compare action to page flow**
   - **Files touched**: `livedemo/frontend/src/pages/ExecutionsIndex.tsx`, `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/styles.css`
   - **Change summary**: Replace artifact-running compare modal entry point with navigation to `/executions/compare/:leftExecutionId`. Enable Compare for succeeded rank, select, and compare_profiles executions; page handles second-id selection and deep-link completion.
   - **Tests added or updated**: No frontend test harness exists; build verifies types. Existing backend compare-artifact tests remain for evaluation endpoints but no longer define page navigation behavior.
   - **Verification command**: `cd livedemo/frontend && npm run build`

5. **Full regression and context artifact update check**
   - **Files touched**: `livedemo/docs/context/executions-index-cross-compare.md`, `livedemo/docs/context/execution-result-serialization.md`, `livedemo/docs/context/frontend-module-split.md`, and/or new `livedemo/docs/context/execution-comparison-page.md` if current context docs need updates
   - **Change summary**: Check `livedemo/docs/context` after implementation and update content if plan edits changed route ownership, API contracts, compare_profiles rendering, or comparison metrics. Keep context focused on final behavior and relevant files.
   - **Tests added or updated**: No tests for docs. This step confirms docs match implementation and runs full livedemo/parent checks.
   - **Verification command**: `cd livedemo && uv run python -m pytest tests && cd frontend && npm run build && cd ../.. && make check && git diff --check`

## Risks

1. New `/api/executions/comparison` route could be shadowed by `/{execution_id}` if declared after dynamic route.
2. Rank correlation can be unavailable for executions with fewer than two common article ids; response must show reason instead of failing whole page.
3. compare_profiles payloads can contain profile sets that do not match; UI must show unmatched profiles clearly.
4. Cluster shared-count based on canonical fact text may be approximate across different corpora/runs; acceptable as inspectable summary, not formal evaluation artifact.
5. Large diagnostics payloads can make comparison response heavy; current demo data volume is small, but tables should avoid expensive repeated transforms in render.
6. Existing evaluation artifact tests around old compare modal should not be weakened; only frontend entry flow changes.

## Open questions

- None before implementation.
