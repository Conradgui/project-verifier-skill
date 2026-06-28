# Conditional Eval Gates Iteration Plan

## Goal

Refactor project-verifier into a three-tier verification workflow with risk-based
user gates, plan-only fallbacks for unavailable live environments, rubric-backed
AI evaluation, and an explicitly optional interview evidence phase.

## Verification Table

1. Add failing workflow and template contract tests -> verify current behavior fails.
2. Update the orchestrator and Phase 1-6 workflows -> verify conditional gates and artifacts.
3. Update the usability runner and benchmark evaluator -> verify no-call preflight and rubric scoring.
4. Update README and Codex metadata -> verify public documentation matches runtime behavior.
5. Run all regression checks -> record exact results in `verification_report.md`.

## Constraints

- Keep the repository, skill directory, skill name, and invocation name unchanged.
- Do not install dependencies or call real APIs.
- Never read, print, or write secret values.
- Do not update the installed copy under `~/.codex/skills/project-verifier`.
- Preserve negative and inconclusive benchmark outcomes.
