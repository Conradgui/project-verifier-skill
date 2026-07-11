# Task 2 Brief: Decision-Envelope Control Plane

## Objective

Add the V3 decision-envelope authorization control plane beside the existing
V2 contracts. A changed log or Markdown plan must not invalidate approval;
changed source identity, risk scope, interpretation, or upper execution limits
must fail closed.

## Owned Files

- `skills/project-verifier/templates/decision_envelope_template.json`
- `skills/project-verifier/templates/project_profile_template.json`
- `skills/project-verifier/templates/verification_manifest_v3_template.json`
- `skills/project-verifier/references/artifact_contracts.md`
- `skills/project-verifier/scripts/validate_gate_v3.py`
- `skills/project-verifier/tests/test_control_plane.py`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution/task-02-report.md`

## Required Behavior

1. Use standard-library Python only. Expose `canonical_object_hash`,
   `validate_decision_envelope`, and `requested_limit_is_within` from
   `validate_gate_v3.py`.
2. Hash canonical JSON only. Numeric maxima may be lowered but never raised;
   strings, booleans, lists, and objects require equality.
3. `check` validates an exact receipt field set, duplicate/missing decision
   handling, receipt/envelope identity, stage, decision type, limits, source
   policy, and fail-closed conditions.
4. `fingerprint` remains secret-safe. `paths` remains fail-closed.
5. `exact` source policy requires the current fingerprint to equal the approved
   base. `approved_fix_scope` accepts only a clean Git commit base that is an
   ancestor of `HEAD`, and only when every committed, staged, unstaged, and
   untracked changed path is in `allowed_fix_paths`.
6. The V3 manifest contains only `stages.stage1` through `stages.stage4`, the
   four independent state dimensions, `source_history`, and `project_profile`.
   Do not alter the V2 canonical manifest.
7. The stable Project Profile contains factual project-understanding material,
   not commands, tool choices, secret values, or transient limits.
8. Add RED-to-GREEN tests for formatting-stable hashes, material changes,
   upper/lower limits, receipt failures, exact and approved-fix source policy,
   dirty/untracked/non-ancestor failure, state semantics, write-scope behavior,
   and secret-safe templates. Update migration rows only for tests actually
   implemented.
9. End with the Task 2 suite, full V3 suite, and all four historical Python
   suites passing. Record exact commands, exit codes, and counts.

## Forbidden Actions

- Do not modify V2 validators, V2 templates, existing workflows, README,
  existing CI configuration, or historical reports.
- Do not install dependencies, access network/API services, inspect secret
  values, commit, push, merge, or update the installed Skill.
- Do not stage files; the controller owns Git state.
- Do not add default scores, claims, or behavior outside the approved Task 2
  interface.

## Required Report

Write `task-02-report.md` with status, changed files, RED and GREEN evidence,
source-policy test coverage, changed migration rows, self-review, limitations,
and any blockers. The detailed specification remains Task 2 in
`IMPLEMENTATION_PLAN.md`.
