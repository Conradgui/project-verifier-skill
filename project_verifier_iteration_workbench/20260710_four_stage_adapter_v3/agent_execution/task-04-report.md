# Task 4 Report: Stage 2 Quality and Authorized Live E2E

## Status

DONE. Task 4 adds the transitional V3 Stage 2 quality runner and workflow while
leaving the V2 usability runner, V2 workflows, README, CI, validator production
code, and production source unchanged.

## Changed Files

- `skills/project-verifier/templates/run_quality_template.sh`
- `skills/project-verifier/workflows/stage2_quality.md`
- `skills/project-verifier/tests/test_quality_runner.py`
- `skills/project-verifier/tests/test_contract.py`
- `skills/project-verifier/evals/fixtures/stale_authorization/stage2_live_execution.json`
- `skills/project-verifier/evals/fixtures/stale_authorization/stage2_quality_plan.md`
- `skills/project-verifier/evals/fixtures/stale_authorization/verification_manifest_v3.json`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution/task-04-report.md`

## Delivered Behavior

- `bash run_quality_template.sh` prints help and exits zero before it inspects a
  test path.
- `preflight` validates required names, files, commands, runtimes, bounds,
  script count, and the V3 confirmed Profile handoff. It does not dispatch a
  fixture path.
- `run` re-runs preflight, then validates the V3 `stage2 / live_e2e` decision
  envelope before it creates output directories or dispatches a script. Missing,
  material-change, over-limit, unconfirmed-Profile, stale, or invalid inputs
  fail closed through the V3 gate contract.
- The runner preserves `.py`, `.sh`, and `.ts` dispatch and reports exit code,
  duration, log path, actual calls, retries, side effects, and field-level
  telemetry provenance. Missing telemetry is `inconclusive`; mixed pass/fail
  paths are `completed` / `partial`.
- `stage2_quality.md` keeps project-native offline lint/build/unit/integration
  commands and fixture/mock oracles outside the runner. It defines one selected
  quality-scope confirmation and the narrow re-confirmation conditions.

## RED Evidence

1. `PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache python3 -m unittest discover -s skills/project-verifier/tests -p 'test_quality_runner.py' -v`
   - Exit `1`; `7` tests ran: `6` failures and `1` error.
   - Cause: `run_quality_template.sh` did not exist, so every runner invocation
     returned shell exit `127` and no result file could be written.
2. `PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache python3 -m unittest discover -s skills/project-verifier/tests -p 'test_contract.py' -v`
   - Exit `1`; `11` tests ran: `10` passed and `1` error.
   - Cause: `stage2_quality.md` did not exist.

## GREEN Evidence

| Command | Exit | Result |
|---|---:|---|
| Targeted quality-runner suite | `0` | `15/15` passed after authorization-path and output-root repair |
| Targeted contract/migration suite | `0` | `11/11` passed in `0.071s` |
| `bash -n skills/project-verifier/templates/run_quality_template.sh` | `0` | Syntax valid |
| `bash skills/project-verifier/templates/run_quality_template.sh` | `0` | Help printed; no path dispatch |
| Full V3 unittest discovery | `0` | `55/55` passed |
| `20260626_skill_hardening/template_behavior_tests.py` | `0` | `5/5` passed |
| `20260628_conditional_eval_gates/workflow_contract_tests.py` | `0` | `33/33` passed |
| `20260629_stage_gate_quality_v2/stage_gate_v2_tests.py` | `0` | `17/17` passed |
| `20260630_lean_core_simplification/lean_core_contract_tests.py` | `0` | `14/14` passed |
| `git diff --check` | `0` | No whitespace errors |

The targeted suite uses disposable local Git repositories and fixture scripts
only. It verifies preflight marker non-execution; material envelope mutation;
missing and over-limit authorization; unconfirmed Profile; lower valid
call/retry/timeout limits; Python/shell/TypeScript dispatch; partial results;
and absent telemetry. It does not execute a real target project path.

## Authorization and Profile Behavior

The runner invokes `validate_gate_v3.py profile` from preflight and before run
authorization can be used. `run` invokes `validate_gate_v3.py check` with the
Stage 2 receipt, envelope, source fingerprint, project root, and all four
approved limits. The dynamic tests prove that a changed envelope, a missing
receipt, a limit above the receipt, or a pending Profile prevents the fixture
script marker from being created.

The Stage 2 stale fixture uses V3 receipt and manifest schemas. Its plan embeds
a valid, materially changed decision envelope; the targeted test validates the
receipt and manifest schemas and proves that the canonical envelope hash differs
from the receipt hash without dispatching a path.

## Migration Matrix

Twelve historical assertions changed from `pending` to `ported`: Python/shell
dispatch; preflight max-path, no-dispatch, invalid-name, and invalid-bound
checks; exit-code preservation; machine-readable results; explicit mode;
missing telemetry; decision/actual telemetry; machine authorization; and
script-self-reported telemetry provenance.

Rows remain `pending` where this task did not add a direct complete equivalent,
including the missing-TypeScript-runtime assertion, no-script-directory case,
secret-value redaction output, blanket-Deno-permission assertion, and the
combined stale-authorization-plus-partial fixture assertion.

## Self-Review

- `git status --short` showed only Task 4 owned files before this report was
  added; no unrelated change was reverted.
- The V2 `run_usability_template.sh` was read and retained unchanged.
- No dependencies or Skills were installed; no network, real API, secret value,
  active scan, production-source write, staging, commit, push, or merge
  occurred.
- The runner intentionally does not execute offline project-native commands;
  the workflow records those separately, avoiding a false claim that live E2E
  runner success represents offline quality coverage.
- Controller review found a V2-derived default log directory outside the V3
  workbench write boundary. The runner now defaults to
  `project_verification_workbench/quality-e2e-reports` and preflight rejects
  any report/result path outside the workbench before dispatch.
- Independent review found that a valid envelope did not bind the discovered
  script set and that relative paths could write outside the project when the
  runner started from another directory. The runner now normalizes the test,
  report, and result paths against `PROJECT_ROOT`; dispatches scripts with the
  project root as their working directory; rejects external test directories;
  and requires a one-to-one match between discovered script path IDs and the
  envelope's approved `scope.path_ids` before any output directory is created.

## Limitations and Blockers

There are no blockers within the Task 4 owned-file scope. Static fixture and
temporary-script tests establish deterministic gate and result behavior, but do
not prove a future target project's telemetry honesty, runtime availability, or
real service behavior. The stale fixture proves hash mismatch structurally; the
dynamic current-source runner test proves pre-dispatch material-envelope
rejection. Neither is a real live E2E execution claim.
