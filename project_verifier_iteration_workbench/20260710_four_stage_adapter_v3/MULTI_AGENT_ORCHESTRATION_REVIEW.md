# Multi-Agent Orchestration Review

Date: 2026-07-10
Status: Research complete; addendum approved and integrated

## Question

How should Project Verifier execute implementation plans when subagents are available, fall back when they are not, decide between serial and parallel work, and prevent context drift between agents?

## Finding

Use subagents by default, but use **serial implementation** by default. Parallelism is an exception for genuinely independent, disjoint work.

The current eight-task V3 plan is a dependency chain and repeatedly touches shared contracts such as `test_contract.py`, adapter references, the manifest, and Skill documentation. Running implementation agents in parallel would create conflicting assumptions and merge risk. The useful role of subagents here is fresh task context plus independent review, not maximum concurrency.

## Recommended Execution Backends

### Primary: `subagent_serial`

1. The controller reads the approved plan and global constraints.
2. It dispatches one fresh implementer for the next ready task.
3. The implementer writes only within its declared ownership, runs targeted tests, self-reviews, and writes a structured report.
4. The controller verifies the actual diff and test evidence.
5. A fresh reviewer checks both specification compliance and code quality.
6. Critical or important findings return to a fixer and then to re-review.
7. Only a clean task advances the dependency graph.
8. A final capable reviewer checks the complete branch.

### Fallback: `inline_serial`

If the host has no subagent tools, dispatch fails, or the available agent cannot safely own the required files, the controller executes the same task brief itself. It uses the same tests, report, ledger, and review checklist.

The fallback must record `review_independence: self_review_only` when no independent reviewer exists. It must not describe self-review as an independent subagent review.

### Mode Detection

- Detect subagent capability before Task 1.
- Do not ask the user to choose again when falling back does not change scope, cost limits, permissions, or result interpretation.
- Record backend, reason, and transition in the progress ledger.
- Never restart a completed task after a backend switch.
- Stop for the user only when the fallback materially reduces an approved quality boundary or requires a new cost/risk decision.

During the 2026-07-10 design review, the active Codex session exposed `spawn_agent`, `send_input`, `wait_agent`, and `close_agent`. The production Skill must still detect capability on every run; this observation is historical evidence, not a permanent availability promise.

## Scheduling Rule

Build a small dependency graph from the plan. A write task may run in parallel only when all conditions are true:

1. no dependency edge exists between the tasks;
2. write sets are disjoint;
3. neither task changes a shared contract, fixture, schema, manifest, or test entrypoint;
4. each task has an isolated workspace or is read-only;
5. integration order and owner are defined before dispatch;
6. failure in one task cannot change the other's expected behavior.

If any condition is unknown, schedule serially.

For the current V3 plan, the following is the approved safe serial order. Some edges enforce integration ownership rather than a functional data dependency:

```text
Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6 -> Task 7 -> Task 8
```

Tasks 5 and 6 look domain-independent, but both modify `tool_adapters.md` and `test_contract.py`; they remain serial unless their shared ownership is redesigned first. That redesign is not justified for an eight-task personal project.

Parallel work remains appropriate for read-only source research, independent fixture inspection, or isolated verification commands that use separate temporary directories.

## Controller and Role Boundaries

### Controller

- owns the approved plan, dependency graph, user communication, and integration;
- is the only role allowed to ask the user for material decisions;
- creates task briefs and validates reports against actual Git/test evidence;
- does not let one subagent's summary become evidence for another task without a file or diff reference;
- never delegates push, merge, dependency installation, real API calls, active scans, or other separately authorized actions.

### Implementer

- receives one task brief, global constraints, prior interfaces needed by that task, allowed files, and forbidden actions;
- does not read the entire conversation or accumulated task history;
- follows TDD where behavior changes;
- reports `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`;
- does not broaden scope, revert other work, or modify files outside ownership.

### Reviewer

- receives the task brief, implementer report, and actual diff/review package;
- is read-only unless separately dispatched as a fixer;
- returns two explicit verdicts: `spec_compliance` and `code_quality`;
- does not trust the implementer's success statement without evidence;
- marks unverifiable requirements separately instead of treating them as passing.

