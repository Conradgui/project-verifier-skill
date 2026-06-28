# Phase 3: Quality Test Suite (Mocks and Mapped Behavior)

## Purpose
Build a robust testing suite utilizing mocks, fixtures, and scripted providers. This ensures the codebase logic, input boundaries, exception propagation, and security limits are verified without incurring API costs or executing destructive side effects.

---

## Instructions & Steps

### Step 0: Load Flow Matrix
Read `project_verification_workbench/verification_manifest.md` and `project_verification_workbench/phase2_flow_matrix.md` before planning tests. If the matrix is missing, do not invent P0 paths from memory; recover and persist it first. Set Phase 3 to `in_progress`.

### Step 1: Self-Audit (Perform Before Code Generation)
Answer these questions internally or in your thinking process before writing any code:
1.  Are these tests designed from the user's perspective (evaluating core results/behaviors), or are they just mirroring code implementation?
2.  Do we have enough information about inputs/outputs to write effective assertions, or are we just checking if functions run without raising errors?
3.  Is there a risk that mock objects are too broad (e.g. mocking out the entire module under test and validating nothing)?

### Step 2: Test Planning
Outline a test matrix categorized under five key test buckets:
*   **A. Single Path Verification**: Happy path tests for all P0 entry points.
*   **B. Junction Synchronization**: Verify shared files, caches, or state stores. Ensure changes written by Process A are correctly parsed by Process B, and that corrupt state is handled gracefully.
*   **C. Safety & Boundaries**: Feed empty variables, excessively long inputs, SQL injections, path traversal strings (e.g. `../../etc/passwd`), or type mismatches. Ensure the system halts safely or throws clean user-facing errors rather than crashing.
*   **D. Fault Injection & Propagation**: Force failures (e.g., HTTP 500, network timeouts, invalid JSON response) inside dependent API clients or external system calls. Ensure the error is propagated clearly up the call stack rather than failing silently.
*   **E. Isolation Verification**: Validate that prior test state (e.g., files left in temporary directories) does not affect subsequent runs. Use fresh directories or fixture setups for each run.

**Ask the user to review the test plan before writing the actual code.** Show the exact test files, runner files, CI files, and dependency commands that would be added or changed. Do not install a package or edit CI until the user approves that list.

Write the approved plan to `project_verification_workbench/phase3_test_plan.md`. Include the P0 path IDs being tested, planned assertions, mock boundaries, and which tests are explicitly out of scope.

### Step 3: Implement Code Quality Tests
Upon user approval, write the test suite:
1.  **Framework Choice**: Detect the project's framework and use the standard testing tools (`pytest` for Python, `jest`/`vitest` for JS/TS, etc.).
2.  **Mocking & Fixtures**: Setup local mock providers, fixtures, and context managers. Never let tests run real web requests (use tools like `unittest.mock`, `pytest-mock`, or JS mock frameworks).
3.  **Offline Fixtures**: Use hand-authored fixtures, scripted providers, or user-provided sanitized recordings. Do not record live traffic in Phase 3. If a new recording is genuinely needed, move that activity to the Phase 4 live-call authorization gate.
4.  **Directory Structure**:
    *   `tests/unit/` - Core mock tests (happy path, safety checks, exception tracking).
    *   `tests/integration/` - High-level flow tests (e.g., verifying multi-step script execution using local mock assets).
5.  **Formatting**: Name test functions with reference IDs, e.g. `test_P0_001__handles_missing_config_gracefully`.
6.  **No Live Credentials**: Phase 3 tests must not require external keys or real network access. Move any such path to Phase 4 and list it as out of scope here.
7.  **CI/CD Pipeline Setup**: Generate a minimal GitHub Actions workflow file under `.github/workflows/verify_pipeline.yml` for the detected project stack. Do not use `|| true` to hide install or test failures. If the project has both Python and Node, choose the stack that owns the generated tests and mention the other as out of scope.
    *   Python example:
    ```yaml
    name: CI Code Quality Pipeline
    on:
      push:
        branches: [ main, master, dev ]
      pull_request:
        branches: [ main, master, dev ]
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Set up Python
            uses: actions/setup-python@v5
            with:
              python-version: '3.11'
          - name: Install dependencies
            run: |
              python -m pip install --upgrade pip
              if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
              pip install pytest pytest-mock
          - name: Run Code Quality Tests
            run: chmod +x ./run_tests.sh && ./run_tests.sh unit
    ```
    *   Node example:
    ```yaml
    name: CI Code Quality Pipeline
    on:
      push:
        branches: [ main, master, dev ]
      pull_request:
        branches: [ main, master, dev ]
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Set up Node
            uses: actions/setup-node@v4
            with:
              node-version: '20'
              cache: npm
          - name: Install dependencies
            run: npm ci
          - name: Run Code Quality Tests
            run: chmod +x ./run_tests.sh && ./run_tests.sh unit
    ```

### Step 4: Write Independent Test Runner
Generate a shell runner `run_tests.sh` in the project root:
*   Supports options:
    *   `./run_tests.sh unit` (Run isolated unit tests with no keys).
    *   `./run_tests.sh integration` (Run offline multi-module tests with local fixtures).
    *   `./run_tests.sh all` (Run everything).
*   Cleans up temporary state directories automatically upon completion.
*   Ensure it runs cleanly and returns appropriate exit codes (0 for success, non-zero for failure).
*   After running, write `project_verification_workbench/phase3_test_results.md` with generated test files, command output summary, pass/fail counts, and any skipped tests. Update the manifest with Phase 3 status and artifacts.

---

## Output Requirements
When completing Phase 3, present the results to the user using this template:
```markdown
---
本阶段生成了 [X] 个测试用例（unit:[a]个 / integration:[b]个），
覆盖 [Y] 个 P0 路径，[Z] 个交汇点，[n] 个安全边界场景。

三个关键问题需要你确认：
① 有没有你平时手动测试时会做但这里没覆盖到的场景？
② 测试函数的命名是否清楚到你看名字就知道它在测什么？
③ run_tests.sh unit 能在你的环境里直接跑通吗？
   如果跑不通，把错误信息告诉我。

请选择：回复「继续」评估 Phase 4；回复「修改」调整测试；或回复「停止」并保留当前产物。
---
```
