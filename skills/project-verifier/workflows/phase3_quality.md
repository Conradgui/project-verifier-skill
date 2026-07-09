# Phase 3: Offline Behavior Tests

## Purpose

Verify approved paths and boundaries without real network calls, credentials, or production side effects.

## Planning Gate

Load `phase2_flow_matrix.md`. For each proposed test, record its oracle provenance:

- source contract or type/interface;
- existing test;
- user-confirmed behavior;
- cited external specification.

Unknown expectations remain unknown. Before writing, show the exact files, existing commands to reuse, CI choice, dependency commands, and allowed paths. CI is optional and must match the repository's existing platform.

## Rules

- Prefer existing tests and project scripts.
- Block real network access and use fake credentials, fixtures, and isolated output paths.
- Do not modify production code to make a test pass. A source fix requires a separate plan and authorization.
- Do not install dependencies automatically.
- VCR-style recording that requires a real first call is not Phase 3 work.
- A completed suite with failing tests has `phase_status: completed` and `result_outcome: fail`; preserve failures.

## Procedure

1. Create `project_verification_workbench/phase3_test_plan.md` mapping every test to path ID, oracle, files, command, and expected evidence.
2. After approval, create tests for normal behavior, boundaries, errors, state transitions, and permitted side effects.
3. Write a deterministic runner only when the project lacks one. Never hide failures with `|| true` or equivalent behavior.
4. Execute only approved local commands. Capture command, exit code, duration, pass/fail counts, log paths, generated artifacts, and untested paths.
5. Compare changed files with the approved write scope. If production files changed, stop and report the violation.

## Output

Write `project_verification_workbench/phase3_test_results.md`. Keep pass rate distinct from code coverage; report coverage only when a coverage tool actually produced it.

Update the manifest and ask whether to revise tests, proceed to conditional Phase 4, or stop.
