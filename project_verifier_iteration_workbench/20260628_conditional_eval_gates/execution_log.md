# Execution Log

## 2026-06-28

- Created isolated branch `codex/conditional-eval-gates` in a project-local worktree.
- Baseline: five existing template behavior tests passed.
- Baseline: bootstrap and usability shell syntax checks passed.
- Baseline: Python template compilation and skill validation passed.
- RED: added 10 initial contract tests; all 10 failed against the previous workflow as expected.
- Reworked the orchestrator around a durable verification manifest and risk-based gates.
- Updated Phase 1-3 for AI classification, pre-generation approval, optional README output, and fully offline L1 tests.
- Updated Phase 4 with a durable plan, environment repair/skip path, explicit execution authorization, and preflight/run modes.
- Updated Phase 5 with guided scenarios, scenario-specific baselines, feasibility states, plan-only fallback, pilot boundaries, and explicit Phase 6 opt-in.
- Updated Phase 6 so no interview files are created without explicit consent.
- Replaced heuristic evaluator scores with task-defined rubrics, structured success thresholds, minimum samples, evidence requirements, and conditional radar generation.
- Migrated prior behavior tests to the new evaluator and runner interfaces.
- Updated README and Codex metadata to describe the conditional three-tier workflow.
- No real API was called, no package was installed, and no secret-bearing file was read.

## 2026-06-29 Audit Remediation

- Reproduced evaluator acceptance of mismatched task IDs, pilot execution mislabeled as completed, out-of-range score mappings, and malformed sample counts.
- Added comparison-level validation for task identity, runner roles, completed status, full execution mode, and zero exit codes.
- Added 0-10 score bounds, numeric rubric validation, safe sample-count parsing, and script-safe JSON embedding.
- Added traceable LLM-as-a-Judge support requiring metric ID, score, evidence, prompt, model, and confidence.
- Removed the stale `vcrpy` dependency from the offline Phase 3 CI example.
- Extended usability preflight to validate environment names, required files, required commands, runtimes, numeric bounds, and maximum path count.
- Added direct Phase 4 result JSON generation with preserved per-script exit codes and failure stages.
- Added six realistic conditional workflow prompts in `skills/project-verifier/evals/evals.json`.
- Hardened evaluator input handling for malformed evidence containers, entries, field names, and non-finite numeric values.
- Removed blanket Deno permissions and replaced an unsupported Phase 6 percentage example with an evidence-bound example.
- Expanded offline contract coverage from 13 to 33 tests, including separate score and threshold reporting. No model-backed eval or live API call was run.
