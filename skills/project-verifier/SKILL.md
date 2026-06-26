---
name: project-verifier
description: >-
  A modular, evidence-backed project verification and interview evidence suite.
  Audits codebase health, creates diagrams, generates mock quality tests, real API
  usability tests, reproducible benchmarks, and traceable interview evidence
  packages. Use when the user asks to verify a software project, generate
  project quality evidence, prepare interview proof points, build mock or live
  usability tests, benchmark an AI app against a baseline LLM, or run
  phase-specific project verification workflows with project-verifier.
---

# Project Verifier & Quality Suite

## Overview
This skill provides a comprehensive, 6-phase project quality verification and job interview evidence generation framework. It is designed to work with AI Coding Agents (such as Claude Code, Codex, Cursor Agent, Gemini CLI, etc.) to establish robust software testing structures and produce high-quality evidence packages for career development and interviews.

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
| Phase 2 | `phase2_flow_matrix.md` | P0/P1/P2 path matrix used by later tests and benchmarks. |
| Phase 3 | `phase3_test_plan.md`, `phase3_test_results.md` | Mock test plan, generated files, and actual run results. |
| Phase 4 | `phase4_usability_results.json` | Real usability path results, required env vars, exit codes, durations, logs, and failure stages. |
| Phase 5 | `phase5_benchmark_results.json` | Benchmark runner outputs with assertions and measurement boundaries. |
| Phase 6 | `phase6_interview_source_map.md` | Source map linking interview claims to workbench evidence and user Grill answers. |

Do not claim a quality, safety, cost, latency, or interview advantage unless it is backed by one of these artifacts or explicitly marked as not measured.

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
  │     ├── phase2_diagrams.md # Mermaid flowchart, architecture, & README update
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

### Phase 2: Visuals & Documentation (`workflows/phase2_diagrams.md`)
*   **Purpose**: Create user flow and technical architecture diagrams (Mermaid).
*   **Safety rule**: Original `README.md` is preserved. A copy is created at `README_updated_[Date]_[RandomID].md` with embedded diagrams.

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
