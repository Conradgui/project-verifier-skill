---
name: project-verifier
description: >-
  Use when a user needs to understand, map, audit, test, or evidence a software
  project; asks for architecture or user-flow documentation, security or quality
  review, mock tests, gated live E2E verification, AI evaluation or benchmark
  design, or an optional interview or presentation evidence pack.
---

# Project Verifier & Quality Suite

## Overview
This skill is a six-phase project understanding and verification workflow with conditional execution gates. Phase 1-3 form the offline core, Phase 4 is gated live usability verification, Phase 5 is a gated AI comparative evaluation, and Phase 6 is an optional presentation layer. It helps users create traceable evidence; it does not guarantee project quality or turn missing measurements into positive claims.

## Identity

- Repository: `https://github.com/Conradgui/project-verifier-skill.git`
- Skill path in the repository: `skills/project-verifier`
- Skill name: `project-verifier`
- Codex invocation name: `$project-verifier`

If Codex receives the repository root URL, locate `skills/project-verifier/SKILL.md`
and install `skills/project-verifier` as the skill directory. Do not install the
repository root as the skill directory.

## Execution Modes

This skill supports two execution modes:
1. **Full Suite Mode (Recommended)**: Runs Phase 1 through Phase 3 as the universal core. Phase 4 and Phase 5 continue only after applicability, environment, cost, and execution gates. Phase 6 runs only when the user explicitly opts in.
2. **Selective Phase Mode**: Runs one requested phase. If prerequisite artifacts are missing, perform a non-destructive recovery pass and write the recovered context before continuing. Selective Phase 4-6 still require their own user gates.

## Verification Manifest Contract

At the start of either mode, create or reuse `project_verification_workbench/verification_manifest.md`. Record:

- User goal, selected mode, selected phases, and allowed write scope.
- Project classification: `AI`, `AI-assisted`, `non-AI`, or `unknown`, with evidence.
- Required environment variable names and backend dependencies, never secret values.
- Each phase status using exactly: `pending / in_progress / completed / blocked / skipped / not_applicable / failed`.
- User approvals, blockers, recovery conditions, and links to generated artifacts.

Update the manifest before and after every phase. A missing credential is a blocker or skip reason, not permission to inspect `.env`, invent a result, or silently install a dependency.

Artifact-specific execution states such as `pilot_only` may appear inside a result JSON, but they do not extend the manifest status enum. If Phase 5 ends after a pilot, set its manifest status to `skipped` and record `pilot_only` as the completed execution scope.

## Risk-Based Interaction Contract

- Phase 1: confirm goals, entry points, classification, and blockers after read-only analysis.
- Phase 2: confirm P0/P1/P2 scope and diagram scope before writing the document package; ask separately whether to create a README update copy.
- Phase 3: show the test plan, exact files, CI changes, and dependency commands before writing code. Do not install automatically.
- Phase 4: approve the live plan, environment readiness, maximum calls/retries/timeouts, and execution before any real request.
- Phase 5: approve scenarios, baselines, rubrics, feasibility, and execution budget. A no-call preflight is mandatory; a real pilot is risk-based and never substitutes for a full benchmark.
- Phase 6: create interview or presentation materials only after an explicit opt-in.

At every phase boundary, offer: continue, revise this phase, skip the next optional phase, or stop and retain current artifacts.

## Evidence Workbench Contract

Create or reuse a folder named `project_verification_workbench/` in the target project root. Each phase must write durable evidence there before moving on:

| Phase | Required workbench artifact | Purpose |
|---|---|---|
| Phase 1 | `phase1_audit.md` | Read-only audit, risk table, entry points, and proceed/stop decision. |
| Phase 2 | `project_understanding/project_understanding_report.md` | Human-readable project understanding report. |
| Phase 2 | `project_understanding/architecture_diagrams.md` | Technical architecture, module, data-flow, dependency, and risk-joint diagrams. |
| Phase 2 | `project_understanding/user_flows.md` | P0/P1/P2 user flows, inputs, outputs, and failure recovery paths. |
| Phase 2 | `project_understanding/flow_matrix.md`, `phase2_flow_matrix.md` | Human-readable and compatibility copies of the path matrix used by later tests and benchmarks. |
| Phase 3 | `phase3_test_plan.md`, `phase3_test_results.md` | Mock test plan, generated files, and actual run results. |
| Phase 4 | `phase4_usability_plan.md`, `phase4_usability_results.json` | Live-path plan plus completed, blocked, or skipped execution state. |
| Phase 5 | `phase5_benchmark_plan.md`, `phase5_benchmark_results.json` | AI-eval scenarios, approved rubrics, runner outputs, status, and measurement boundaries. |
| Phase 6 | `phase6_interview_source_map.md` | Conditional source map created only after the user opts into Phase 6. |

