# Phase 2: Project Mapping and Diagrams

## Purpose

Turn Phase 1 evidence into `project_verification_workbench/project_report.md` and the path matrix used by later tests.

## Scope Gate

Read `project_report.md` and current source evidence. Propose before writing:

- P0/P1/P2 user paths;
- architecture, module, data-flow, and user-flow diagrams;
- assumptions requiring confirmation;
- whether to create a README update copy.

The user owns path priority and diagram scope. Bind the approved proposal to the current source revision. A revision or scope change invalidates approval.

## Procedure

1. Map each path to its trigger, source entry point, modules, dependencies, inputs, outputs, state changes, failures, and recovery behavior.
2. Add Mermaid diagrams to `project_report.md`:
   - system architecture and external dependencies;
   - core module/data flow;
   - P0/P1 user flows and failure recovery;
   - risk joints where shared state or external services can fail.
3. Do not invent modules, users, or flows that lack source evidence. Label inferred relationships and unresolved gaps.
4. Create `project_verification_workbench/flow_matrix.md` with one row per approved path:

   | Path ID | Priority | User goal | Source entry | Preconditions | Expected result | Failure recovery | L1 | L2 | L3 |
   |---|---|---|---|---|---|---|---|---|---|

5. Write the same canonical matrix to `project_verification_workbench/phase2_flow_matrix.md`. Later phases consume this compatibility path; do not maintain different facts in the two files.

## Optional README Copy

Only when separately approved, create `README_updated_[Date]_[RandomID].md`. Preserve the original README. Public claims must cite current workbench evidence and state unverified boundaries.

## Exit

Update the manifest and ask the user to approve factual accuracy, path priority, and whether Phase 3 may plan tests. Offer revise, continue, or stop.
