# Task 7 简报：公开合同迁移至四阶段

## 目标

把已经独立审阅完成的 V3 Stage 1-4 作为唯一公开入口。用户不应再从 README、`SKILL.md`、元数据、CI 或旧 workflow 看到可执行的五阶段路线。

## 删除清单

- `skills/project-verifier/workflows/phase1_explore.md`
- `skills/project-verifier/workflows/phase2_diagrams.md`
- `skills/project-verifier/workflows/phase3_quality.md`
- `skills/project-verifier/workflows/phase4_usability.md`
- `skills/project-verifier/workflows/phase5_benchmark.md`
- `skills/project-verifier/templates/run_usability_template.sh`
- `LICENSE`

## 迁移范围

- 将 V3 validator、manifest、Benchmark runner 和 evaluator 提升为 canonical 文件名。
- 重写 `SKILL.md`、README、`agents/openai.yaml`、可选面试导出、eval 描述和离线 CI，使它们只引用 Stage 1-4。
- README 采用中文主叙述，说明四阶段 Gate、默认产物、脚本优先、条件工具选择、可信度边界与未隔离 executor 的限制。
- 不删除历史 iteration workbench，不执行真实 API/扫描/安装/推送/合并。

## 验收边界

完成后不应存在当前合同中的 `phase1` 至 `phase5` workflow、License 声明、录制/回放、默认评分或雷达图；Task 8 才执行完整离线回归和最终发布证据收尾。
