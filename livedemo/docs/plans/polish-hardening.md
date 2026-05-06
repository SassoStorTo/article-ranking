# Polish Hardening Plan

## Goal

Implement only Milestone 9 from `docs/brief.md`: harden local readiness,
deterministic behavior, serializer drift detection, frontend loading/empty/error
states, and handoff documentation.

## Steps

1. Add deterministic execution coverage and exact serializer payload snapshot
   assertions using existing fake embedder/decomposer fixtures.
2. Extend health checks to report cheap readiness details for DB connectivity,
   executor availability, embedder cache readiness, and Mistral configuration
   without loading models or calling external services.
3. Improve API/client-facing error clarity where current messages are too raw,
   especially validation detail parsing and readiness failures.
4. Add frontend loading, empty, disabled, and error states to the major existing
   surfaces: corpus detail, article/result panels, executions index, compare
   modal, and evaluation baseline controls.
5. Rewrite the README as an operations and troubleshooting guide for setup,
   env vars, common failures, DB reset, test commands, and development workflow.
6. Run focused backend tests and frontend build, then run `make check` from the
   parent repository and inspect the final diff.

## Commit Plan

1. `test(livedemo): add deterministic and serializer snapshot tests`
2. `feat(api): improve health checks and error handling`
3. `feat(frontend): polish loading and empty states`
4. `docs(livedemo): document operations and troubleshooting`
5. `chore(livedemo): run final lint test and cleanup`
