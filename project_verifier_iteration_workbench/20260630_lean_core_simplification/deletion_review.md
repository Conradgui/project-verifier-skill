# Deletion Review

| Candidate | Decision | Reason |
|---|---|---|
| Browser recording, conversion, and replay design | Remove | Unimplemented and outside the lean verification core. Existing project-owned browser E2E scripts remain runnable. |
| Multi-host Guarded/Isolated platform plan | Remove | Unimplemented platform expansion. Replace only the Codex need with a separate minimal hook. |
| Revision-bound gate validator | Keep | Implemented and tested against stale plans, revisions, limits, and invalidation. |
| Usability and benchmark preflight runners | Keep | Implemented no-call preflight and authorization boundaries. |
| Execution telemetry and inconclusive fallback | Keep | Prevents missing evidence from becoming a positive claim. |
| Four-dimensional phase state | Keep | Separates workflow progress, observed result, execution scope, and claim scope. |
| Task-defined raw metric evaluator | Keep | Prevents fixed metrics and unsupported default scores. |
| Normalized scores and radar | Remove | Optional but still introduces incomparable-unit and visual overclaim risk. |
| Six offline fixtures and existing tests | Keep | They provide regression evidence without adding user-facing complexity. |
| Multi-file interview pack | Replace | A single optional evidence pack reduces duplication while retaining traceability. |
