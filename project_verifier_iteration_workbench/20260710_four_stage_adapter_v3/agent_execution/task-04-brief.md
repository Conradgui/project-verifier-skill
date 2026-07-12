# Task 4 Brief: Stage 2 Quality and Authorized Live E2E

## Objective

Replace the split V2 quality/usability journey with one V3 Stage 2 workflow.
It must keep offline quality and project-native commands distinct from an
explicitly authorized Smoke/live E2E runner. Stage 2 is not a security scan and
does not modify production code to make tests pass.

## Owned Files

- `skills/project-verifier/templates/run_quality_template.sh`
- `skills/project-verifier/workflows/stage2_quality.md`
- `skills/project-verifier/tests/test_quality_runner.py`
- `skills/project-verifier/tests/test_contract.py`
- `skills/project-verifier/evals/fixtures/stale_authorization/stage2_live_execution.json`
- `skills/project-verifier/evals/fixtures/stale_authorization/stage2_quality_plan.md`
- `skills/project-verifier/evals/fixtures/stale_authorization/verification_manifest_v3.json`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution/task-04-report.md`

## Required Behavior

1. Runner invocation is `bash run_quality_template.sh preflight|run`; no
   argument prints help and never executes a project path.
2. `preflight` validates only names, scripts, files, commands, runtimes, task
   bounds, and the confirmed Stage 1 Profile handoff. It must not execute path
   scripts, network calls, or production changes.
3. `run` requires the V3 `stage2/live_e2e` decision-envelope authorization,
   complete limits, current source, and confirmed Profile. It validates before
   any script dispatch.
4. Retain `.py`, `.sh`, and `.ts` dispatch behavior. Record script exit code,
   duration, actual calls/retries/side effects, log path, and telemetry source.
   Missing telemetry becomes `inconclusive`; partial paths yield completed /
   partial, not a false overall pass.
5. Offline lint/build/unit/integration work uses project-native commands and
   fixture/mock oracles. The runner only handles approved Smoke/live paths.
6. Do not install dependencies, execute real APIs, read secrets, write
   production source, change V2 consumers, or generate a coverage claim from a
   pass rate.
7. Use a single selected-quality-scope user gate. Ask again only for production
   fixes, installations, live calls, sensitive data, or changed side effects.
8. Add targeted RED-to-GREEN tests and update the migration matrix only for
   historical assertions actually covered.

## Required Report

Write `task-04-report.md` with status; changed files; RED/GREEN commands and
counts; authorization/Profile behavior; fixture migration; self-review;
limitations; and blockers. Do not stage, commit, push, or modify files outside
the owned list.