### Fixer

- receives the complete finding set for one review cycle;
- changes only files needed for those findings;
- reruns covering tests and appends evidence to the task report;
- returns to the same reviewer contract.

## File-Based Communication Contract

Subagents should not freely converse with each other. The controller is the hub, and durable files are the shared state.

```text
project_verification_workbench/agent_execution/
├── execution_manifest.json
├── progress.md
├── task-01-brief.md
├── task-01-report.md
├── task-01-review.md
└── review-packages/
```

### Task Brief

Required sections:

- `task_id`
- objective and place in the dependency graph
- exact requirements and acceptance tests
- allowed write paths
- forbidden actions
- consumed interfaces and source revision
- expected output/report path

### Implementer Report

Required sections:

- status
- source revision before and after
- files changed
- interfaces added or changed
- tests with command, exit code, and concise result
- self-review findings and corrections
- concerns, unknowns, and blockers
- evidence paths needed by the next task

### Review Report

Required sections:

- `spec_compliance: approved | changes_required | cannot_verify`
- `code_quality: approved | changes_required | cannot_verify`
- findings ordered by severity with file/line evidence
- tests or evidence inspected
- requirements not verifiable from the task diff
- re-review result after fixes

### Progress Ledger

One line per state transition:

```text
Task 2: complete (base abc1234, head def5678, backend subagent_serial, review approved)
```

The ledger is the resume source after context compaction or backend failure. Git and test output remain higher-authority evidence than agent prose.

## Borrowed Patterns

### Superpowers

Adopt directly:

- fresh implementer per task;
- task brief and report files rather than full conversation inheritance;
- implementer status protocol;
- task-level spec and quality review;
- review/fix/re-review loop;
- durable progress ledger and final whole-branch review.

Source: https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md

### AutoGen GraphFlow

Borrow only the directed-graph scheduling idea: sequential, parallel, conditional, and loop edges should be explicit rather than decided by informal agent conversation.

Source: https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/graph-flow.html

### MetaGPT

Borrow the SOP principle: roles observe upstream artifacts and publish structured downstream artifacts. Do not import its software-company role hierarchy or runtime.

Source: https://github.com/geekan/MetaGPT-docs/blob/main/src/en/guide/tutorials/multi_agent_101.md

### OpenAI Agents SDK

Borrow typed handoff metadata, context filtering, and trace identity. Keep stable project state outside handoff messages, pass only task-local inputs, and record role transitions. Do not add the SDK as a dependency.

Its documentation also shows why Project Verifier cannot rely on a first/last guardrail alone: handoff input guardrails apply to the first agent and output guardrails to the final agent, so each high-risk tool/action still needs Project Verifier's own Gate.

Sources:

- https://github.com/openai/openai-agents-python/blob/main/docs/handoffs.md
- https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md

### LangGraph

Borrow durable execution, persisted state, resume, and human-in-the-loop concepts. Do not add LangGraph: this personal Skill does not need a long-running production agent runtime.

Source: https://github.com/langchain-ai/langgraph

## Rejected Approaches

- **Free-form agent group chat:** difficult to audit, duplicates context, and lets assumptions become shared facts.
- **Parallel implementation by default:** conflicts with shared files and dependency ordering.
- **One long-lived implementer:** accumulates context drift and weakens independent review.
- **Framework installation:** adds dependencies and operational complexity without improving this repository's core evidence contract.
- **User approval for every agent transition:** increases friction without changing risk or interpretation.
- **Silent fallback:** hides the loss of independent review and undermines credibility.

## Proposed V3 Addendum

After user approval, add these requirements to `DESIGN.md` and `IMPLEMENTATION_PLAN.md`:

1. subagent-first capability detection with inline fallback;
2. serial-by-default DAG scheduling and the six-condition parallel gate;
3. controller-only user communication;
4. task brief, report, review, and progress-ledger contracts;
5. explicit review-independence disclosure;
6. no new multi-agent framework dependency;
7. no repeated user confirmation for non-material backend switches.

This addendum changes orchestration quality, not the four-stage Project Verifier product model.
