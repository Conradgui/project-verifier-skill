# Task 6 简报：Stage 4 证据优先 AI Benchmark

## 目标

只替换 V3 Benchmark 路径，建立适配具体项目的双入口合同：Stage 1/2
证据提出候选特征，用户选择希望突出的方向；任何 pilot 或 full 执行前必须完成最终方案审阅。

## 负责文件

- `skills/project-verifier/workflows/stage4_benchmark.md`
- `skills/project-verifier/templates/benchmark_task_template.json`
- `skills/project-verifier/templates/run_benchmark_v3_template.sh`
- `skills/project-verifier/templates/benchmark_evaluator_v3_template.py`
- `skills/project-verifier/scripts/validate_benchmark_task_v3.py`
- `skills/project-verifier/tests/test_benchmark.py`
- `skills/project-verifier/tests/test_contract.py`
- `skills/project-verifier/references/tool_adapters.md`
- Task 6 workbench report and review records.

## 非目标

- 不调用真实模型/API、不安装依赖、不下载后端或工具。
- 不生成通用评分、雷达图、隐藏默认 Baseline 或虚构优势主张。
- Task 7 前不修改 V2 的公开入口文件。

## 验收边界

本任务保留既有的原始指标、最小样本、证据文件、盲化 Judge 与“不以 Judge
单独证明安全”的保护；只补齐 V3 的方案输入、后端来源、比较结论和 Gate
绑定。用户只决定方向与最终方案确认；已授权 envelope 内可逆的后端胶水和报告措辞由 Agent 处理。

## 已接受的独立审阅修复范围

Task 6 初稿尚未通过。完成前必须在不新增后端、不进行真实执行的前提下，实现并测试以下内容：

1. 将 `final_plan_approval` 绑定到可验证的决策收据，其中包含决策 ID、方案哈希、源码 revision、用户选择方向和上限。
2. runner preflight 与 evaluator 共用一个严格的任务合同校验器。
3. 用数据集哈希、唯一样本 ID 和逐样本证据引用绑定最小样本，而不是相信自报数量。
4. 校验并实际使用每个主张指标的阈值和比较映射。
5. runner 在 dispatch 后创建执行收据；Evaluator 只有在匹配的 full 收据存在时才可输出正向结论。pilot、缺失、过期或不匹配的收据均为 `inconclusive` / `not_measured`。

执行收据是本地来源追溯链接，不是对手工编辑本地文件的密码学防篡改保证；Stage 4 报告必须保留此限制。
