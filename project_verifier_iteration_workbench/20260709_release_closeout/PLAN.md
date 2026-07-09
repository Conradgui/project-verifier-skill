# Project Verifier Release Closeout Plan

## Objective

Close the remaining release gaps after the lean-core simplification without adding new product scope.

## Scope

- Align README, SKILL, workflow, CONTRIBUTING, and optional Hook documentation with the current five-phase design.
- Add a small machine gate requiring explicit benchmark rubric approval before metric calculation.
- Clarify Phase 4 telemetry provenance so self-reported script telemetry is not mistaken for wrapper-enforced limits.
- Add minimal offline GitHub Actions CI.

## Non-Scope

- Do not reintroduce browser recording, replay, production browser operation, multi-host Hook roadmaps, universal scores, or radar charts.
- Do not run real API, model, browser, database, or paid evaluations.
- Do not install the optional Hook or update the local installed skill copy in this iteration.
- Do not rerun the full 66-test suite before changes; rely on the existing lean verification report and rerun only tests invalidated by this closeout work.

## Verification Strategy

- Add targeted contract tests first where current behavior is under-specified.
- Run targeted tests after implementation.
- Run syntax checks for changed shell/Python/YAML-style files.
- Run `git diff --check` after edits.
