# Task 3 Brief: Stage 1 Project Understanding

## Objective

Create the V3 Stage 1 workflow that turns a repository into a source-backed,
human-readable project understanding package: project report, flow matrix,
stable profile, and Mermaid diagrams. This is static understanding and scope
control, not a claim of exhaustive code review, penetration testing, or
compliance certification.

## Owned Files

- `skills/project-verifier/workflows/stage1_understanding.md`
- `skills/project-verifier/tests/test_contract.py`
- `skills/project-verifier/evals/fixtures/*/fixture.json` (the six existing
  descriptor files only)
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution/task-03-report.md`

## Required Behavior

1. Stage 1 records reviewed files, exclusions, unreviewed areas, and coverage
   limits. Large repositories use an inventory plus risk-based deep reading,
   never a false line-by-line-complete claim.
2. It produces `project_report.md`, `flow_matrix.md`, and `project_profile.json`.
   Every P0/P1/P2 path binds to source evidence.
3. `project_report.md` embeds Mermaid source for architecture, module/data flow,
   user flow, and failure recovery.
4. The Profile separates facts, inferences, and unknowns; feature-level AI
   classification is evidence-backed.
5. Before formal output, it asks one concise user confirmation covering goal,
   P0 paths, factual corrections, and interpretation-changing unknowns. README
   rewriting remains a separate optional output.
6. Stage 1 does not read secret values, install anything, access networks, or
   write production source.
7. Update all six fixture descriptors with only evidence-grounded fields:
   `feature_classification`, `entry_points`, `path_ids`, `trust_boundaries`, and
   `expected_capabilities`.
8. Add precise contract tests first, capture RED, then make them GREEN. Update
   migration rows only for historical assertions actually covered.

## Forbidden Actions

- Do not modify existing V2 workflows, V2 validators/templates, README, CI,
  production code, or historical reports.
- Do not invent fixture conclusions, install dependencies, access a network,
  read secret values, stage, commit, push, merge, or update the installed Skill.

## Required Report

Write `task-03-report.md` with changed files; RED/GREEN commands, exit codes,
and counts; fixture evidence limits; migration changes; self-review; and any
blockers. The detailed contract is Task 3 in `IMPLEMENTATION_PLAN.md`.
