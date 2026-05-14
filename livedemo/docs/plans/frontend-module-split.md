# Frontend Module Split Plan

## Goal

Refactor livedemo frontend so `livedemo/frontend/src/main.tsx` becomes a tiny React entrypoint that imports app root, mounts providers, and renders `<App />`. User-visible behavior, URLs, execution/replay/evaluation flows, theme switching, and API calls remain unchanged while code moves into clear `app/`, `components/`, `pages/`, `forms/`, `artifacts/`, and `utils/` modules.

## Non-goals

- No backend API changes.
- No new frontend dependencies or router library.
- No visual redesign beyond import-boundary-safe CSS class reuse.
- No route/query-string behavior changes.
- No changes to ranking, replay, evaluation, decomposition, or persistence semantics.
- No frontend test framework setup.
- No changes to parent `news_ranker` package.

## Approach

Use behavior-preserving extraction. First move current SPA implementation from `main.tsx` into an app module and leave `main.tsx` as the bootstrapper. Then split pure helpers, form-heavy execution controls, artifact/result renderers, reusable components, and page/workspace modules. Each step should compile after import updates and keep runtime behavior unchanged.

Keep CSS centralized in `src/styles.css` for this refactor. Moving styles with components would create more churn and risk visual regressions without improving acceptance criteria. Keep TanStack Query provider setup outside app component or in a tiny provider module so `main.tsx` remains small but explicit.

Rejected adding React Router or a test framework. Existing URL-backed navigation already uses History API helpers and issue forbids new dependencies. Frontend has no tests today; verification relies on strict TypeScript plus Vite build. If future frontend tests appear, extracted pure helpers (`utils/format.ts`, `app/navigation.ts`) become easy unit-test targets.

## Steps

1. **Extract app root from entrypoint**
   - **Files touched**: `livedemo/frontend/src/main.tsx`, `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/app/queryClient.ts`
   - **Change summary**: Move current `App` implementation and supporting local functions from `main.tsx` into `app/App.tsx`. Move `new QueryClient()` into `app/queryClient.ts`; keep `main.tsx` limited to React/ReactDOM imports, CSS import, provider setup, and `<App />` render.
   - **Tests added or updated**: None — no frontend test harness exists; TypeScript build asserts module graph and JSX types.
   - **Verification command**: `cd livedemo/frontend && npm run build`

2. **Extract navigation and display helpers**
   - **Files touched**: `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/app/navigation.ts`, `livedemo/frontend/src/utils/format.ts`, `livedemo/frontend/src/utils/payload.ts`
   - **Change summary**: Move `AppPage`, `AppRoute`, `routeForPage`, `pathForRoute`, `routeForPathname`, `routeEquals`, path normalization, and route param decoding into `app/navigation.ts`. Move formatting/date helpers into `utils/format.ts`; move generic payload guards like `isRecord` and `arrayPayload` into `utils/payload.ts`.
   - **Tests added or updated**: None — no frontend test harness exists; strict TS verifies helper exports/imports.
   - **Verification command**: `cd livedemo/frontend && npm run build`

3. **Extract execution parameter forms**
   - **Files touched**: `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/forms/ParameterForm.tsx`, `livedemo/frontend/src/forms/configDraft.ts`
   - **Change summary**: Move `ParameterDraft`, `ParameterForm`, mode-specific rank/select/compare forms, profile weight controls, validation warning helpers, and draft normalization into `forms/`. Export `draftFromExecution()` so execution replay still pre-fills locked mode-specific forms without changing payloads.
   - **Tests added or updated**: None — no frontend test harness exists; build verifies props, mutation payload types, and config helper types.
   - **Verification command**: `cd livedemo/frontend && npm run build`

4. **Extract artifacts and ranking result renderers**
   - **Files touched**: `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/artifacts/EvaluationPanel.tsx`, `livedemo/frontend/src/artifacts/ArtifactCard.tsx`, `livedemo/frontend/src/artifacts/ResultPayloadTable.tsx`, `livedemo/frontend/src/components/Metric.tsx`
   - **Change summary**: Move evaluation controls, artifact cards/payload renderers, result payload table, ranking table, selected article id helper, and article-material generation into `artifacts/`. Move shared `Metric` into `components/` and reuse from home, compare modal, and artifact views.
   - **Tests added or updated**: None — no frontend test harness exists; build verifies artifact payload union handling and component props.
   - **Verification command**: `cd livedemo/frontend && npm run build`

5. **Extract reusable UI and page-level modules**
   - **Files touched**: `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/components/TopNavigation.tsx`, `livedemo/frontend/src/components/CorpusList.tsx`, `livedemo/frontend/src/components/ArticleList.tsx`, `livedemo/frontend/src/components/ArticleBody.tsx`, `livedemo/frontend/src/components/EmptyWorkspace.tsx`, `livedemo/frontend/src/pages/HomePage.tsx`, `livedemo/frontend/src/pages/NewCorpusPage.tsx`, `livedemo/frontend/src/pages/ArticleManagementPage.tsx`, `livedemo/frontend/src/pages/ExecutionsIndex.tsx`
   - **Change summary**: Move top nav, corpus/article lists, article inspector/structured panel, empty state, home page, new corpus page, article management page, executions index, and compare modal out of app root. Keep all existing props callback-driven so navigation state stays owned by `App`.
   - **Tests added or updated**: None — no frontend test harness exists; build verifies page/component props and API client imports.
   - **Verification command**: `cd livedemo/frontend && npm run build`

6. **Extract corpus and execution workspace modules, then prune app root**
   - **Files touched**: `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/pages/CorpusPanel.tsx`, `livedemo/frontend/src/pages/ExecutionPanel.tsx`, `livedemo/frontend/src/components/ExecutionControls.tsx`
   - **Change summary**: Move corpus workspace, run buttons, execution detail/polling panel, replay hook-up, and evaluation panel composition out of `App`. Leave `App.tsx` focused on route state, selected IDs, top-level queries, and page composition; ensure `main.tsx` remains tiny.
   - **Tests added or updated**: None — no frontend test harness exists; build verifies final split and replay/evaluation prop wiring.
   - **Verification command**: `cd livedemo/frontend && npm run build`

7. **Final verification and docs/context sync**
   - **Files touched**: `livedemo/frontend/src/main.tsx`, `livedemo/frontend/src/app/App.tsx`, `livedemo/docs/context/frontend-module-split.md`, `livedemo/docs/context/frontend-ux-polish.md` if current-behavior notes need updating
   - **Change summary**: Inspect final `main.tsx` size and module boundaries against issue acceptance criteria. Check `livedemo/docs/context` files and create/update focused context notes if implementation changed current frontend structure or invalidated existing context claims.
   - **Tests added or updated**: None expected; if implementation adds any frontend test harness later, document exact test files here before work starts.
   - **Verification command**: `cd livedemo/frontend && npm run build && cd ../.. && make check`

## Risks

1. Large import-only refactor can create circular dependencies between pages, forms, artifacts, and shared components.
2. Callback wiring mistakes can break URL-backed navigation, selected corpus/article/execution state, or replay after extraction.
3. Moving helpers may change function identity/import paths and trigger unnecessary rerenders if callbacks are not kept stable.
4. No frontend test harness means behavior regressions may only appear in manual browser smoke checks despite TypeScript build passing.
5. `main.tsx` can become tiny while `App.tsx` remains too large unless final extraction/pruning step is enforced.
6. Existing context docs mention single-file frontend; docs must be updated after implementation to avoid stale guidance.

## Open questions

None. Use local modules and existing dependencies only.
