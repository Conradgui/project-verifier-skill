# Task 6 Independent Review

Reviewer: independent read-only subagent (`Ohm`)

Verdict: `CHANGES_REQUIRED`

## P1 Findings Accepted By Controller

1. `rubric_approved` is only a task-local boolean and lacks a verifiable final
   plan approval reference.
2. Runner preflight does not validate the full task contract before a later
   pilot/full path could dispatch.
3. Minimum samples are self-reported rather than bound to unique approved
   dataset sample IDs and per-sample evidence.
4. `success_threshold` is neither fully validated nor included in the claim
   decision.
5. Evaluator input is not bound to an authorized Stage 4 execution receipt,
   backend/baseline identity, dataset identity, or actual mode, so a fabricated
   full result or pilot result could become a positive claim.

## Repair Direction

Before adding more backends or metrics, introduce one strict task-contract
validator shared by preflight and evaluator. Bind a final plan-approval receipt,
dataset hash and unique sample IDs, complete metric thresholds/contracts, and a
runner-created execution receipt. The evaluator must accept `supported` only
from receipt-bound full runs; every missing or mismatched element remains
`inconclusive` / `not_measured`.

No real model/API call, dependency installation, network access, file staging,
commit, push, or merge occurred during this review.

## 第二次独立审阅：修复前发现（2026-07-13）

新的只读 reviewer 发现 4 个 P1 和 1 个 P2，控制器已开始修复，不能将本节视为当前未解决状态：

1. runner 输出路径可利用 `..` 越出 workbench；已改为拒绝 `..`、符号链接并在真实路径解析后检查 workbench 边界。
2. `rubric_approved: false` 的任务仍可能 dispatch；已在执行 envelope 校验中硬性拒绝。
3. Evaluator 未检查源码变更后的旧收据；CLI 现从项目根目录重新计算源码指纹，纯函数缺少当前指纹时不会输出结论。
4. 数值指标只信任聚合值；现要求每个已批准样本都有有限的逐样本值并从该值计算原始指标。
5. Judge 安全限制可用错误类别绕过；任务比较主张出现安全/隐私/泄漏关键词时，拒绝使用 Judge 作为唯一指标。

这些修复仍须由新的独立 reviewer 验证。整个审阅与修复过程未调用真实模型/API、网络或安装任何依赖。

## 第二次独立审阅：修复后发现（2026-07-13）

第二位 reviewer 确认前述路径越界、rubric dispatch、普通源码变更后的旧收据和数值聚合伪充分均已关闭，但发现两项 P1：

1. Judge 风险类别仍可由自由文本绕过；已将可单独使用 Judge 的类别改为受控白名单。
2. executor 可放入被源码指纹排除的 workbench；已明确拒绝该目录下的 executor。

这两项补丁已加入定向测试，仍需最后一次独立复核。审阅期间未执行真实模型/API、网络、安装或 Git 写入。

## 最终独立审阅：当前阻断项（2026-07-13）

最终 reviewer 未发现 P0，但结论为 `CHANGES_REQUIRED`，有两项 P1 尚未关闭：

1. Evaluator 仍能接受彼此自洽但不来自 runner 的 JSON；它需要从项目 workbench 的收据路径重新读取并校验当前文件哈希，同时复验实际授权 receipt/envelope。
2. 项目 executor 是未隔离进程，Bash 无法技术性限制它的网络和任意文件写入。正确处理不是宣称 sandbox，而是要求同一 envelope 显式确认 `trusted_project_executor_execution`，并在文档中说明这是信任边界、不是 OS 级限制。

Task 6 继续保持进行中；不得提交、不得进入 Task 7。此审阅没有编辑文件、联网、安装依赖或调用真实 API。

## 最终复核结论（2026-07-13）

最终独立 reviewer 结论为 `APPROVED`，未发现 P0/P1。公开 evaluator CLI 已改为只从当前项目 workbench 读取收据与 Tool/Baseline 实物，重新计算源码指纹，并复验计划和执行 Gate；执行收据也绑定实际授权收据与 envelope。runner 对项目 executor 明确要求同一 envelope 的 `trusted_project_executor_execution` 确认，文档同时说明这不是 OS sandbox。

保留的非阻断限制：本地收据并不提供抵抗手工篡改的密码学保证；该限制已在 Stage 4 工作流和 Task 6 报告中如实说明。Task 7 的公开合同迁移尚未开始，不属于本任务缺陷。
