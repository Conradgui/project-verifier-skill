# Phase 5: Guided AI Comparative Evaluation (L3 Benchmark)

## Purpose
For an AI or AI-assisted feature, propose realistic evaluation directions, help the user select a fair baseline and rubric, verify feasibility, and execute only when the environment and budget are authorized. This phase is not applicable to a non-AI project and never optimizes for attractive results.

---

## Instructions & Steps

### Step 0: Load Prior Evidence
Read these files before proposing Benchmark tasks:
*   `project_verification_workbench/verification_manifest.md`
*   `project_verification_workbench/phase2_flow_matrix.md`
*   `project_verification_workbench/phase3_test_results.md`
*   `project_verification_workbench/phase4_usability_results.json`

Phase 4 may legitimately be blocked or skipped. Preserve that state instead of treating missing live evidence as success. Set Phase 5 to `in_progress`.

### Step 1: Applicability Gate
Classify the project or selected feature as `AI / AI-assisted / non-AI / unknown` using Phase 1 evidence.

- `non-AI`: write a short `phase5_benchmark_plan.md` and `phase5_benchmark_results.json` with `status: not_applicable`; do not propose an LLM comparison.
- `unknown`: ask the user which user-facing behavior depends on model inference before continuing.
- `AI` or `AI-assisted`: continue only when there is a user-facing outcome and a meaningful comparative claim.

### Step 2: Propose Guided Evaluation Directions
Use project architecture, P0/P1/P2 flows, risks, and core value to propose 3 to 5 directions. Recommend 1 or 2; do not ask the user to design technical baselines unaided.

For every direction include:

- Scenario and linked path IDs.
- User value and the claim being tested.
- Agent-recommended baseline and why it is fair. It may be a raw LLM, prior version, no-RAG path, single-turn model, manual workflow, or alternate configuration.
- Repeatable inputs, assertions, required evidence, likely limitations, backend requirements, and estimated call count.
- Feasibility hypothesis and whether sensitive data is involved.

Offer these choices exactly: **Accept recommended set**, run all directions, select individual directions, add another idea, or skip Phase 5.

### Step 3: Clarify Selected Directions Only
For selected directions, ask only for missing information that changes the result: representative inputs, expected outcomes or ground truth, acceptable variation, sensitive-data restrictions, and maximum calls/retries/timeouts. Avoid making the user decide implementation details that the agent can infer.

### Step 4: Feasibility Gate and Durable Plan
Classify every selected direction as `ready_now / needs_setup / plan_only / rejected` after checking:

- Application entry point is callable and output can be captured.
- Inputs and assertions are repeatable.
- The selected baseline is runnable and comparable.
- Required environment variable names, backend services, and dependencies are known.
- Calls, retries, timeouts, side effects, and evidence storage are bounded.

Write `project_verification_workbench/phase5_benchmark_plan.md` with all candidates, selections, baselines, approved rubrics, feasibility, budget, blockers, and recovery conditions.

If a credential or backend is missing, show the exact blocker and ask whether the user wants guided repair or plan-only execution:

- Repair requested: mark Phase 5 `blocked` and pause without installing or reading secrets.
- Repair declined: write `phase5_benchmark_results.json` with `status: skipped`; do not generate runners, scores, or advantage claims.

### Step 5: Implement Approved Benchmark Harness
Only for `ready_now` directions and after file/dependency approval, write:

1.  **Directory Structure**:
    ```
    benchmarks/
      ├── tasks/         # Input definitions (e.g. task_BM_001.json)
      ├── tool_runner/   # Wrapper calling your tool
      ├── baseline/      # Scenario-specific approved baseline adapters
      ├── evaluator/     # Evaluation scoring script (rule-based or LLM-graded)
      ├── results/       # Output folder for raw results (Git ignored)
      └── run_benchmark.sh # Orchestrator script
    ```
2.  **Task Definition Contract**: Each `task_BM_*.json` must contain the scenario, linked paths, baseline type and label, inputs, assertions, and metric definitions. Every metric definition requires:
    *   `measurement_method`
    *   `success_threshold` as `{"operator": ">=", "value": 0.9}` or another explicit numeric rule
    *   `score_mapping`
    *   `minimum_samples`
    *   `evidence_fields`
