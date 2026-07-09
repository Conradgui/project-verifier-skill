# Contributing to Project Verifier

Thank you for your interest in contributing to Project Verifier. This repository
contains a Codex-compatible workflow skill, not a standalone SaaS product.

## How to Contribute

### 1. Reporting Bugs & Suggesting Enhancements
*   Please search the issue tracker first to ensure the topic hasn't been discussed yet.
*   If you find a bug, open an issue explaining the steps to reproduce, actual behavior, expected behavior, and the affected file or phase.
*   If you want to suggest a feature, explain the user decision it improves and the evidence boundary it preserves.

### 2. Submitting Pull Requests
*   Fork the repository and create your branch from `main` or `dev`.
*   If you've added new features, update the corresponding workflow instruction file in `skills/project-verifier/workflows/`.
*   If you change user-facing behavior, update `README.md`, `skills/project-verifier/SKILL.md`, and `skills/project-verifier/agents/openai.yaml` when their claims would otherwise drift.
*   Ensure all Markdown links match local directory relative offsets cleanly.
*   Write clear, descriptive commit messages.
*   Submit your pull request and describe your changes.

## Development Setup

The skill relies on Python standard-library scripts and standard Unix/Mac shell
environments. The offline validation suite intentionally avoids third-party
packages and secrets.

1.  Verify Python 3.10+ is installed.
2.  Run the current offline checks before submitting behavior changes:

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-pycache \
  python3 project_verifier_iteration_workbench/20260626_skill_hardening/template_behavior_tests.py
PYTHONPYCACHEPREFIX=/tmp/project-verifier-pycache \
  python3 project_verifier_iteration_workbench/20260628_conditional_eval_gates/workflow_contract_tests.py
PYTHONPYCACHEPREFIX=/tmp/project-verifier-pycache \
  python3 project_verifier_iteration_workbench/20260629_stage_gate_quality_v2/stage_gate_v2_tests.py
PYTHONPYCACHEPREFIX=/tmp/project-verifier-pycache \
  python3 project_verifier_iteration_workbench/20260630_lean_core_simplification/lean_core_contract_tests.py
```

These scripts currently cover 66 offline checks across template behavior,
workflow contracts, gate validation, evaluator behavior, and the optional Codex
Hook classifier.

## Coding Conventions
*   Keep the core skill instructions (`SKILL.md` and `workflows/*.md`) highly structured with explicit step instructions for the LLM agents.
*   For Python scripts, use standard libraries where possible to limit the installation overhead for users running the verification suite.
*   For script outputs, prioritize writing JSON output to files rather than stdout to keep the agent's context window token-efficient.
*   Do not convert test pass rate into code coverage, and do not turn missing or empty outputs into positive claims.
*   Keep deleted scope deleted: no user-operation replay, production browser operation, multi-host Hook platform claims, universal score, or radar chart.

## License
By contributing, you agree that your contributions will be licensed under the project's MIT License.
