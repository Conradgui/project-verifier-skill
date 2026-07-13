# Stage 4：证据优先的 AI Benchmark

## 适用边界

本阶段只适用于已经确认存在可评测 AI 或 AI-assisted 功能、且比较结果能够支持一个明确决策的项目。非 AI 路径应标记为 `not_applicable`；缺少凭据、获批数据集或有意义 Baseline 时只能产出 `plan_only` 方案。不得默认创建泛化的 LLM 对比。

## 双入口与用户 Gate

先从已确认的 Profile、流程矩阵、Stage 2 结果及经过选择的 Stage 3 发现中，提取 **3-5** 个有证据支撑的项目特征。再单独询问用户希望突出什么方向：可以接受推荐、选择全部、选择部分、提出新方向或跳过。

每个候选方向需说明用户价值、关联路径 ID、可证伪的比较主张、推荐 Baseline、数据来源、指标、可能使用的后端、预计调用量与限制。推荐 1-2 个方向，但不要让用户决定后端胶水代码或文件布局等细节。

用户只做两次关键决策：**方向选择** 与 **最终方案确认**。只有真实调用、成本、敏感数据、Baseline 含义、数据集范围、指标含义或副作用发生实质变化时才重新确认；用户未回复不等于批准。

## 方案与任务合同

先写入 `project_verification_workbench/stage4_benchmark_plan.md`，再创建任务 JSON。方案应把“证据派生特征”与“用户突出方向”分别记录，并明确比较主张、决策用途、路径 ID、Baseline、数据来源、后端版本/配置、等价性偏差、指标合同、预算、停止条件及可行性（`ready_now`、`needs_setup`、`plan_only` 或 `rejected`）。

只有最终方案被确认后，才能从 `benchmark_task_template.json` 创建可执行任务。`final_plan_approval` 必须引用最终方案的决策 ID、方案 SHA-256、源码 revision、授权收据和授权 envelope；envelope 必须绑定任务 ID、方案哈希、路径、比较主张、Baseline、数据集和指标。

样本只能是 `real`、`existing_test`、`user_confirmed` 或 `synthetic_candidate`。每个样本必须有唯一 ID 和来源证据；没有确定性 oracle 或用户明确确认时，合成候选不得作为 ground truth。工具与 Baseline 的结果必须覆盖同一组已批准样本，并为每个样本保存证据引用。

每个指标都要定义测量方法、绝对成功阈值、相对比较合同、最小样本量和所需证据字段。报告展示原始值、阈值是否达标、比较是否达标、样本充分性、证据和限制；不生成通用评分或雷达图。

`llm_judge_score` 只接受逐样本、盲化且随机顺序的 Judge 结果，并保留 prompt、模型、版本和证据引用。可由 Judge 单独支撑的类别采用受控白名单：`quality`、`helpfulness`、`relevance`、`style`、`instruction_following`。安全、隐私、泄漏与安全性类别不在白名单中，必须使用其他可复核证据或标记为 `not_measured`。

## Preflight、执行与收据

`run_benchmark_template.sh preflight` 会校验完整任务、最终方案授权、数据集唯一性、指标合同、执行上限、executor 和已确认的 Stage 1 Profile，且不会调用模型、API、工具、Baseline 或 executor。

执行命令为 `pilot TASK_ID` 或 `full TASK_ID`。两者都需要当前有效的 `stage4 / benchmark_execution` 授权；实际请求上限不得超过任务和授权 envelope 的上限。runner 只接受 `project_verification_workbench/` 内尚不存在且非符号链接的输出路径，并在执行后写入新的执行收据、日志、工具结果、Baseline 结果和遥测结果。

项目 executor 是受信任但**未隔离**的 bridge：执行 envelope 必须在 `scope.side_effects` 中显式包含 `trusted_project_executor_execution`，并在 `write_scope` 中授权 `project_verification_workbench`。这能让用户明确接受真实调用与副作用风险，但不构成 OS sandbox，也不能技术性阻止恶意或错误 executor 访问网络或写入其他位置；需要强隔离时只保留计划，不执行项目 executor。

收据绑定任务方案哈希、数据集哈希、后端/Baseline 身份、审批 ID、实际模式、退出码、耗时、调用/重试/副作用遥测及输出哈希。缺少、过期、不匹配或 pilot 收据时，Evaluator 只能给出 `inconclusive` 或 `not_measured`；只有匹配的 `full` 收据才允许产生 `supported`、`partially_supported` 或 `not_supported` 结论。

调用 evaluator CLI 时必须提供项目根目录；CLI 会实时计算当前源码指纹，并拒绝与方案及 `full` 收据不一致的旧证据。纯函数接口也必须显式传入当前源码指纹，缺失时不输出结论。

收据提供本地文件之间的可追溯关联，不是对手工编辑本地文件的密码学防篡改证明。报告必须保留这一限制，以及负面结果和无显著差异结果。

pilot 仅是小范围验证：`phase_status: completed`、`result_outcome: inconclusive`、`execution_scope: pilot`、`claim_eligibility: pilot`。它不能替代完整 Benchmark，也不能生成完整优势主张。
