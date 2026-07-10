# Task 1 Brief: V3 Contract Test Harness

## Objective

Create a standard-library V3 test entrypoint and a machine-checked historical-test migration ledger. End GREEN without changing current V2 CI consumers.

## Owned Files

- `skills/project-verifier/tests/__init__.py`
- `skills/project-verifier/tests/helpers.py`
- `skills/project-verifier/tests/test_contract.py`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution/task-01-report.md`

## Required Behavior

1. Write `test_contract.py` before `helpers.py`; capture a RED import failure.
2. Implement `read`, `write_json`, `load_module`, and `run` helpers using only the Python standard library.
3. Enumerate every `test_*` function from the four historical executable workbench suites with Python AST.
4. Matrix schema is `1.0`, `retired_contract_allowlist` is empty, and every legacy ID appears exactly once.
5. Allowed statuses are `pending`, `ported`, `covered_by`, and `retired_contract`.
6. `ported/covered_by` must reference an existing V3 test function. `retired_contract` is rejected unless allowlisted. Only `pending` may omit `v3_test` before Task 7.
7. End with the full current V3 suite GREEN and all four historical CI Python commands passing.

## Forbidden Actions

- Do not modify `.github/workflows/offline-validation.yml`.
- Do not modify `README.md`, `SKILL.md`, workflows, templates, validators, runners, fixtures, or historical workbench test files.
- Do not install dependencies, use network access, commit, push, merge, or update the installed Skill.
- Do not stage files; the controller owns Git state.

## Required Report

Write `task-01-report.md` with:

- status: `DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED`
- files changed
- RED command, exit code, and failure reason
- GREEN commands, exit codes, and exact test counts
- migration matrix legacy row count
- self-review and concerns

The complete implementation requirements remain Task 1 in `IMPLEMENTATION_PLAN.md`; this brief is the task-local binding summary.
