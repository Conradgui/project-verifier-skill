# Phase 4: Real Usability Testing (E2E & Live API Validation)

## Purpose
Validate that the application works seamlessly under real-world conditions by executing end-to-end (E2E) paths using actual API endpoints. This phase verifies live system behavior, network connectivity, and external data parsing.

---

## Instructions & Steps

### Step 0: Load Prior Evidence
Read `project_verification_workbench/phase2_flow_matrix.md` and `project_verification_workbench/phase3_test_results.md` before planning real usability tests. If Phase 3 results are missing, state that mock-test maturity is unknown before running live paths.

### Step 1: Real Usability Test Planning
Design real-world usage scenarios for the P0 paths documented in Phase 2.
1.  **Define Inputs**: Choose realistic, domain-specific parameters. Do not use generic placeholders like "test", "foo", or "bar".
2.  **Define Assertions**:
    *   Validate the final outcome (e.g., exit code is 0, files exist, outputs are not empty).
    *   Do not test the exact wording of natural language model outputs (as these can vary); instead, test structure, schema, file writes, and response headers.
3.  **Specify Timeouts**: Set maximum wait times (e.g., 30s to 120s depending on call complexity) to prevent infinite loops or hanging connections.
4.  **Identify Diagnostic Steps**: Note what parts of the script are most likely to fail due to rate limits or network issues, and how the runner can detect these errors.
5.  **Declare Required Environment Variables**: List only the variables each real path truly requires. Do not hardcode generic API key assumptions. If variables are required by all scripts, write them to `tests/usability/required_env.txt` or instruct the runner via `USABILITY_REQUIRED_ENV`.

**Ask the user to review the Usability Test Plan before writing scripts.**

### Step 2: Implement Usability Test Scripts
Upon approval, create the test files:
1.  **Directory**: Place all files under `tests/usability/`.
2.  **Naming Convention**: Create separate, standalone executable script files for each path:
    `usability_[PathID].py` (or `.ts`, `.sh` as appropriate).
3.  **Isolation**: Ensure every test script runs inside an isolated temporary directory to prevent race conditions or caching pollution, and clean up files when finished.
4.  **Cost Controls**: Implement retry counts with exponential backoff.
5.  **Output Log Formatting**: Each script must write standard logs to a separate file, and print a single-line result to stdout upon completion:
    *   `✅ [PathID] [PathName] - Usable (Took X seconds)`
    *   `❌ [PathID] [PathName] - Failed (Stage: [FailurePoint] / Error: [ErrorSummary])`

### Step 3: Write Usability Test Runner
Generate a shell runner `run_usability.sh` in the project root:
*   Runs all E2E usability scripts sequentially.
*   Enforces environment checks from `USABILITY_REQUIRED_ENV` or `tests/usability/required_env.txt`; do not assume provider-specific keys unless the project actually needs them.
*   Provides a clean summary at the end showing pass rates: `X/Y usability paths passed.`
*   Cleans up test state files.
*   Writes `project_verification_workbench/phase4_usability_results.json` with one object per path:
    ```json
    {
      "path_id": "P0_001",
      "path_name": "Core path",
      "required_env": ["MODEL_API_KEY"],
      "exit_code": 0,
      "duration_seconds": 12.4,
      "log_path": "tests/usability/reports/usability_P0_001.log",
      "failure_stage": null,
      "errors": []
    }
    ```

---

## Output Requirements
When completing Phase 4, present the results to the user using this template:
```markdown
---
本阶段对 [X] 条 P0 路径执行了真实 API 可用性测试，[Y] 条通过，[Z] 条失败。
[如有失败] 失败路径：[列出]，已分析原因。

三个关键问题需要你确认：
① 通过的路径，行为是否符合你平时手动使用时的预期？
② 失败的路径（如有），你是否理解失败原因并知道下一步怎么处理？
③ 有没有你希望测试但没有包含在 P0 路径里的真实使用场景？

如无异议，回复「继续」；如有修改，直接告诉我。
---
```
