# Phase 6: Job Role Alignment & Interview Evidence Pack

## Purpose
Synthesize all verification data, code audits, and architectural details into high-value professional assets. This phase customizes pitches, trade-off logs, and evidence summaries to align with a specific job description and target role.

This phase is optional. Do not create `interview_evidence_pack/` unless the user explicitly opted in at the Phase 5 gate or explicitly requested Phase 6 in Selective Phase Mode.

> [!IMPORTANT]
> **核心原则：去“AI味”黑话，建“工程证据链”**
> 面试官极度反感空泛的大模型黑话堆砌（如盲目排列 `RAG`、`Agent`、`DAG`、`Embedding` 等词）。本阶段生成的所有材料必须**少写抽象名词，多写具体判断；少写流程参与，多写“为什么这么做”；突出具体 Bad Case 及其调试定位细节。**

---

## Instructions & Steps

### Step 0: Confirm Opt-In and Load Verification Evidence
Confirm that the user explicitly opted in. If they decline, set Phase 6 to `skipped` in `verification_manifest.md`, create no interview files, and end.

Read the workbench evidence before asking for role/JD:
*   `project_verification_workbench/phase1_audit.md`
*   `project_verification_workbench/phase2_flow_matrix.md`
*   `project_verification_workbench/phase3_test_results.md`
*   `project_verification_workbench/phase4_usability_results.json`
*   `project_verification_workbench/phase5_benchmark_results.json`

If an artifact is missing, blocked, skipped, pilot-only, or not applicable, preserve that boundary. Missing evidence cannot be converted into an interview claim.

The interview evidence pack is a derived presentation layer, not a new source of truth. Every strong outcome, quality, safety, benchmark, or architecture claim must be traceable to `project_verification_workbench/phase6_interview_source_map.md` or one of the prior phase artifacts listed above.

### Step 1: Request Target Role & JD
Ask for the target use (interview, defense, or portfolio), target role, and optional Job Description (JD).

Do not silently select a generic role. If no JD or role is provided, ask whether the user wants a clearly labeled general presentation mode or wants to stop. External role research also requires user consent; otherwise align only to the provided material.

### Step 2: Interactive "Grill" Session
Before generating any files, present the user with 3 or 4 targeted questions to align on the core project narrative. The questions must force the user to unpack their specific decision logic and hands-on work:
1.  **语料/流程标准是如何制定的？** (这些标准对应了什么上游的产品判断或算法需求？为什么选择这批数据/执行路径？)
2.  **你在手动调试或自动化验证中，踩过最深的工程坑或捕获过什么 Bad Case？** (你是如何定位并用代码/用例修复它的？最后沉淀了什么经验？)
3.  **使用你的验证和修复后，下游系统或最终模型的实际效果有没有变好？** (怎么变好的？是否形成了一个“需求 -> 执行 -> 闭环反馈”的业务回路？)

**Wait for the user's answers to the Grill questions before writing files. Do not proceed to Step 3 automatically.**

### Step 3: Generate Evidence Pack Files
Create a folder named `interview_evidence_pack/` in the project root. Generate the following four Markdown files:

#### 1. `narrative_scripts.md` (Elevator Pitches)
Generate three versions of job narratives (30-second, 2-minute, and 5-minute pitches). Apply these strict formatting rules:
*   **No Jargon Stacking**: Do not list tools or libraries. Every sentence must have high information density.
*   **Replace Abstract with Concrete**:
    *   *Bad*: "我参与并使用 LangChain 建立了 Agentic 工作流进行多步骤编排测试。"
    *   *Good*: "在评测第一轮 Bad Case 时，我发现模型在多步执行中容易丢失上下文。因此，我增加了状态回溯和显式超时，并用回归日志记录修复前后的失败路径；只有实测数据存在时才填写改善比例。"
*   **Decision-Oriented**: Write "I decided to do X because..." instead of "I participated in Y process."

#### 2. `product_decisions.md` (Trade-off & Scope Log)
Format as a detailed markdown table representing engineering decisions. Focus on *logic trade-offs*, not just implementation steps:
*   *Alternative A vs. Alternative B* (e.g. "Rule-based evaluator vs. LLM-as-a-judge").
*   *Why the decision was made*: Explain the trade-off (e.g. latency vs. semantic accuracy).
*   *Scope Cuts*: What features or tests were deliberately left out, and how that represents strong focus on core value.

#### 3. `verification_evidence.md` (Testing & Benchmark Proofs)
Compile a summary of:
*   Mock testing coverage results.
*   Usability E2E success metrics.
*   Automated Benchmark outcomes. Frame only measured metrics as value claims. For missing or not-measured dimensions, explicitly say they are not yet proven.
*   Include a "Source Map" table linking each claim to the exact workbench artifact and line/section when available.

#### 4. `architectural_evolution.md` (System Design & Tech Debt)
*   Describe how the codebase evolved from a loose script to a robust modular application.
*   Document existing technical debt and outline a roadmap of what would be refactored next if given more time.

#### 5. Workbench Source Map
Write `project_verification_workbench/phase6_interview_source_map.md` with:
*   User-provided role/JD summary.
*   User Grill answers.
*   Claims used in the evidence pack.
*   The workbench artifact backing each claim.
*   Claims deliberately excluded because evidence was missing or weak.

If `benchmarks/results/benchmark_radar.html` exists and Phase 5 confirms at least three comparable rubric-backed metrics, copy or reference it as `interview_evidence_pack/benchmark_radar.html`. Otherwise state that no defensible radar chart is available and do not fabricate one.

---

## Output Requirements
Upon completion, output the confirmation to the user using this template:
```markdown
---
本阶段已在项目根目录生成面试证据包：
📁 [interview_evidence_pack/](file:///absolute/path/to/project/interview_evidence_pack/)
  ├── [narrative_scripts.md](file:///absolute/path/to/project/interview_evidence_pack/narrative_scripts.md)
  ├── [product_decisions.md](file:///absolute/path/to/project/interview_evidence_pack/product_decisions.md)
  ├── [verification_evidence.md](file:///absolute/path/to/project/interview_evidence_pack/verification_evidence.md)
  └── [architectural_evolution.md](file:///absolute/path/to/project/interview_evidence_pack/architectural_evolution.md)

三个关键问题需要你确认：
① 话术脚本中提炼的项目价值是否去除了“空泛黑话”，是否符合你的个人表达风格？
② 决策与折中记录是否体现了你希望展现的核心决策能力？
③ 验证证据中的数据指标是否能有力支撑你的项目成果陈述？

请选择：回复「完成」结束流程；回复「修改」调整面试包；或回复「停止」并保留当前产物。
---
```
