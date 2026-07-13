---
name: project-verifier
description: >-
  Use when a user needs evidence-backed project understanding, architecture or
  flow mapping, scoped quality or security verification, conditional live E2E,
  or a guided AI Benchmark with reproducible workbench artifacts.
---

# Project Verifier

使用四阶段、证据优先的项目理解与验证流程。优先使用已有确定性脚本；缺失证据、失败、空输出和未知项都必须保留，不能转化为正向主张。

## 核心规则

1. **脚本优先**：优先复用项目现有测试、lint、构建和 E2E 脚本。
2. **先理解，后执行**：Stage 1 只读分析并生成来源可追溯的项目理解材料。
3. **少而关键的用户决策**：用户决定目标、P0 路径、生产代码修改、安装、真实调用、成本、敏感数据、Baseline、指标与公开主张；其余可逆实现细节由 Agent 处理。
4. **高风险动作必须 Gate**：计划、源码 revision、授权 envelope 和执行上限不一致时拒绝执行；未回复不是批准。
5. **证据先于叙事**：面试或 README 主张必须引用当前 revision 的 workbench 证据。

始终提供：继续、修订、跳过可选项、停止并保留证据。

## 四阶段

1. [Stage 1：项目理解与 Profile Gate](workflows/stage1_understanding.md)
2. [Stage 2：质量、可运行性与授权 Live E2E](workflows/stage2_quality.md)
3. [Stage 3：项目适配的安全边界验证](workflows/stage3_security.md)
4. [Stage 4：条件式、证据优先的 AI Benchmark](workflows/stage4_benchmark.md)

Stage 1 是后续阶段的前置条件。Stage 2、3、4 均须拒绝未确认或过期的 Profile。Stage 4 仅用于存在可评测 AI / AI-assisted 功能且有明确比较决策的项目；非 AI 项目应标为 `not_applicable`。

## 控制面与产物

在 `project_verification_workbench/` 中维护 `verification_manifest.json`、`authorizations/*.json`、原始日志和各阶段结果。状态始终分开记录：`phase_status`、`result_outcome`、`execution_scope`、`claim_eligibility`。

默认人类阅读路径：`project_report.md`、`flow_matrix.md`、`quality_report.md`、`security_report.md`，以及条件生成的 `benchmark_report.md`。详细 schema 与证据边界见 [artifact contracts](references/artifact_contracts.md)；工具选择、替代方案和受信任 bridge 边界见 [tool adapters](references/tool_adapters.md)。

## 可选导出

README 优化副本需要单独确认。只有用户明确要求面试、答辩或作品集材料时，才加载 [可选证据导出](workflows/optional_interview_export.md)。它不生成新的原始证据，所有主张都需用户确认并引用当前 workbench。

## 不能证明什么

- 静态理解不是完整代码审计、渗透测试、合规认证或漏洞不存在证明。
- `preflight` 不执行目标、模型、API 或扫描。
- 测试通过率不是代码覆盖率；单次成功不是稳定性证明。
- 缺少遥测、空输出、非零退出或 pilot 不能形成完整 Benchmark 主张。
- LLM Judge 只能用于允许的质量类指标，不能单独证明安全、隐私或泄漏。
- 项目 executor 是显式授权的未隔离 bridge，不是 sandbox。
- 在授权的真实 Agent 行为 Eval 完成前，不声称模型会稳定遵守所有 Gate。
