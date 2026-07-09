# Phase 4: Authorized Live E2E

## Purpose

Verify approved user paths against the real dependencies they actually require. Local real paths and external API paths are evaluated separately.

## Plan and Preflight

Load `project_verification_workbench/verification_manifest.json`, `phase2_flow_matrix.md`, and Phase 3 results. Create `project_verification_workbench/phase4_usability_plan.md` containing:

- selected path IDs and exact commands;
- required services, files, runtimes, and environment variable names;
- maximum paths, calls per path, retries, timeout, and cost estimate;
- expected side effects, allowed output paths, stop conditions, and cleanup;
- telemetry fields required from each script.

Reuse existing project scripts first, including existing Playwright or Cypress E2E tests. Do not install tooling automatically.

Run `run_usability.sh preflight` before requesting execution approval. Preflight may inspect names, files, commands, runtimes, schema, and limits; it must not execute a target path.

## Execution Gate

If dependencies are missing, offer assistance or save a recovery plan. Do not read secret values.

Before `run`, obtain a receipt bound to:

- `proposal_sha256` and current `source_revision`;
- selected paths and exact execution limits;
- cost, sensitive-data use, and permitted side effects.

Validate it with `validate_gate.py`. Missing, stale, invalidated, or mismatched authorization stops execution.

## Results

Write `project_verification_workbench/phase4_usability_results.json` with top-level state and per-path:

- command/script type, exit code, duration, and log path;
- actual external calls, retries, side effects, and generated artifacts;
- failure stage, errors, missing conditions, and recovery conditions;
- authorization `decision_id` and approved limits.

Separate telemetry provenance in the result. The runner can directly observe
exit code, duration, and log path. External call counts, retries, and side
effects are `script_self_reported` unless the target project provides independent
instrumentation. Do not describe self-reported telemetry as wrapper-enforced.

If required telemetry is missing, use `result_outcome: inconclusive` and `claim_eligibility: none`. Do not claim that cost or call boundaries were satisfied.

Update the manifest and ask whether to revise, continue to Phase 5 when applicable, or stop.
