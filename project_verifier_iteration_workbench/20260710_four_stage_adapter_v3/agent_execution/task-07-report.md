# Task 7 报告：公开合同迁移至四阶段

## 完成内容

- 公开 README、`SKILL.md`、Agent 默认提示和 CI 已改为四阶段模型。
- Gate、manifest、Benchmark runner、evaluator 和共享 Benchmark 合同校验器已提升为正式名称。
- 删除五个旧 `phase*.md` workflow、旧 usability runner、过渡副本和 `LICENSE`。
- stale-authorization fixture 已迁移为 `stage2 / live_e2e`，明确以源码变化使旧 Profile 与旧授权同时失效，而不是以计划哈希错配模拟阻断。
- 新增公开合同断言：四个 Stage workflow 必须存在、旧 phase workflow 与 License 不得返回、canonical 模板不得保留 `_v3` 名称。
- 独立审阅发现并修复：Stage 2 默认 Gate 改为 Skill 自带 validator；stale-authorization fixture 补齐确认 Profile、当前源码版本与 runner 级派发前阻断；贡献条款删除 MIT；默认机器产物改为 `stage2_*`/`stage3_*`；README 恢复可选 Hook 入口。

## 验证

- 完整迁移后的 `unittest` 套件曾以退出码 0 完成；最终收束后的合同、质量、安全和 Benchmark 定向回归分别为 14、16、35、14 项通过。
- `quick_validate.py skills/project-verifier`：通过。
- Skill JSON 解析：通过。
- 三个 runner 的 `bash -n`：通过。
- `git diff --check`：通过。

## 边界

没有调用真实 API、执行安全扫描、安装依赖、覆盖本地安装 Skill、推送或合并。Task 8 仍负责一次性的最终离线验证报告和发布前证据收尾；本任务不重复执行发布级全量检查。
