# Task 0 Review: Pre-Execution Plan Review

## Verdict

- `spec_compliance: changes_required`
- `code_quality: changes_required`
- Task 1 may start: no

## Critical Findings

1. The existing staged design baseline would be included in the first ordinary task commit, destroying task-level commit boundaries.
2. Renaming canonical runners and changing the validator before switching CI would break the historical tests that current CI still executes.
3. `approved_fix_scope` did not explicitly compare the approved base commit against committed changes in `HEAD`, index, working tree, and untracked files.

## Important Findings

1. The historical-to-V3 migration matrix lacked a machine check for complete legacy coverage and real target tests.
2. Runner invocation assumed executable bits that templates do not guarantee.
3. The orchestration research status and runtime capability wording were stale after approval.
4. Development orchestration evidence and target-project workbench paths were conflated.
5. Final evidence was reviewed before it was staged.

## Required Corrections

- Commit the approved design baseline before staging Task 1 files and verify every task's staged file list before commit.
- Keep V2 canonical consumers intact while V3 files are built and tested beside them; switch names, CI, and consumers atomically in Task 7.
- End every task with all currently active tests GREEN; do not commit a long-lived RED suite.
- Compare `base commit -> HEAD + index + working tree + untracked` for approved fix scopes and test committed out-of-scope changes.
- Use a machine-readable migration matrix and validate both legacy coverage and target-test existence before old CI removal.
- Invoke shell runners with `bash <runner>`.
- Keep development execution evidence under the current iteration workbench; reserve `project_verification_workbench/agent_execution/` for target-project Skill runs.
- Stage final evidence before inspecting the staged diff.

## Source

Independent read-only explorer `019f4bd7-f388-7720-a2da-98b3e5a0bb78`.
