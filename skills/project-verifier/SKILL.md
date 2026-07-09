---
name: project-verifier
description: >-
  Use when a user needs to understand, map, audit, test, or evidence a software
  project; asks for architecture or user-flow documentation, scoped security or
  quality review, offline tests, gated live E2E, AI evaluation, or evidence-backed
  README, interview, defense, or portfolio material.
---

# Project Verifier

## Overview

Run a five-phase project understanding and verification workflow. Prefer existing deterministic scripts, preserve negative results, and bind high-risk execution to current evidence. Never turn missing measurements into positive claims.

## Identity

- Repository: `https://github.com/Conradgui/project-verifier-skill.git`
- Skill path: `skills/project-verifier`
- Skill name and invocation: `project-verifier` / `$project-verifier`

Install the skill directory, not the repository root.

## Core Rules

1. **Script-first:** reuse existing tests and deterministic scripts before generating new ones.
2. **Read before writing:** Phase 1 is read-only except for workbench evidence.
3. **Ask at consequential gates:** production code, dependencies, live calls, costs, sensitive data, baselines, metrics, public claims, and optional exports belong to the user.
4. **No inferred evidence:** record interpretation-changing unknowns as `unknown` and ask.
5. **Evidence before claims:** preserve failures, empty outputs, limitations, raw logs, and current source identity.

At every boundary offer: continue, revise, skip an optional action, or stop and retain evidence.

## Control Plane

Create `project_verification_workbench/verification_manifest.json` from `templates/verification_manifest_template.json`. It is the canonical state file. Capture the source with:

```bash
python3 scripts/validate_gate.py fingerprint --root <project>
```

Keep these state dimensions separate:

| Field | Meaning |
|---|---|
| `phase_status` | Whether workflow work ran |
| `result_outcome` | What verification observed |
| `execution_scope` | `none`, `plan_only`, `pilot`, or `full` |
| `claim_eligibility` | Maximum evidence scope that may be described |

A completed test run may have `result_outcome: fail`. A pilot is completed but remains `result_outcome: inconclusive` and `claim_eligibility: pilot`.

## Authorization Contract

Before a high-risk action, create an authorization receipt and record the same object once in the manifest. It must include `decision_id`, `phase`, `decision_type`, `proposal_sha256`, `source_revision`, `user_choice`, `approved_limits`, `approved_at`, and `invalidated_at`.

Use `scripts/validate_gate.py check` before execution. Reject missing, changed, duplicated, expired, invalidated, or non-approved receipts. A proposal, source revision, action, or limit change requires a new decision. No response is not approval.

Do not read secret values. Record only required variable names and missing conditions.

## Evidence Contract

Create durable artifacts before moving to the next phase:

| Stage | Required artifacts |
|---|---|
| Control | `verification_manifest.json`, `authorizations/*.json` |
| Phase 1–2 | `project_report.md`, `flow_matrix.md`, `phase2_flow_matrix.md` |
| Phase 3 | `phase3_test_plan.md`, `phase3_test_results.md` |
| Phase 4 | `phase4_usability_plan.md`, `phase4_usability_results.json` |
| Phase 5 | `phase5_benchmark_plan.md`, `phase5_benchmark_results.json` |

`flow_matrix.md` is the human-readable source. Keep `phase2_flow_matrix.md` synchronized as the compatibility path consumed by later phases.

The default user reading path is `project_report.md`, `flow_matrix.md`, and the current phase results. Keep raw logs and runner outputs even when results are negative.

## Workflows

Load only the workflow needed for the current phase:

1. [Phase 1: scoped exploration and static risk review](workflows/phase1_explore.md)
2. [Phase 2: project mapping and diagrams](workflows/phase2_diagrams.md)
3. [Phase 3: offline behavior tests](workflows/phase3_quality.md)
4. [Phase 4: authorized live E2E](workflows/phase4_usability.md)
5. [Phase 5: evidence-first AI comparative evaluation](workflows/phase5_benchmark.md)

Phase 1–3 form the universal core. Phase 4 depends on the project environment. Phase 5 applies only to AI or AI-assisted features with a defensible comparison question.

## Optional Exports

Optional exports are not phases:

- Phase 2 may create `README_updated_[Date]_[RandomID].md` after separate approval.
- When the user explicitly requests interview, defense, or portfolio material, load [optional interview export](workflows/optional_interview_export.md).

The interview export creates only `interview_evidence_pack.md` plus `project_verification_workbench/interview_evidence_source_map.md`. Every strong claim must cite a current-revision workbench artifact and receive claim approval.

## Credibility Boundaries

- Static review is not penetration testing, compliance certification, or complete coverage.
- `preflight` performs no target execution.
- Missing telemetry produces `inconclusive`, not success.
- Phase 4 call counts, retries, and side effects are script self-reported unless
  independent instrumentation is present.
- Test pass rate is not code coverage.
- Empty or missing output and nonzero runner exits cannot win a comparison.
- A single run cannot prove stability. Respect every metric's `minimum_samples`.
- Phase 5 metrics require `rubric_approved: true` after user approval.
- Report raw values, thresholds, sample adequacy, evidence, and limitations. Do not produce a universal project score.
- LLM Judge must be blinded and versioned and cannot alone prove safety, security, privacy, or leakage.
- Do not claim stable Agent gate compliance until a separately authorized Agent behavior evaluation supports it.

## Common Mistakes

- Treating README statements as code evidence.
- Modifying production code to make Phase 3 tests pass without a new decision.
- Reusing approval after source or plan changes.
- Calling a pilot a completed benchmark.
- Dropping failed or inconvenient runs.
- Generating public claims from conversation context instead of workbench evidence.
