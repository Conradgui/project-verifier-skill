---
name: project-verifier
description: >-
  A modular, evidence-backed project understanding and verification suite.
  Reads codebases, maps architecture, documents user flows, audits security and
  quality risks, generates mock and real usability tests, runs reproducible
  benchmarks, and builds traceable evidence packages. Use when the user asks to
  understand a software project, generate architecture or flow diagrams, audit a
  project, verify project quality, prepare interview proof points, build mock or
  live usability tests, benchmark an AI app against a baseline LLM, or run
  phase-specific project-verifier workflows.
---

# Project Verifier & Quality Suite

## Overview
This skill provides a comprehensive, 6-phase project understanding and verification framework. It is designed to work with AI Coding Agents (such as Claude Code, Codex, Cursor Agent, Gemini CLI, etc.) to help users understand a codebase, map architecture and user flows, audit risks, establish testing structures, and produce traceable evidence packages. It is a workflow skill, not a guarantee of project quality; every quality or interview claim must be backed by durable evidence.

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
1. **Full Suite Mode (Recommended)**: Runs Phase 1 through Phase 6 sequentially in the same conversation session.
2. **Selective Phase Mode**: Runs a specific phase standalone. To do this, the agent loads the corresponding phase instructions from the `workflows/` directory. If any pre-requisite information or outputs from earlier phases are missing, the agent must first perform a quick, non-destructive exploration and write the missing context into `project_verification_workbench/` before continuing.

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
| Phase 4 | `phase4_usability_results.json` | Real usability path results, required env vars, exit codes, durations, logs, and failure stages. |
| Phase 5 | `phase5_benchmark_results.json` | Benchmark runner outputs with assertions and measurement boundaries. |
| Phase 6 | `phase6_interview_source_map.md` | Source map linking interview claims to workbench evidence and user Grill answers. |

Do not claim a quality, safety, cost, latency, or interview advantage unless it is backed by one of these artifacts or explicitly marked as not measured.

## User-Facing Deliverables

The full suite produces four independent but cross-referenceable deliverable families:

| Deliverable | Default path | Audience and purpose |
|---|---|---|
| Project understanding package | `project_verification_workbench/project_understanding/` | Human-readable explanation of what the project is, where it starts, how modules cooperate, how users move through it, and where risks sit. |
| Verification workbench | `project_verification_workbench/phase*_*.md/json` | Durable source of truth for later phases, including audits, flow matrix, test plans, usability results, benchmark results, and interview source maps. |
| README update copy | `README_updated_[Date]_[RandomID].md` | Public-facing README rewrite based on the understanding artifacts. This is not a replacement for the project understanding package. |
| Interview / presentation evidence pack | `interview_evidence_pack/` | Role-specific narratives, decision logs, verification summaries, architecture evolution notes, and benchmark visuals derived from workbench evidence and user Grill answers. |

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
  │     ├── phase4_usability.md# Real API usability verification
  │     ├── phase5_benchmark.md# Automated Tool vs. Baseline LLM evaluation & HTML charts
  │     └── phase6_interview.md# Custom job role alignment & Grill pack
  └── templates/               # Reusable code and configuration templates
        ├── benchmark_evaluator_template.py
        └── run_usability_template.sh
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
*   **Purpose**: Read codebase, evaluate basic architectures, list entry points, and identify security vulnerabilities (🔴/⚠️/✅/❓).
*   **Safety rule**: Strictly read-only. Do not edit files or write code in this phase.

### Phase 2: Project Understanding & Diagrams (`workflows/phase2_diagrams.md`)
*   **Purpose**: Create a fixed project understanding document package, including project overview, technical architecture diagrams, module/data-flow diagrams, user flow diagrams, and a reusable flow matrix.
*   **Safety rule**: Original `README.md` is preserved. A copy is created at `README_updated_[Date]_[RandomID].md` with embedded diagrams. The fixed understanding package is written separately under `project_verification_workbench/project_understanding/`.

### Phase 3: Quality Mock Tests (`workflows/phase3_quality.md`)
*   **Purpose**: Generate unit and integration tests using mock / scripted providers. Output runner to `run_tests.sh`.

### Phase 4: Real Usability Verification (`workflows/phase4_usability.md`)
*   **Purpose**: Verify P0 user paths using real API calls (uses environment variables, never hardcoded keys). Output runner to `run_usability.sh`.

### Phase 5: Automated Benchmarking (`workflows/phase5_benchmark.md`)
*   **Purpose**: Automate Tool Runner vs. Baseline LLM Runner. Compare results using an Evaluator. Output runner to `run_benchmark.sh`.

### Phase 6: Custom Interview Evidence Pack (`workflows/phase6_interview.md`)
*   **Purpose**: Grill the user on their goals, JD, and target position. Build customized话术 (narratives), decisions logs, and proof points in `interview_evidence_pack/`.

---

## Common Pitfalls
*   **Modifying files prematurely**: Always finish Phase 1 audits completely before editing any code files.
*   **Exposing Secrets**: Under no circumstances should API keys or passwords be hardcoded or written to test directories. Always load via environment variables.
*   **Unbounded LLM loops**: In Phase 4 & 5, ensure API client requests have retry caps, backoffs, and maximum timeouts to avoid runaway costs.
