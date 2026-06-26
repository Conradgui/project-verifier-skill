# project-verifier 可信度强化迭代

## Goal

把 `$project-verifier` 从“能生成漂亮材料的流程提示包”升级为“证据可复核、失败可解释、跨阶段可追踪的项目验证 skill”。

## Scope

- 保持 skill 名称、目录结构和安装命令不变。
- 不引入第三方依赖。
- 优先修复 Benchmark 证据可信度、runner/CI 执行可靠性、跨阶段 artifact contract 和 README 过度承诺。

## Verification Targets

1. `benchmark_evaluator_template.py` 不再给缺少证据的维度默认高分。
2. `run_usability_template.sh` 按 `.py`、`.sh`、`.ts` 类型分发执行，并对缺少 TypeScript runtime 给出清晰失败。
3. Phase 1-6 workflow 都写入 `project_verification_workbench/` 产物。
4. README 不再使用“不可伪造”“企业级工程产品”等过度承诺。

