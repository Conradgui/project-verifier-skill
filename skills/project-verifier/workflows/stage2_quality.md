# Stage 2: Quality and Authorized Smoke/Live E2E

## Purpose

Stage 2 verifies selected quality paths without treating a pass rate as code
coverage. It combines offline quality evidence, runnability, Smoke checks, and
explicitly authorized live E2E into one report while keeping their execution
boundaries distinct. It is not a security scan and it does not change
production source to make tests pass.

## One Selected-Quality-Scope Gate

After the confirmed Stage 1 Profile is available, present exactly one concise
selected-quality-scope user gate. It records the selected paths, project-native
commands, fixture/mock oracles, allowed test-output paths, and whether a
Smoke/live path needs a `stage2 / live_e2e` decision envelope. Ask again only
for production fixes, dependency installations, live calls, sensitive data, or
changed side effects.

## Offline Quality and Runnability

Use project-native lint, build, unit, and integration commands where they
already exist. Record each command, its oracle, exit code, duration, log path,
and untested paths in `project_verification_workbench/quality_report.md` and
`project_verification_workbench/phase2_quality_results.json`.

- Offline checks use fixture/mock oracles and must block network access.
- Prefer existing project commands; do not install dependencies automatically.
- Generated tests belong outside production source unless a separate source-fix
  envelope authorizes a production change.
- The Stage 2 runner does not execute offline unit tests itself. It only runs
  selected approved Smoke/live path scripts.
- Pass rate is not code coverage. Report coverage only when a coverage tool
  produced a coverage artifact, and keep that artifact separate from pass rate.

## Smoke/Live Plan and No-Call Preflight

Create `project_verification_workbench/phase2_quality_plan.json` and its human
summary `project_verification_workbench/phase2_quality_plan.md`. For each
Smoke/live path, include path ID, script, required environment-variable names,
files, commands, runtime, fixture versus live target, exact limits, expected
side effects, output paths, stop conditions, and telemetry fields.

Run `bash run_quality_template.sh preflight` before requesting live execution.
Preflight validates names, scripts, files, commands, runtimes, task bounds, and
the confirmed Stage 1 Profile handoff with `validate_gate_v3.py profile`. It
must not execute a path script, network call, production change, or offline
project command.

## Live E2E Authorization and Execution

`bash run_quality_template.sh run` re-runs preflight and validates the confirmed
Stage 1 Profile before any dispatch. It then requires a current, approved V3
decision-envelope authorization for `stage2 / live_e2e`, including exactly
`max_paths`, `max_calls_per_path`, `max_retries`, and `timeout_seconds`. Missing,
stale, invalidated, material-change, or over-limit authorization fails closed
before any script dispatch.

The runner retains `.py`, `.sh`, and `.ts` dispatch. For every path it records
the wrapper-observed exit code, duration, and log path, plus script-self-reported
actual calls, retries, and side effects. Missing or invalid script telemetry is
`inconclusive`; a mixture of passed and failed paths is `phase_status:
completed` with `result_outcome: partial`.

Do not read secret values. Do not execute real APIs without the approved live
envelope. Do not install tooling or write production source from this workflow.

## Output and Recovery

Write the selected scope, offline evidence, authorized path results, telemetry
provenance, authorization decision ID, and limitations to `quality_report.md`.
Keep `phase_status`, `result_outcome`, `execution_scope`, and
`claim_eligibility` separate in the machine result. When a prerequisite is
missing, record a recovery condition rather than silently installing, changing
source, or broadening the approved side effects.