3.  **Coding Guidelines**:
    *   Use project configurations and templates where appropriate.
    *   Reuse existing project clients and dependencies. Do not install a new SDK without approval.
    *   Implement robust exception handling. If the baseline or tool crashes, the benchmark runner must log it and continue rather than crashing.
    *   Tool output, baseline output, and task definition must use the same `task_id`. Runner outputs must declare the expected `runner_type`, `status: completed`, and `execution_mode: full` before they are eligible for scoring.
    *   LLM-as-a-Judge results must record `metric_id`, a 0-10 `score`, `evidence`, the complete `judge_prompt`, judge `model`, and `confidence`. Missing metadata means `not_measured`.
    *   Each runner output JSON must include at least:
        ```json
        {
          "task_id": "BM_001",
          "runner_type": "tool",
          "status": "completed",
          "execution_mode": "full",
          "exit_code": 0,
          "duration_seconds": 3.2,
          "artifacts_created": ["output/result.json"],
          "logs_created": true,
          "token_count": 1200,
          "assertions": [
            {
              "text": "Output JSON file exists",
              "passed": true,
              "evidence": "output/result.json",
              "tags": ["completeness"]
            }
          ],
          "control_evidence": [],
          "diagnostics": [],
          "errors": []
        }
        ```

### Step 6: Mandatory Preflight, Optional Pilot, and Full Run
Generate `run_benchmark.sh` in the project root:
*   Supports `preflight`, `pilot <task_id>`, and `full`. With no mode, print usage and make no live call.
*   `preflight` is mandatory and makes no real model or API call. It checks environment names, files, commands, task schemas, output directories, and runner wiring.
*   Recommend a one-sample real pilot only for new adapters, multi-step or side-effectful paths, or materially larger call budgets. The user may skip it after seeing the risk.
*   A pilot writes result `status: pilot_only`; it tests harness feasibility and cannot substitute for the complete benchmark or support full comparative claims. If the phase stops there, record Phase 5 as `skipped` in the manifest with `pilot_only` as the completed scope.
*   `full` sequentially executes approved Tool Runner, baseline, and evaluator tasks only after explicit authorization of maximum calls, retries, and timeouts.

### Step 7: Rubric-Backed Evaluation and Reports
*   The Evaluator should support both rules-based metrics and LLM-as-a-Judge prompt grading (passing outputs to the LLM to rate semantic accuracy, safety, and leakage).
*   LLM-as-a-Judge scores must be stored as evidence, not as unquestioned truth. Include judge prompt, model name, and confidence when used.
*   No approved rubric or evidence means `not_measured`, never a default numeric score.
*   A single run cannot prove stability. Calculate P95 only with at least 20 samples and P99 only with at least 100 samples in an explicitly approved repeated-performance mode; otherwise report observed durations without percentile claims.
*   Write a neutral Markdown report to `benchmarks/results/benchmark_report_[Date]_[RandomID].md` with measured results, negative or inconclusive findings, and limitations. Do not generate resume language here.
*   Generate `benchmarks/results/benchmark_radar.html` only when Tool and baseline both have at least three comparable numeric metrics backed by approved rubrics.
*   Never create `interview_evidence_pack/` in Phase 5.

Write `project_verification_workbench/phase5_benchmark_results.json` with:

```json
{
  "schema_version": "2.0",
  "status": "completed",
  "applicability": {"classification": "AI", "rationale": "...", "evidence": ["..."]},
  "preflight": {"passed": true, "checks": [], "errors": []},
  "execution_authorization": {"approved": true, "max_calls": 12, "max_retries": 1, "timeout_seconds": 60},
  "runs": [],
  "metrics": [],
  "limitations": [],
  "recovery_conditions": []
}
```

Update the manifest with the Phase 5 status and evidence boundaries.

### Step 8: Explicit Phase 6 Gate
At the end of Phase 5, whether completed, skipped, blocked, or not applicable, ask whether to enter Phase 6:

1. `需要` - enter the optional interview/presentation evidence workflow.
2. `不需要` - end the suite and retain all current artifacts.

Do not interpret a generic `继续` as consent to create interview materials.

---

## Output Requirements
When completing Phase 5, output the results using this template:
```markdown
---
Phase 5 manifest 状态：[completed / blocked / skipped / not_applicable / failed]。
Benchmark 执行状态：[not_run / pilot_only / completed / failed]。
[如完整执行] 完成了 [X] 个 Benchmark 任务，
已形成可复核结果：[已测维度列表]。
以下维度仍不能作为优势主张：[not_measured 维度列表及原因]。
[如未完整执行] 仅形成 Benchmark 计划或 pilot 诊断；未生成完整比较结论或优势主张。

三个关键问题需要你确认：
① 这个结果和你对项目的预期是否符合？有没有让你意外的地方？
② 选定基线和评分标准是否公平、符合真实用户价值？
③ 有没有你想追加测试的任务场景？

最后请选择：回复「需要」进入可选 Phase 6；回复「不需要」结束；或回复「修改」调整本阶段。
---
```
