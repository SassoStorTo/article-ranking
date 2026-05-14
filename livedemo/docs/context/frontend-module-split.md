# Frontend Module Split Context

## Scope

Document final frontend module boundaries after splitting the live demo SPA out of
`frontend/src/main.tsx`. This context supports follow-up work that needs to find
route ownership, page composition, forms, artifacts, or shared UI without
re-reading the full refactor history.

## Current Structure

- `frontend/src/main.tsx` is a 15-line bootstrapper. It imports global styles,
  `App`, and the shared TanStack Query client, then renders the provider tree.
- `frontend/src/app/App.tsx` owns URL-backed route state, theme state, selected
  corpus/article/execution IDs, top-level corpus query, legacy `/articles`
  redirects, nested corpus/article URL validation, comparison route composition,
  and page composition. It does not contain form internals, artifact renderers,
  execution polling, or page-specific markup beyond workspace shells.
- `frontend/src/app/navigation.ts` owns route/page types, URL normalization,
  route equality, route-to-path mapping, path decoding, nested
  `/corpora/:corpusId/article/:articleId` paths, durable
  `/executions/compare/:leftExecutionId?/:rightExecutionId?` paths, and legacy
  `/articles` path parsing for redirects.
- `frontend/src/forms/` owns execution parameter drafts, normalization, replay
  prefill, validation warnings, locked execution parameter form UI, and shared
  Ranking Parameters/Metadata sections rendered by rank, select, and compare
  forms.
- `frontend/src/artifacts/` owns evaluation controls, artifact cards, ranking
  tables, article-material generation, selected-article helpers, result payload
  rendering, and reusable comparison result tables.
- `frontend/src/components/` owns reusable UI such as top navigation,
  corpus/article lists, article body rendering, execution controls, metrics, and
  empty workspace state.
- `frontend/src/pages/` owns route/workspace-level screens: home, corpus create,
  executions index, execution comparison, corpus workspace, and execution detail.
  Article upload, inspection, decomposition, and deletion live in `CorpusPanel`;
  there is no separate top-level Articles page.
- `frontend/src/utils/` owns shared formatting and payload guard helpers.

## Boundary Notes

- Route state remains centralized in `App`; child modules receive callbacks and
  selected IDs through props.
- No router library or frontend test harness was added.
- CSS remains centralized in `frontend/src/styles.css`.
- Execution replay and evaluation wiring now cross page/form/artifact boundaries:
  `CorpusPanel` passes config drafts into `ParameterForm`, while
  `ExecutionPanel` composes `ResultPayloadTable` and `EvaluationPanel`.
- Execution comparison wiring crosses page/artifact/API boundaries:
  `ExecutionsIndex` navigates to `ExecutionComparisonPage`, which loads the
  read-only comparison response and renders `ComparisonResultTables`.

## Verification

Final split verification should run:

```bash
cd livedemo/frontend && npm run build && cd ../.. && make check
```
