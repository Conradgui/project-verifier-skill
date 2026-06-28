# AI-Agent Project Understanding & Verification Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)
[![Agent Compatibility](https://img.shields.io/badge/Agent_CLIs-Claude_Code_|_Codex_|_Gemini-purple.svg)](https://github.com/features/copilot)

> **帮助你理解项目结构、梳理架构与用户流程、看清安全/质量风险，并沉淀可复核的验证证据。**

---

## 🌟 核心痛点：为什么你需要它？

在 AI-First 时代，构建一个基于大模型的 App 变得非常简单，但理解、审计和解释一个项目仍然很难：
1. **新接手项目时看不懂结构**：入口、模块关系、外部依赖、用户路径和风险节点散落在代码里。
2. **需要系统化审计却缺少路径**：安全边界、异常处理、状态流转、API 成本风险很容易靠感觉判断。
3. **需要用图表和证据解释项目价值**：仅靠 README 或口头描述，很难让别人快速理解项目是如何工作的、哪里已经验证过、哪里还没有被证明。

**AI-Agent Project Verifier** 是一个面向软件项目的理解与验证 workflow skill。项目理解、审计和 L1/L2 适用于一般软件项目；L3 比较评测只适用于 AI / AI-assisted 功能。它不是完整 SaaS 平台，也不能替代真实测试和人工判断；它的价值是把“项目如何工作、风险在哪里、哪些结论有证据”固定成可阅读、可复核的文档。

---

## 🧭 条件式 6 阶段项目理解与验证流

```mermaid
flowchart TD
    START([1. 全仓库探索与安全审计])
    DIAGRAMS[2. 项目理解文档包与可选 README 副本]
    MOCK_TESTS[3. L1 离线 Mock Quality]
    E2E_GATE{4. L2 环境与执行授权}
    REAL_E2E[真实 E2E]
    E2E_PLAN[仅保存可恢复计划]
    EVAL_GATE{5. 是否为可评测 AI 功能}
    BENCHMARK[引导式 AI Comparative Eval]
    EVAL_PLAN[不适用或仅保存计划]
    INTERVIEW_GATE{是否需要 Phase 6}
    INTERVIEW[6. 面试或展示证据包]
    END([保留当前理解与验证证据])

    START -->|安全绿灯| DIAGRAMS
    DIAGRAMS --> MOCK_TESTS
    MOCK_TESTS --> E2E_GATE
    E2E_GATE -->|环境就绪且用户授权| REAL_E2E
    E2E_GATE -->|缺依赖或用户跳过| E2E_PLAN
    REAL_E2E --> EVAL_GATE
    E2E_PLAN --> EVAL_GATE
    EVAL_GATE -->|AI 或 AI-assisted| BENCHMARK
    EVAL_GATE -->|non-AI 或 plan-only| EVAL_PLAN
    BENCHMARK --> INTERVIEW_GATE
    EVAL_PLAN --> INTERVIEW_GATE
    INTERVIEW_GATE -->|明确需要| INTERVIEW
    INTERVIEW_GATE -->|不需要| END
    INTERVIEW --> END

    %% Subgraphs
    subgraph STAGE_UNDERSTAND["项目理解与架构梳理"]
        direction TB
        START
        DIAGRAMS
    end

    subgraph STAGE_QA["通用离线质量护栏"]
        direction TB
        MOCK_TESTS
    end

    subgraph STAGE_LIVE["条件式真实验证"]
        direction TB
        E2E_GATE
        REAL_E2E
        E2E_PLAN
        EVAL_GATE
        BENCHMARK
        EVAL_PLAN
    end

    subgraph STAGE_OPTIONAL["可选展示层"]
        direction TB
        INTERVIEW_GATE
        INTERVIEW
    end

    %% Class Defs & Styling
    classDef main fill:#dbeafe,stroke:#3b82f6,color:#111827,stroke-width:2px
    classDef harness fill:#ede9fe,stroke:#8b5cf6,color:#111827,stroke-width:2px
    classDef decision fill:#fef9c3,stroke:#ca8a04,color:#111827,stroke-width:2px
    classDef terminal fill:#f3f4f6,stroke:#6b7280,color:#111827,stroke-width:2px
    classDef success fill:#dcfce7,stroke:#22c55e,color:#111827,stroke-width:2px

    class START,DIAGRAMS main
    class MOCK_TESTS,REAL_E2E,BENCHMARK harness
    class E2E_GATE,EVAL_GATE,INTERVIEW_GATE decision
    class E2E_PLAN,EVAL_PLAN terminal
    class INTERVIEW,END success
```

Full Suite 默认完成 Phase 1–3。Phase 4 和 Phase 5 只有在适用、环境就绪且用户明确授权时才真实执行；Phase 6 永远是可选项。

---

## 🛠️ 三层测试框架 (3-Tier Testing Architecture)

本套件采用分层测试思路，但每一层能证明的范围不同：

| 层级 | 定位 | 适用范围 | 环境要求 | 无环境或用户跳过时 | 能证明什么 |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **L1 Mock Quality** | 离线代码质量测试 | 几乎所有代码项目 | 不需要真实 Key 或后端 | 正常执行 | 代码逻辑、输入边界、异常传播和本地副作用。 |
| **L2 Live Usability/E2E** | 条件式真实用户链路 | 有可运行产品入口的项目，不限 AI | 仅在项目真实依赖时需要 Key、数据库或服务 | 生成 `plan-only` 可恢复计划，不调用真实服务 | 当前真实环境中的主流程是否跑通。 |
| **L3 AI Comparative Eval** | AI 功能相对合理基线的比较评测 | 仅 AI / AI-assisted 且存在可比较主张的项目 | 可运行推理后端、批准的 rubric 和调用预算 | 生成场景与计划，不评分、不伪造优势 | 特定任务和批准指标上的相对表现。 |

L2/L3 的无调用 preflight 用来检查 runner、环境变量名称和输出 schema，不执行真实测试。真实 Smoke 只在高风险场景推荐，结果标记为 `pilot_only`，不能替代完整 Benchmark。

所有阶段都会把关键证据和状态写入 `project_verification_workbench/`。`verification_manifest.md` 使用 `pending / in_progress / completed / blocked / skipped / not_applicable / failed` 跟踪阶段，并保存用户授权、阻塞项与恢复条件。

---

## 📦 它会生成什么？

这个 skill 会生成四类互相独立、但可以互相引用的产物：

| 产物 | 默认位置 | 用途 |
|---|---|---|
| **项目理解文档包** | `project_verification_workbench/project_understanding/` | 面向人阅读，帮助用户理解项目是什么、入口在哪里、模块如何协作、用户如何使用、风险节点在哪里。 |
| **验证 workbench** | `project_verification_workbench/phase*_*.md/json` | 面向后续阶段引用，保存审计、流程矩阵、测试计划、真实可用性结果、Benchmark 结果和面试证据来源。 |
| **README 优化副本** | `README_updated_[Date]_[RandomID].md` | Phase 2 中由用户选择后生成；它不是项目理解文档包本身。 |
| **面试/展示证据包** | `interview_evidence_pack/` | 仅在用户明确进入可选 Phase 6 后生成，基于 workbench 证据和用户 Grill 回答形成岗位化叙事材料。 |

四类产物的关系是：`project_verification_workbench/` 是证据源，`project_understanding/` 是项目理解层，`README_updated_*` 是公开表达层，`interview_evidence_pack/` 是岗位/展示叙事层。面试证据包必须引用 workbench，不能凭空生成成果主张。

项目理解文档包固定包含：

```text
project_verification_workbench/project_understanding/
├── project_understanding_report.md
├── architecture_diagrams.md
├── user_flows.md
└── flow_matrix.md
```

面试/展示证据包在用户明确选择 Phase 6 后包含：

```text
interview_evidence_pack/
├── narrative_scripts.md
├── product_decisions.md
├── verification_evidence.md
├── architectural_evolution.md
└── benchmark_radar.html  # 仅当 Phase 5 有至少三个可比、rubric-backed 数字维度
```

---

## ⚡ 快速开始 (Quick Start)

### 方式 1：把仓库地址发给 Codex 安装（推荐）

在 Codex 中直接发送：

```text
请安装这个 Codex skill 仓库：
https://github.com/Conradgui/project-verifier-skill.git
```

Codex 应识别本仓库内的 skill 路径：

```text
skill path: skills/project-verifier
invoke name: $project-verifier
```

如果 Codex 需要手动安装命令，可以使用：

```bash
python3 /Users/conrad/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/Conradgui/project-verifier-skill/tree/main/skills/project-verifier
```

安装后重启 Codex，让新 skill 被重新发现。

### 方式 2：本地软链接安装

如果你已经克隆本仓库，也可以运行根目录下的 `bootstrap.sh`，将 `skills/project-verifier` 软链接到本机 Agent CLI 的 skill 目录。建议先 dry run 查看计划：

```bash
chmod +x bootstrap.sh

./bootstrap.sh codex --dry-run
./bootstrap.sh codex

# 或链接至已检测到的多个 Agent CLI skill 目录
./bootstrap.sh all --dry-run
./bootstrap.sh all
```

### 方式 3：召唤 Agent 运行验证

部署完成后，在你的 AI 编程终端（如 **Codex** 或 **Claude Code**）中，对目标项目执行：

```text
# 条件式 Full Suite：1-3 为核心，4-5 按环境和授权执行，6 需明确选择
使用 $project-verifier 对当前项目运行条件式全流程项目理解、审计与验证，并在每个真实调用或可选产物前向我确认。

# 选择性运行某一阶段
使用 $project-verifier 对当前项目运行 phase1 只读探索和安全审计。
使用 $project-verifier 的 phase2 为当前项目生成项目理解报告、架构图、用户流程图和流程矩阵。
使用 $project-verifier 的 phase3 为当前项目生成 mock 测试和 GitHub Actions 配置。
```

---

## 📂 技能模块结构

```
.
├── AGENTS.md                  # Codex 仓库级安装识别说明
├── bootstrap.sh               # 本地软链接安装脚本
├── skills/
│     └── project-verifier/
│           ├── SKILL.md       # 技能总控（Main Orchestrator）
│           ├── agents/
│           │     └── openai.yaml # Codex UI 元数据与默认调用提示
│           ├── workflows/     # 每个验证阶段的独立 Workflow 配置文件
│           │     ├── phase1_explore.md  # 阶段 1：只读源码探索与安全审计
│           │     ├── phase2_diagrams.md # 阶段 2：项目理解文档包、Mermaid 图与 README 备份更新
│           │     ├── phase3_quality.md  # 阶段 3：离线 Mock、单元测试与 GitHub Actions
│           │     ├── phase4_usability.md# 阶段 4：条件式真实 E2E
│           │     ├── phase5_benchmark.md# 阶段 5：引导式 AI 比较评测
│           │     └── phase6_interview.md# 阶段 6：可选目标岗位与展示证据包
│           ├── templates/     # 评估器与测试运行器模板
│           │     ├── benchmark_evaluator_template.py # Radar 图 HTML 生成器
│           │     └── run_usability_template.sh       # 独立 E2E 测试脚本
│           └── evals/
│                 └── evals.json # 六类条件流程行为评测提示
├── CONTRIBUTING.md            # 开源贡献指南
├── LICENSE                    # MIT 开源许可证
└── README.md                  # 本文档
```

---

## ✅ 开发者验证

提交 PR 或修改模板后，建议至少运行以下检查，确保核心模板行为没有回退：

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-pycache \
  python3 project_verifier_iteration_workbench/20260626_skill_hardening/template_behavior_tests.py

PYTHONPYCACHEPREFIX=/tmp/project-verifier-pycache \
  python3 project_verifier_iteration_workbench/20260628_conditional_eval_gates/workflow_contract_tests.py

bash -n bootstrap.sh
bash -n skills/project-verifier/templates/run_usability_template.sh

PYTHONPYCACHEPREFIX=/tmp/project-verifier-pycache \
  python3 -m py_compile \
    skills/project-verifier/templates/benchmark_evaluator_template.py \
    project_verifier_iteration_workbench/20260626_skill_hardening/template_behavior_tests.py \
    project_verifier_iteration_workbench/20260628_conditional_eval_gates/workflow_contract_tests.py
```

这些检查覆盖条件阶段门、Phase 6 opt-in、rubric-backed 评分、pilot 边界、无调用 preflight，以及 `.py`、`.sh`、`.ts` runner 分发。

---

## 📊 条件式 Benchmark 雷达图

Phase 5 完整执行且双方至少有三个可比、预先批准评分标准的数字维度时，系统才会生成 `benchmarks/results/benchmark_radar.html`。指标不足时只输出 Markdown 结果，不用空缺或推测分数凑图。

### 生成的面试官证据包 (`interview_evidence_pack/`)
用户明确选择 Phase 6 后，Agent 才会基于目标岗位招聘需求（JD）、Grill 对齐内容和 `project_verification_workbench/` 证据输出以下派生材料：
*   **`narrative_scripts.md`**：30秒、2分钟、5分钟的自我介绍与项目陈述话术。
*   **`product_decisions.md`**：系统架构的关键技术折衷选择（Trade-offs）与裁剪范围记录。
*   **`verification_evidence.md`**：可复核的自动化测试结果、Benchmark 量化指标，以及尚未被证明的边界。
*   **`architectural_evolution.md`**：项目演进路径、现有技术债与重构路线图。

---

## 🤝 参与贡献 (Contributing)

我们非常欢迎社区提交 Pull Request 或 Issue 来优化该技能模版！请在提交 PR 前查阅 [CONTRIBUTING.md](CONTRIBUTING.md) 以获取开发指南与规范。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 许可开源。
