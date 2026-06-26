# Phase 5: Benchmark & Automated Comparison (Evaluation)

## Purpose
Design and execute automated evaluations that compare the application against a baseline while preserving measurement boundaries. This phase may support engineering value claims, but only for dimensions backed by runner outputs, assertions, logs, or explicit evaluator evidence.

---

## Instructions & Steps

### Step 0: Load Prior Evidence
Read these files before proposing Benchmark tasks:
*   `project_verification_workbench/phase2_flow_matrix.md`
*   `project_verification_workbench/phase3_test_results.md`
*   `project_verification_workbench/phase4_usability_results.json`

If any file is missing, mark the related evidence as unknown. Do not silently convert unknown maturity into a positive claim.

### Step 1: Design the Benchmark Harness
Understand the three core modules of the benchmarking suite:
1.  **Tool Runner**: Runs the application on a specific task and records execution metrics (run time, exit code, outputs generated, API cost, logs created).
2.  **Baseline LLM Runner**: A standalone script that sends the raw task prompt directly to the LLM (using the same API key) in a single API call, bypassing all application code, tooling, or state tracking. It records response duration, response text, and token counts.
3.  **Evaluator**: Evaluates both outputs against AI-native and engineering dimensions. Every metric must have `score`, `evidence`, `confidence`, and `not_measured_reason`:
    *   *Completeness*: Did the system complete all aspects of the task successfully?
    *   *Auditability*: Are there structured logs, records, or tracking history of what occurred?
    *   *Stability & Accuracy*: Did the process execute cleanly or did it fail/hallucinate?
    *   *Control & Safety Defensibility*: Did it operate within constraints (e.g. prompt injection guards, local directory sandbox boundaries)?
    *   *Token & Cost Efficiency (Cost-to-Value)*: Optimization ratio of API call volume or token usage compared to raw baseline.
    *   *Latency (P95/P99)*: Execution speed consistency and API request overhead optimizations.
    *   *User Experience / Diagnostics*: Are failure messages or output structures helpful to a human operator?

**Evidence rule**: A missing metric is `not_measured`, not a zero and not an assumed win. Never assign high safety, UX, cost, or latency scores without explicit evidence in the runner JSON.

### Step 2: Propose Benchmark Tasks
Suggest 3 to 5 realistic benchmark tasks.
*   Define specific, repeatable task instructions (e.g., "Analyze this 10-line CSV file, find outliers, and generate a JSON summary").
*   Define task assertions before writing code. Each assertion must state the evidence source and failure condition.
*   Explain why the tool might outperform the raw LLM, but label this as a hypothesis until measured.
*   Explain how the Evaluator will score the results and what will be marked `not_measured`.

**Ask the user to review the task set and answer the custom grill questions before writing code.**
```markdown
┌─────────────────────────────────────┐
│ 【需要你配合】                        │
│ 以上是我提议的 Benchmark 任务集。      │
│ 请告诉我：                            │
│ ① 有没有你最想展示但没有在列表里的场景？│
│ ② 有没有任务描述不够具体，需要我补充的？│
│ ③ 有没有你认为不合适或不想展示的任务？  │
│ 你的回答会直接影响 Benchmark 的质量。  │
└─────────────────────────────────────┘
```

### Step 3: Implement Benchmark Code
Upon user approval, write the files:
1.  **Directory Structure**:
    ```
    benchmarks/
      ├── tasks/         # Input definitions (e.g. task_BM_001.json)
      ├── tool_runner/   # Wrapper calling your tool
      ├── baseline/      # Raw LLM API caller script
      ├── evaluator/     # Evaluation scoring script (rule-based or LLM-graded)
      ├── results/       # Output folder for raw results (Git ignored)
      └── run_benchmark.sh # Orchestrator script
    ```
2.  **Coding Guidelines**:
    *   Use project configurations and templates where appropriate.
    *   Keep the Baseline LLM Runner lightweight, relying on basic HTTP libraries or standard official SDKs.
    *   Implement robust exception handling. If the baseline or tool crashes, the benchmark runner must log it and continue rather than crashing.
    *   Each runner output JSON must include at least:
        ```json
        {
          "task_id": "BM_001",
          "runner_type": "tool",
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

### Step 4: Write Benchmark Orchestrator
Generate `run_benchmark.sh` in the project root:
*   Sequentially executes the Tool Runner, Baseline Runner, and Evaluator for each task.
*   The Evaluator should support both rules-based metrics and LLM-as-a-Judge prompt grading (passing outputs to the LLM to rate semantic accuracy, safety, and leakage).
*   LLM-as-a-Judge scores must be stored as evidence, not as unquestioned truth. Include judge prompt, model name, and confidence when used.
*   Outputs two report files:
    1.  A Markdown report `benchmarks/results/benchmark_report_[Date]_[RandomID].md` containing comparison tables, advantages summary, and a 3-sentence resume evidence pitch.
    2.  An interactive HTML dashboard `interview_evidence_pack/benchmark_radar.html` containing visual Chart.js radar graph plots rendering scores for all metrics (Completeness, Cost, Latency, Safety, Stability, UX, Auditability) for visual impact.
    3.  A machine-readable summary `project_verification_workbench/phase5_benchmark_results.json` containing all runner outputs and evaluator results. Phase 6 must use this file as its source of truth.

---

## Output Requirements
When completing Phase 5, output the results using this template:
```markdown
---
本阶段完成了 [X] 个 Benchmark 任务，
已形成可复核结果：[已测维度列表]。
以下维度仍不能作为优势主张：[not_measured 维度列表及原因]。

三个关键问题需要你确认：
① 这个结果和你对项目的预期是否符合？有没有让你意外的地方？
② 报告里的三句话结论，你觉得在面试中说出来是否自然、有说服力？
③ 有没有你想追加测试的任务场景？

如无异议，回复「继续」；如有修改，直接告诉我。
---
```
