# Lean Core Simplification Plan

## Goal

Reduce user-facing complexity without weakening the verified authorization,
telemetry, evidence, and evaluation boundaries in Stage Gate V2.

## Required Changes

1. Remove recorded browser replay and multi-host Guarded/Isolated planning.
2. Present five core phases; make interview evidence a single optional export.
3. Consolidate human-facing project understanding into `project_report.md` and
   `flow_matrix.md`, while retaining `phase2_flow_matrix.md` compatibility.
4. Keep revision-bound approvals, no-call preflight, execution telemetry,
   four-dimensional state, raw-first evaluation, and all six fixtures.
5. Remove normalized scores and radar output from the evaluator.
6. Add a separately installed, Codex-only hook for five high-risk action
   classes. It must not claim sandbox or cross-host enforcement.

## Non-Goals

- No real API, browser, model, database, or paid execution.
- No dependency or hook installation.
- No update to the installed skill copy.
- No merge, commit, or push.
