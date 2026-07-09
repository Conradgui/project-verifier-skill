# Phase 1: Scoped Exploration and Static Risk Review

## Purpose

Build a source-backed understanding of the approved code scope. This is a static review, not penetration testing, compliance certification, or proof of complete repository coverage.

## Gate

Before reading, confirm:

- user goal, target users, and success criteria;
- in-scope and out-of-scope areas;
- risk tolerance and allowed workbench write scope.

Initialize `verification_manifest.json`, capture `source_revision`, and set Phase 1 to `in_progress`. Record environment variable names only; never read or display actual secret values.

## Procedure

1. Inspect configs, entry points, core modules, tests, CI, docs, and example environment files.
2. For repositories over 80 files, publish the reading plan first. Prioritize entry points, shared state, side-effectful code, security boundaries, and existing tests.
3. Maintain a coverage ledger: reviewed files, excluded generated/vendor paths, sampled areas, unreviewed areas, and reasons.
4. Classify each relevant feature as `AI`, `AI-assisted`, `non-AI`, or `unknown`, with source evidence.
5. Trace user-visible entry points through modules, external dependencies, state changes, outputs, and common failures.
6. Review:
   - secret handling and logging;
   - input, path, shell, SQL, URL, and file-write boundaries;
   - permissions and destructive operations;
   - external-call timeouts, retries, token/cost limits, and empty responses;
   - error handling, state consistency, shared modules, and maintainability;
   - existing tests without confusing pass rate with code coverage.

Mark unknowns as `unknown`; do not complete them by inference. Report critical risks immediately.

## Output

Create or update `project_verification_workbench/project_report.md` with:

- goal, scope, project summary, entry points, feature classification;
- coverage ledger and limitations;
- risk table with source locations, impact, evidence, and suggested action;
- external dependencies and required environment variable names;
- candidate P0/P1/P2 paths for Phase 2;
- proceed, revise, or stop recommendation.

Update the manifest with artifacts, blockers, recovery conditions, `phase_status`, `result_outcome`, `execution_scope`, and `claim_eligibility`.

Ask the user to confirm factual corrections, risk priority, coverage limitations, and whether to continue.
