# Stage Gate Quality V2 Plan

Base commit: `b0fa305`

## Goals

1. Replace prompt-only approvals with revision-bound, machine-checkable gate receipts.
2. Separate phase lifecycle, result outcome, execution scope, and claim eligibility.
3. Make live runners fail closed when authorization or telemetry is missing.
4. Make benchmark reports raw-metric-first and task-defined.
5. Remove prompts that invite unsupported test or interview narratives.
6. Add realistic local fixtures and prepare, but do not run, model-backed comparison evals.

## Verification Table

| Step | Verification |
|---|---|
| Control-plane schema and gate validator | Invalid, stale, or mismatched receipts are rejected by tests. |
| Phase 4 runner | `run` cannot start without a valid receipt; result JSON records decision and telemetry. |
| Benchmark evaluator | Dynamic raw metrics work without auxiliary scores; optional scores require explicit approval. |
| Workflow contracts | Each phase states entry evidence, user decision ownership, exit state, and invalidation behavior. |
| Fixtures | Six fixture projects cover non-AI, blocked AI, local AI, mixed AI-assisted, stale approval, and partial E2E. |
| Documentation | README distinguishes static contract tests, fixture tests, and unexecuted agent behavior evals. |
| Regression | Existing tests, V2 tests, shell syntax, Python compilation, skill validation, and diff checks pass. |

## Constraints

- Do not call a real API or model.
- Do not install dependencies.
- Do not read or write secret values.
- Do not update the installed skill copy.
- Do not merge or push without separate authorization.
