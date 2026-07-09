# Project Verifier Lean Roadmap

## 审查结论

Project Verifier 的核心功能已经完整：

- 五阶段项目理解与验证流程；
- 架构图、用户流程和流程矩阵；
- 离线测试与条件式真实 E2E；
- AI / AI-assisted 场景化 Eval；
- revision-bound 授权、preflight、遥测和失败状态；
- 可选 README 与面试证据导出；
- 可选 Codex Hook。

后续不再以增加功能为主。当前真正需要完成的是“公开版本闭环”：让仓库、CI、实际 Agent 行为和本机安装版本保持一致。

## 上一版 Roadmap 的删减决定

| 原计划 | 审查后决定 | 原因 |
|---|---|---|
| 全链路 Skill/Runner/Hook 哈希和授权过期 | 移为按需增强 | 适合安全执行平台，不应成为普通 workflow Skill 的发布前置条件。当前先准确声明边界。 |
| 四级遥测信任体系 | 简化为两类 | 只区分 wrapper enforced 与 script self-reported 即可。 |
| Benchmark evidence contract v3 | 只保留 rubric 批准检查 | 当前 raw-first、样本量和文件证据能力已经够用，不再扩展复杂 schema。 |
| 搬迁全部测试到 `tests/` | 暂缓 | 现有 66 项测试可直接运行，迁移不增加用户价值。 |
| SECURITY、Issue templates、CHANGELOG、CODEOWNERS 全套治理 | 只修 CONTRIBUTING | 小型 pre-1.0 项目无需一次性复制成熟基金会流程。 |
| 七类真实 Hook 合同测试 | 缩为一次最小 host smoke | Hook 是可选实验能力，不应拖住核心 Skill 发布。 |
| 12 次新旧 Agent 对照 | 缩为 3 个代表场景 | 当前目标是确认流程可用，不做统计性模型优越性声明。 |
| 两套 golden 项目 | 暂缓 | 已有六类 fixtures；只有用户仍看不懂产物时再增加。 |
| doctor、完整 schema 迁移、workbench 索引 | 按需 | 等真实安装或兼容问题出现后再做。 |
| 产品反馈指标体系 | 省略 | 当前没有足够用户规模，不应提前建设度量体系。 |

## P0：发布闭环

### 1. 文档体系与可信度口径校准

由于本轮已经从六阶段收敛为五阶段，并移除了回放、多宿主强制模式、通用评分和雷达图，发布前必须同步检查整个现行文档体系：

- `README.md`：五阶段流程、默认产物、可选导出、已删除能力、Hook 状态和测试边界；
- `skills/project-verifier/SKILL.md`：阶段路由、artifact contract、用户决策点和可信度边界；
- `workflows/*.md`：不得残留 Phase 6、回放、雷达图或旧产物路径；
- `agents/openai.yaml`：默认提示必须与五阶段和 optional export 一致；
- `CONTRIBUTING.md`：使用当前 66 项离线测试和无第三方依赖的真实开发命令；
- `optional/codex-hook/README.md`：明确 optional experimental、Codex-only、pattern-based 和非 sandbox；
- `AGENTS.md`：只核对仓库、Skill 路径和调用名，不加入重复的功能说明。

同时统一以下可信度口径：

- calls/retries 来自项目脚本时属于 self-reported，不宣称 wrapper 已强制限制；
- Codex Hook 未完成真实 host smoke 前保持 experimental；
- 测试通过率不等于代码覆盖率；
- preflight、pilot 和 plan-only 不等于真实 Benchmark；
- 已删除功能不得继续出现在安装示例、目录树、产物表或贡献指南中。

历史 iteration workbench 作为过程证据保留，不批量改写旧结论；若仍可能被误认为现行设计，只增加 `superseded` 指向当前 Roadmap。

同时给 Evaluator 增加一个小型硬检查：只有 task 明确包含 `rubric_approved: true` 才进行指标计算，否则返回 `not_measured`。

**完成标准：** README、SKILL、workflow、OpenAI 提示、CONTRIBUTING、Hook 文档和实际实现口径一致；全仓现行文档扫描不存在旧阶段、旧产物和已删除功能引用；现有测试和新增 rubric 回归测试通过。

### 2. 添加最小离线 CI

增加一个 GitHub Actions workflow，直接运行现有命令：

- 66 项离线测试；
- Shell 语法检查；
- Python 编译和 JSON 解析；
- Skill validator；
- `git diff --check`。

不迁移测试目录、不安装第三方包、不运行真实 API。

**完成标准：** clean clone 在无密钥环境下 CI 全绿。

### 3. 最小真实行为复核

在明确模型调用次数和成本并获得授权后，只运行三个代表场景，各一次：

1. non-AI CLI：不应进入 AI Eval；
2. AI 缺少凭据：只能生成 plan，不得调用 API；
3. stale authorization：源码变化后必须拒绝执行。

不做旧版/新版 12 次统计对照，也不据此声称“所有 Agent 稳定遵守”。

Codex Hook 若准备随本次版本公开，只额外做一次真实 host smoke：一个安全读取应放行，一个缺少 receipt 的高风险动作应在执行前拒绝。若暂不授权安装，则在 README 中保持 experimental/未完成 host validation 状态，不阻塞核心 Skill。

**完成标准：** 三个 Agent 输出和原始日志可复核；任何未授权调用、写入或虚假成果主张都阻止发布。

### 4. GitHub 与本机版本同步

1. 复核并提交当前 staged 变更；
2. 通过 PR 或明确的分支合并方式进入 `main`；
3. 推送并确认远程 README 与 Skill 路径；
4. 使用发布后的 `skills/project-verifier` 更新本机旧安装；
5. 比对仓库版本与安装版本，并实际调用 `$project-verifier` 确认加载五阶段 Skill。

**完成标准：** GitHub `main`、本地 `main`、安装目录和实际调用内容一致。

## P1：出现真实需求后再做

### A. 更强授权身份

只有用户确实需要接近安全执行平台的保证时，才增加 Validator/Runner/Hook 哈希、授权过期和可信安装路径。否则维持当前 revision-bound 工作流，并准确声明它不是对抗性安全边界。

### B. 安装 doctor

只有 stale installation 反复出现时，再增加只读 doctor。当前先在发布步骤中人工比对即可。

### C. Machine-readable schemas

只有出现第三方工具集成或 schema 兼容问题时，再提供完整 JSON Schema 和迁移工具。当前 `schema_version` 与离线 validator 足够。

### D. 示例输出

只有真实用户仍无法理解 `project_report.md`、`flow_matrix.md` 和阶段结果时，再增加一个完整 golden workbench 示例，不预先维护两套示例项目。

## 继续明确不做

- 用户操作录制或回放；
- 生产浏览器操作；
- 多宿主 Hook 强制执行；
- sandbox 或安全认证；
- SaaS/dashboard；
- 通用评分、综合分或雷达图。

## 推荐顺序

1. 完成 README 等现行文档体系同步，并加入 rubric 小型硬检查。
2. 最小离线 CI。
3. 三场景 Agent 行为复核；Hook smoke 仅在准备发布 Hook 时执行。
4. 提交、合并、推送和安装版本同步。
5. 停止开发并收集真实使用反馈；P1 不自动启动。