Do not claim a quality, safety, cost, latency, or interview advantage unless it is backed by one of these artifacts or explicitly marked as not measured.

## User-Facing Deliverables

The skill supports four independent but cross-referenceable deliverable families; optional families are created only after their user gate:

| Deliverable | Default path | Audience and purpose |
|---|---|---|
| Project understanding package | `project_verification_workbench/project_understanding/` | Human-readable explanation of what the project is, where it starts, how modules cooperate, how users move through it, and where risks sit. |
| Verification workbench | `project_verification_workbench/phase*_*.md/json` | Durable source of truth for later phases, including audits, flow matrix, test plans, usability results, benchmark results, and interview source maps. |
| README update copy | `README_updated_[Date]_[RandomID].md` | Optional public-facing README rewrite, created only when the user requests it in Phase 2. |
| Interview / presentation evidence pack | `interview_evidence_pack/` | Optional role-specific materials created only after Phase 6 opt-in and derived from workbench evidence. |

Treat `interview_evidence_pack/` as a presentation layer, not a new source of truth. Strong claims in that pack must cite `project_verification_workbench/phase6_interview_source_map.md` or an earlier phase artifact.

## Directory Structure & Installation

### Installer
*   `bootstrap.sh`: Script in the project root to symlink this skill to local Agent configurations.

### Skill Layout
The core skill files are organized under:
```
project-verifier/
  ├── SKILL.md                 # This file (Main Orchestrator)
  ├── workflows/               # Instruction workflows for each individual phase
  │     ├── phase1_explore.md  # Safe repo exploration & audit
  │     ├── phase2_diagrams.md # Project understanding docs, Mermaid diagrams, & README update
  │     ├── phase3_quality.md  # Mock-based unit/integration tests & CI templates
  │     ├── phase4_usability.md# Conditional live E2E verification
  │     ├── phase5_benchmark.md# Guided AI comparative evaluation
  │     └── phase6_interview.md# Optional role alignment & evidence pack
  ├── templates/               # Reusable code and configuration templates
  │     ├── benchmark_evaluator_template.py
  │     └── run_usability_template.sh
  └── evals/
        └── evals.json         # Six conditional workflow behavior prompts
```

### Installation
For Codex installation from GitHub:

```bash
python3 /Users/conrad/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/Conradgui/project-verifier-skill/tree/main/skills/project-verifier
```

For local symlink installation from a cloned repository:

```bash
./bootstrap.sh codex --dry-run
./bootstrap.sh codex
./bootstrap.sh all --dry-run
./bootstrap.sh all
```

---

## Skill Workflows Quick Index

To run a specific phase, load and execute the corresponding instructions:

### Phase 1: Exploration & Audit (`workflows/phase1_explore.md`)
*   **Purpose**: Read the codebase, classify its AI role, list entry points and environment requirements, and identify architecture, security, and quality risks.
*   **Safety rule**: Strictly read-only. Do not edit files or write code in this phase.

### Phase 2: Project Understanding & Diagrams (`workflows/phase2_diagrams.md`)
*   **Purpose**: Create a fixed project understanding document package, including project overview, technical architecture diagrams, module/data-flow diagrams, user flow diagrams, and a reusable flow matrix.
*   **Safety rule**: Confirm flow and diagram scope before writing. Preserve the original `README.md`; create a dated README copy only when requested.

### Phase 3: Quality Mock Tests (`workflows/phase3_quality.md`)
*   **Purpose**: Generate offline unit and integration tests using mock or scripted providers after plan and file approval.

### Phase 4: Real Usability Verification (`workflows/phase4_usability.md`)
*   **Purpose**: Conditionally verify real P0 paths using live dependencies. Missing environments produce a recoverable plan, not fabricated results.

### Phase 5: Guided AI Comparative Evaluation (`workflows/phase5_benchmark.md`)
*   **Purpose**: For AI or AI-assisted features, propose scenario-specific baselines and execute only approved, feasible, rubric-backed evaluations.

### Phase 6: Custom Interview Evidence Pack (`workflows/phase6_interview.md`)
*   **Purpose**: After explicit opt-in, align existing evidence to an interview, defense, or portfolio audience.

---

## Common Pitfalls
*   **Modifying files prematurely**: Always finish Phase 1 audits completely before editing any code files.
*   **Exposing Secrets**: Under no circumstances should API keys or passwords be hardcoded or written to test directories. Always load via environment variables.
*   **Unbounded LLM loops**: In Phase 4 & 5, ensure API client requests have retry caps, backoffs, and maximum timeouts to avoid runaway costs.
*   **Treating pilots as benchmarks**: A smoke or pilot result may validate the harness, but it cannot support full benchmark claims.
*   **Optimizing for attractive results**: Preserve negative and inconclusive outcomes. Change the product or rubric transparently, never cherry-pick evidence.
