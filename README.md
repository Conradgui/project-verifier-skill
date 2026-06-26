# AI-Agent Project Verifier & Evidence Builder

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)
[![Agent Compatibility](https://img.shields.io/badge/Agent_CLIs-Claude_Code_|_Codex_|_Gemini-purple.svg)](https://github.com/features/copilot)

> **为你的 AI 代理项目生成可复核、可解释、有边界的质量验证材料与面试证据。**

---

## 🌟 核心痛点：为什么你需要它？

在 AI-First 时代，构建一个基于大模型的 App 变得非常简单。但这给开发者带来了新的挑战：
1. **面试官的质疑**：“你这个项目是不是套壳？系统稳定性怎么保证？你真的懂架构设计吗？”
2. **非确定性系统的管理**：大模型（LLM）的输出是发散且不稳定的，传统的单元测试无法有效评估其边界、成本消耗与幻觉率。
3. **缺乏可量化的价值证据**：无法用数据直观证明“使用你的 Agent 系统”比“直接调用 OpenAI/Gemini 裸模型接口”到底强在哪里。

**AI-Agent Project Verifier** 是一个面向 AI 项目的验证 workflow skill。它通过**三层测试框架**与**定制化岗位 Grill 对齐机制**，帮助你沉淀审计、测试、Benchmark 和面试表达材料。它不会自动证明项目“足够好”，而是要求每个质量主张都能追溯到具体测试、日志或 workbench 证据。

---

## 🧭 6阶段项目质量与价值验证流

```mermaid
flowchart TD
    %% Node Definitions
    START([1. 全仓库探索与安全审计])
    DIAGRAMS[2. 流程/架构图与README更新]
    MOCK_TESTS[3. Mock 单元测试与 GHA CI]
    REAL_E2E[4. 真实 API 可用性测试]
    BENCHMARK[5. 自动化 Benchmark 对比评估]
    INTERVIEW[6. 目标岗位 Grill 与面试证据包]
    END([生成完整项目证据包])

    %% Connection Links
    START -->|安全绿灯| DIAGRAMS
    DIAGRAMS --> MOCK_TESTS
    MOCK_TESTS -->|CI 测试通过| REAL_E2E
    REAL_E2E --> BENCHMARK
    BENCHMARK --> INTERVIEW
    INTERVIEW --> END

    %% Subgraphs
    subgraph STAGE_QA["自动化质量护栏 (QA Shield)"]
        direction TB
        MOCK_TESTS
        REAL_E2E
    end

    subgraph STAGE_EVAL["价值评估与面试套件"]
        direction TB
        BENCHMARK
        INTERVIEW
    end

    %% Class Defs & Styling
    classDef main fill:#dbeafe,stroke:#3b82f6,color:#111827,stroke-width:2px
    classDef harness fill:#ede9fe,stroke:#8b5cf6,color:#111827,stroke-width:2px
    classDef success fill:#dcfce7,stroke:#22c55e,color:#111827,stroke-width:2px
    
    class START,DIAGRAMS main
    class MOCK_TESTS,REAL_E2E,BENCHMARK harness
    class INTERVIEW,END success
```

---

## 🛠️ 三层测试框架 (3-Tier Testing Architecture)

本套件采用分层测试思路，但每一层能证明的范围不同：

| 层级 | 测试类型 | 是否使用真实 API | 证明什么 (Proves What) |
| :---: | :--- | :---: | :--- |
| **L1** | **Mock 质量测试** | ❌ 使用 mock/VCR | **代码逻辑与边界行为**。适合低成本验证输入边界、异常传播和本地副作用。 |
| **L2** | **真实可用性测试** | ✅ 使用真实 API | **端到端（E2E）主流程是否跑通**。适合验证真实网络、模型 API 解析和文件写入行为。 |
| **L3** | **自动化 Benchmark 评测** | ✅ 使用真实 API | **特定任务上的相对表现**。只有被 runner JSON、断言、日志或 evaluator 证据覆盖的维度，才能作为优势主张。 |

所有阶段都会把关键证据写入目标项目的 `project_verification_workbench/`，后续阶段必须引用这些产物，而不是只依赖对话上下文。

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
# 一站式顺序运行 1-6 阶段
使用 $project-verifier 对当前项目运行 phase1-phase6 全流程验证与面试证据生成。

# 选择性运行某一阶段
使用 $project-verifier 对当前项目运行 phase1 只读探索和安全审计。
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
│           │     ├── phase2_diagrams.md # 阶段 2： Mermaid 图生成与 README 备份更新
│           │     ├── phase3_quality.md  # 阶段 3：VCR 录制、单元测试与 GitHub Actions
│           │     ├── phase4_usability.md# 阶段 4：真实 API 可用性测试
│           │     ├── phase5_benchmark.md# 阶段 5：LLM-as-a-Judge 与 HTML 看板评测
│           │     └── phase6_interview.md# 阶段 6：目标岗位 Grill 与面试证据包
│           └── templates/     # 评估器与测试运行器模板
│                 ├── benchmark_evaluator_template.py # Radar 图 HTML 生成器
│                 └── run_usability_template.sh       # 独立 E2E 测试脚本
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

bash -n bootstrap.sh
bash -n skills/project-verifier/templates/run_usability_template.sh

PYTHONPYCACHEPREFIX=/tmp/project-verifier-pycache \
  python3 -m py_compile \
    skills/project-verifier/templates/benchmark_evaluator_template.py \
    project_verifier_iteration_workbench/20260626_skill_hardening/template_behavior_tests.py
```

这些检查覆盖两类关键行为：Benchmark evaluator 不会在缺少证据时默认给高分；usability runner 会按 `.py`、`.sh`、`.ts` 脚本类型分发，并在缺少 TypeScript runtime 时给出清晰失败信息。

---

## 📊 成果展现：Benchmark 雷达图看板

在阶段 5 运行结束后，系统除了生成 Markdown 对比报告，还会在项目内输出静态可视化面板 `interview_evidence_pack/benchmark_radar.html`。双击即可在任何浏览器中打开。

### 生成的面试官证据包 (`interview_evidence_pack/`)
在最后一阶段，Agent 会基于你的目标岗位招聘需求（JD）、Grill 对齐内容和 `project_verification_workbench/` 证据，输出以下文档：
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
