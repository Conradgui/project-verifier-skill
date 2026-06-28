# Phase 4: Conditional Live Usability Testing (L2 E2E)

## Purpose
Determine whether selected P0 paths can be verified in the real environment, then execute them only after environment and execution authorization gates. A blocked environment produces a reusable plan and recovery conditions, not a failed or fabricated test result.

---

## Instructions & Steps

### Step 0: Load Prior Evidence
Read `project_verification_workbench/verification_manifest.md`, `project_verification_workbench/phase2_flow_matrix.md`, and `project_verification_workbench/phase3_test_results.md`. If Phase 3 is missing, state that offline quality maturity is unknown. Set Phase 4 to `in_progress`.

### Step 1: Applicability and Real Usability Plan
Design real-world usage scenarios for the P0 paths documented in Phase 2.
1.  **Define Inputs**: Choose realistic, domain-specific parameters. Do not use generic placeholders like "test", "foo", or "bar".
2.  **Define Assertions**:
    *   Validate the final outcome (e.g., exit code is 0, files exist, outputs are not empty).
    *   Do not test the exact wording of natural language model outputs (as these can vary); instead, test structure, schema, file writes, and response headers.
3.  **Specify Timeouts**: Set maximum wait times (e.g., 30s to 120s depending on call complexity) to prevent infinite loops or hanging connections.
4.  **Identify Diagnostic Steps**: Note what parts of the script are most likely to fail due to rate limits or network issues, and how the runner can detect these errors.
5.  **Declare Required Environment Variables and Backends**: List only names, commands, services, databases, browsers, or local runtimes each path truly requires. Never read or display secret values.
6.  **Declare Execution Bounds**: State the maximum path count, external calls per path, retries, timeout per call, and possible file/database side effects.

Write `project_verification_workbench/phase4_usability_plan.md` before creating scripts. Include path IDs, inputs, assertions, environment names, backend dependencies, execution bounds, side effects, and recovery steps.

**Ask the user to review the Usability Test Plan before writing scripts.** The user may approve it, revise it, request guided environment repair, choose plan-only and skip execution, or stop.

### Step 2: Environment Readiness Decision
Check readiness without making a live request and without parsing or echoing `.env` values.

- If dependencies are missing, list the exact blocker and setup instruction. Do not install automatically.
- If the user chooses repair, mark Phase 4 `blocked`, preserve the plan, and resume after they confirm the repair.
- If the user chooses plan-only, write `phase4_usability_results.json` with `status: skipped`, empty `paths`, blockers, and recovery conditions. Do not create or execute live scripts.
- If ready, record that readiness is not execution authorization and continue only after plan approval.

### Step 3: Implement Approved Usability Test Scripts
Upon approval, create the test files:
1.  **Directory**: Place all files under `tests/usability/`.
2.  **Naming Convention**: Create separate, standalone executable script files for each path:
    `usability_[PathID].py` (or `.ts`, `.sh` as appropriate).
3.  **Isolation**: Ensure every test script runs inside an isolated temporary directory to prevent race conditions or caching pollution, and clean up files when finished.
4.  **Cost Controls**: Implement the approved retry cap, timeout, and external-call limit. Do not increase them silently.
5.  **Output Log Formatting**: Each script must write standard logs to a separate file, and print a single-line result to stdout upon completion:
    *   `✅ [PathID] [PathName] - Usable (Took X seconds)`
    *   `❌ [PathID] [PathName] - Failed (Stage: [FailurePoint] / Error: [ErrorSummary])`

### Step 4: Write Usability Test Runner and Preflight
Generate a shell runner `run_usability.sh` in the project root:
*   Supports only explicit modes: `run_usability.sh preflight` and `run_usability.sh run`. With no mode, print usage and make no live request.
*   `preflight` is mandatory and must never execute a usability script. It checks declared environment names, required files, commands, and runtimes.
*   `run` executes approved E2E scripts sequentially only after preflight has passed.
*   Enforces environment checks from `USABILITY_REQUIRED_ENV` or `tests/usability/required_env.txt`; do not assume provider-specific keys unless the project actually needs them.
*   Reads required file and command names from `USABILITY_REQUIRED_FILES`, `USABILITY_REQUIRED_COMMANDS`, or corresponding files under `tests/usability/`.
*   Validates and records approved numeric bounds through `USABILITY_MAX_PATHS`, `USABILITY_MAX_CALLS_PER_PATH`, `USABILITY_MAX_RETRIES`, and `USABILITY_TIMEOUT_SECONDS`; invalid values or an exceeded path limit block execution. The generated path scripts remain responsible for enforcing their own call, retry, and per-call timeout limits.
*   Provides a clean summary at the end showing pass rates: `X/Y usability paths passed.`
*   Cleans up test state files.
*   Writes `project_verification_workbench/phase4_usability_results.json` directly after `run`; do not rely on the conversation to reconstruct exit codes or durations.
After preflight, show the user the ready paths and approved maximum calls, retries, timeouts, and side effects. Obtain explicit execution authorization before `run`.

Write `project_verification_workbench/phase4_usability_results.json` for completed, blocked, skipped, or failed outcomes:
    ```json
    {
      "schema_version": "2.0",
      "status": "completed",
      "required_env": ["MODEL_API_KEY"],
      "missing_env": [],
      "backend_dependencies": ["project API service"],
      "execution_authorization": true,
      "execution_bounds": {"max_paths": 1, "max_calls_per_path": 2, "max_retries": 1, "timeout_seconds": 60},
      "paths": [{
        "path_id": "P0_001",
        "path_name": "Core path",
        "exit_code": 0,
        "duration_seconds": 12.4,
        "log_path": "tests/usability/reports/usability_P0_001.log",
        "failure_stage": null,
        "errors": []
      }],
      "blockers": [],
      "recovery_conditions": []
    }
    ```

Update `verification_manifest.md` with authorization, result status, blockers, recovery conditions, and artifact links.

---

## Output Requirements
When completing Phase 4, present the results to the user using this template:
```markdown
---
Phase 4 状态：[completed / blocked / skipped / failed]。
[如执行] 对 [X] 条 P0 路径执行了真实 E2E，[Y] 条通过，[Z] 条失败。
[如未执行] 已保存 `phase4_usability_plan.md`；未发生真实调用，恢复条件为：[列出]。

三个关键问题需要你确认：
① 通过的路径，行为是否符合你平时手动使用时的预期？
② 失败的路径（如有），你是否理解失败原因并知道下一步怎么处理？
③ 有没有你希望测试但没有包含在 P0 路径里的真实使用场景？

请选择：回复「继续」评估 Phase 5；回复「修改」调整本阶段；回复「跳过」保留计划但不执行；或回复「停止」。
---
```
