# Task 6 修复报告：Stage 4 证据优先 Benchmark

## 当前结论

Task 6 的初版被独立审阅拒绝后，已完成针对五项 P1 可信度缺口的修复；本报告仅说明当前定向实现，不代表 Task 6 已完成。是否完成仍取决于新的独立审阅。

## 已落实的合同

1. `final_plan_approval` 现在绑定决策 ID、方案 SHA-256、源码 revision、收据路径与 envelope 路径。
2. `validate_benchmark_task_v3.py` 是 runner preflight 与 evaluator 共用的严格合同来源。
3. 数据集必须使用唯一 ID、数据集 SHA-256 和逐样本证据；结果必须覆盖同一组已批准样本，不能再用自报 `sample_count` 证明充分性。
4. 每个指标的绝对阈值与相对比较合同都会参与结论；比较胜出但绝对阈值不达标时，结论为 `not_supported`。
5. `pilot TASK_ID` 与 `full TASK_ID` 都要求明确任务 ID。runner 仅接受当前授权范围内的新 workbench 输出路径，并在执行后生成新的收据、日志和输出哈希。
6. Evaluator 只有在收据、任务、数据集、后端/Baseline、输出哈希、遥测和 `full` 模式全部匹配时，才允许产生正向或负向完整结论；pilot、缺失、过期或不匹配证据均为 `inconclusive` / `not_measured`。
7. 保留受限的 `llm_judge_score`：逐样本 Judge 必须盲化、随机顺序，并有 prompt、模型、版本和证据；安全、隐私、泄漏和安全性类别不得仅依赖 Judge。

## 定向验证

- `test_benchmark.py`：14/14 通过。
- `bash -n templates/run_benchmark_v3_template.sh`：通过。
- `py_compile validate_benchmark_task_v3.py benchmark_evaluator_v3_template.py`：通过。
- `git diff --check`：通过。

## 明确边界

- 没有调用模型/API、安装依赖、下载后端、访问网络或执行真实 Benchmark。
- 执行收据是本地可追溯绑定，不是针对手工编辑本地文件的密码学防篡改认证。
- evaluator CLI 会重新计算目标仓库的当前源码指纹；源码变更后，旧方案与旧 full 收据只能得到 `inconclusive`。
- 本任务未扩展为通用评测框架；当前模板只实现 `numeric_value` 与受限 `llm_judge_score`。其他指标类型需要先被方案和合同明确支持，不能被静默猜测或降级。
- 未重复运行完整历史套件；公开合同尚未迁移，完整兼容性验证仍属于 Task 7/8。

## 最终复核

最终独立审阅已 `APPROVED`，未发现 P0/P1。公开 CLI 会重新读取 workbench 实物并复验当前 Gate；未隔离 executor 的信任边界已要求显式授权且没有被包装成 sandbox。
