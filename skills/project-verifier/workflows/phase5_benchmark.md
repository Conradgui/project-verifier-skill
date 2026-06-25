# Phase 5: Benchmark & Automated Comparison (Evaluation)

## Purpose
Design and execute automated evaluations to quantitatively prove the value of your application compared to directly calling a raw LLM API (the baseline). This provides data-driven evidence of engineering value (e.g., increased reliability, better flow orchestration, state management, or cost controls).

---

## Instructions & Steps

### Step 1: Design the Benchmark Harness
Understand the three core modules of the benchmarking suite:
1.  **Tool Runner**: Runs the application on a specific task and records execution metrics (run time, exit code, outputs generated, API cost, logs created).
2.  **Baseline LLM Runner**: A standalone script that sends the raw task prompt directly to the LLM (using the same API key) in a single API call, bypassing all application code, tooling, or state tracking. It records response duration, response text, and token counts.
3.  **Evaluator**: Evaluates both outputs against AI-native and engineering dimensions (scored 0-10, with brief rationales):
    *   *Completeness*: Did the system complete all aspects of the task successfully?
    *   *Auditability*: Are there structured logs, records, or tracking history of what occurred?
    *   *Stability & Accuracy*: Did the process execute cleanly or did it fail/hallucinate?
    *   *Control & Safety Defensibility*: Did it operate within constraints (e.g. prompt injection guards, local directory sandbox boundaries)?
    *   *Token & Cost Efficiency (Cost-to-Value)*: Optimization ratio of API call volume or token usage compared to raw baseline.
    *   *Latency (P95/P99)*: Execution speed consistency and API request overhead optimizations.
    *   *User Experience / Diagnostics*: Are failure messages or output structures helpful to a human operator?

### Step 2: Propose Benchmark Tasks
Suggest 3 to 5 realistic benchmark tasks.
*   Define specific, repeatable task instructions (e.g., "Analyze this 10-line CSV file, find outliers, and generate a JSON summary").
*   Explain why the tool is expected to outperform the raw LLM (e.g., "The raw LLM cannot write files or check local directories, whereas the tool parses local system structure").
*   Explain how the Evaluator will score the results.

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

### Step 4: Write Benchmark Orchestrator
Generate `run_benchmark.sh` in the project root:
*   Sequentially executes the Tool Runner, Baseline Runner, and Evaluator for each task.
*   The Evaluator should support both rules-based metrics and LLM-as-a-Judge prompt grading (passing outputs to the LLM to rate semantic accuracy, safety, and leakage).
*   Outputs two report files:
    1.  A Markdown report `benchmarks/results/benchmark_report_[Date]_[RandomID].md` containing comparison tables, advantages summary, and a 3-sentence resume evidence pitch.
    2.  An interactive HTML dashboard `interview_evidence_pack/benchmark_radar.html` containing visual Chart.js radar graph plots rendering scores for all metrics (Completeness, Cost, Latency, Safety, Stability, UX, Auditability) for visual impact.

---

## Output Requirements
When completing Phase 5, output the results using this template:
```markdown
---
本阶段完成了 [X] 个 Benchmark 任务，
工具在 [维度A]、[维度B] 维度上显著优于裸模型（差距约 [X] 分），
在 [维度C] 维度上接近（说明原因）。

三个关键问题需要你确认：
① 这个结果和你对项目的预期是否符合？有没有让你意外的地方？
② 报告里的三句话结论，你觉得在面试中说出来是否自然、有说服力？
③ 有没有你想追加测试的任务场景？

如无异议，回复「继续」；如有修改，直接告诉我。
---
```
