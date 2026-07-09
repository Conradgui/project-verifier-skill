# Stage Gate Audit Matrix

| Area | Baseline risk at `b0fa305` | V2 acceptance criterion |
|---|---|---|
| Approval | Prose-only approval can survive plan or source changes. | Receipt binds decision ID, plan hash, source revision, limits, and invalidation state. |
| State | Lifecycle, test outcome, pilot scope, and claims are conflated. | Four independent state fields are required and validated. |
| Phase 1 | "Full repo" and "security audit" can overstate review coverage. | Coverage ledger and static-review boundary are mandatory. |
| Phase 2 | Scope approval has no freshness or evidence binding. | Approved path register links source evidence and plan hash. |
| Phase 3 | Agent may infer test oracles or modify production code. | Oracle provenance and production-code prohibition are explicit hard gates. |
| Phase 4 | Runner can write `execution_authorization: true` without proof. | Runner validates a receipt before execution and records actual telemetry. |
| Phase 5 | Fixed metrics and default 0-10 views imply false comparability. | Task-defined raw metrics are primary; auxiliary scores and radar are opt-in. |
| Phase 6 | Prompt assumes a loose-script-to-modular evolution. | History claims require Git or workbench evidence and a claim approval gate. |
| README | Static tests may be mistaken for Agent behavior validation. | Evidence levels and unverified behavior boundaries are explicit. |
| Skill eval | Six prompts have no fixture inputs or old/new comparison. | Six local fixtures exist; comparison package uses `b0fa305` as baseline and waits for cost approval. |
