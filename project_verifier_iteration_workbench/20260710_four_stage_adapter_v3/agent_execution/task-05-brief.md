# Task 5 Brief: Stage 3 Project-Fit Security Boundary Verification

## Objective

Implement the V3 security stage as a bounded, project-adapted verification
workflow. It must derive surfaces from the confirmed Profile, compare tools
with trade-offs, preflight safely, require separate authority for distinct
risk capabilities, and normalize findings without inventing exploitability or
a project-wide security score.

## Owned Files

- `skills/project-verifier/workflows/stage3_security.md`
- `skills/project-verifier/references/tool_adapters.md`
- `skills/project-verifier/templates/run_security_template.sh`
- `skills/project-verifier/templates/security_normalizer_template.py`
- `skills/project-verifier/tests/test_security.py`
- `skills/project-verifier/tests/test_contract.py`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json`
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution/task-05-report.md`

## Required Behavior

1. Detection never installs tools or scans targets. Tool choice compares fit,
   coverage, offline capability, maintenance, version, network/database cost,
   target risk, and blind spots; a declined recommendation records the fallback
   and reduced coverage.
2. Runner is `bash run_security_template.sh preflight|run`; no argument is
   help-only. `preflight` validates the confirmed Stage 1 Profile, installed
   tool names, task scripts, targets, output paths, limits, and permissions
   without scanner target execution.
3. Stage 3 separates authorization for offline read-only tasks, tool download,
   vulnerability database update, network, passive dynamic scan, and active
   scan. Active scans reject non-local/non-isolated targets.
4. `run` requires a current V3 `stage3/security_execution` envelope and
   complete limits before dispatch. It writes only under the workbench and
   records command identity, version, exit code, duration, raw-output path,
   target, network/active mode, side effects, and decision ID.
5. The normalizer accepts adapter-intermediate findings; validates, redacts
   secret-like fields recursively, preserves raw evidence, creates deterministic
   IDs when missing, deduplicates only exact category/rule/location matches,
   and leaves uncertain triage as `needs_review`.
6. Clean results say only that no issue was found in the executed scope. No
   security score, certification, or inferred exploitability is allowed.
7. Add focused RED-to-GREEN tests. Do not install tools, access networks, scan
   targets, modify V2 consumers, production code, README, or CI.

## Required Report

Write `task-05-report.md` with status, changed files, RED/GREEN commands and
counts, tool-selection boundary, authorization coverage, normalizer behavior,
migration rows, limitations, and blockers. Do not stage, commit, push, or merge.
