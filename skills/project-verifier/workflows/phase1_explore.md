# Phase 1: Full Repo Exploration + Security/Quality/Architecture Audit

## Purpose
Analyze the target codebase to understand its language, structure, entry points, dependencies, and health, with a specific focus on finding security risks and architectural flaws.

## Rules
*   **STRICTLY READ-ONLY**: Do not modify any files or write any code during this phase.
*   **NO GUESSING**: Mark any unknown or ambiguous information with a red question mark `❓`. Do not hallucinate or assume.
*   **IF SECURITY RISKS ARE FOUND**: Prioritize displaying them immediately.
*   **WORKBENCH REQUIRED**: Create `project_verification_workbench/phase1_audit.md` and write the audit evidence there. This is the only file-writing exception to the read-only rule.

---

## Instructions & Steps

### Step 1: Read Project Files
Read the files in the codebase systematically.
1. Identify and read project config files: `package.json`, `pyproject.toml`, `requirements.txt`, `tsconfig.json`, `CMakeLists.txt`, `Cargo.toml`, etc.
2. Identify and read entry points: `main.py`, `app.js`, `index.ts`, `server.py`, `cli.go`, etc.
3. Check for existing tests: `tests/`, `test/`, `spec/`, etc.
4. Read docs: `README.md`, `docs/`.
5. Check environment example files: `.env.example`, `.env.sample`. Do NOT read actual `.env` files if they contain production keys; if you must read them to verify gitignore, check if they are ignored first.

*Note for large repos (>80 files)*: Print the directory tree first, list your reading plan, and prioritize the core entrypoints, config files, and files that trigger side-effects (e.g. calling APIs, writing files, executing subprocesses).

### Step 2: Extract Project Overview
Compile the following details:
1. Programming languages, frameworks, and runtimes.
2. Project size: approximate file count, lines of code, and major folders.
3. Project type: CLI, Web app, API service, Agent, Frontend, or Mixed.
4. Core functionality explained in 1 or 2 simple sentences.
5. Existing test framework and current coverage (if known).
6. External integrations: LLM APIs, Database, GitHub, File system, etc.
7. Top risk areas where the application is most likely to break.

### Step 3: Security Audit (🔴 Critical Priority)
Check each area and mark with: 🔴 Danger / ⚠️ Warning / ✅ Secure / ❓ Unsure.

*   **A. Secret Leakage**: Are API keys, DB connection strings, or passwords hardcoded? Is `.env` included in `.gitignore`?
*   **B. Input Validation**: Are inputs validated? Is there danger of SQL injection, shell command injection (e.g. direct string formatting in shell calls), path traversal, or unhandled null/overflow inputs?
*   **C. Process Execution Boundaries**: Are external command runners used (e.g. `subprocess`, `exec`, `eval`, `shell=True`, `os.system`)? Are there safe boundaries or confirmations?
*   **D. Cost/API Exhaustion Risks**: Is there any loop that could make infinite LLM API calls? Are timeout bounds, max token counts, or billing limit safeguards in place?
*   **E. Dependency Risk**: Identify major third-party libraries and note any outdated versions or missing lockfiles.

For each issue, specify:
*   File path and approximate line number.
*   Why it is a risk.
*   How to fix it (brief summary).
*   Whether it is a **Blocker** that must be fixed before proceeding to Phase 2.

### Step 4: Quality & API Interface Audit
Evaluate and mark with 🔴 / ⚠️ / ✅ / ❓:
*   **A. Error Handling**: Are network/file operations safely wrapped? Are exceptions caught silently (e.g. `catch {}` or `except: pass`)?
*   **B. Boundary Cases**: How does the code handle empty lists, None/null, zero length values, or type mismatches?
*   **C. Interface Integrity**: Are inputs typed? Are CLI arguments validated?
*   **D. State Management**: Where is state persisted (Memory, Local DB, Files)? Can state be corrupted by concurrent operations?
*   **E. Modularity**: Identify tightly coupled components or excessively long files.

### Step 5: Functional & Control Flow Discovery
1.  **Entry Points**: List all CLI options, API routes, or event hooks.
2.  **Execution Path Mapping**: Trace the flow from user input to the final output or side effects.
3.  **Cross-cutting Concerns**: Identify shared files or databases (e.g. config managers) where errors will cascade.
4.  **Sequential Dependencies**: Identify step order constraints (e.g., Step A must run before Step B).
5.  **Undocumented Features**: List features found in the code but omitted in `README.md`.
6.  **Core Value Proposals**: Suggest 2-3 key value statements of the project (e.g. reliability, multi-step orchestration, cost savings).

---

## Output Requirements

Before presenting the response, write `project_verification_workbench/phase1_audit.md` with:
*   Project overview.
*   Security audit table with file paths and approximate line numbers.
*   Code/API quality issues.
*   Entry points and flow matrix.
*   Sequential and component dependencies.
*   Core value proposition candidates.
*   Overall health rating and whether Phase 2 is allowed to proceed.

Present the audit report using the following structure:
1.  **Project Overview**
2.  **Security Audit Table** (Ordered by severity: 🔴 -> ⚠️ -> ❓ -> ✅)
3.  **Code/API Quality Issues**
4.  **Entry Points and Flow Matrix**
5.  **Sequential & Component Dependencies**
6.  **Core Value Proposition Candidates**
7.  **Overall Health Rating** (🟢 Proceed / 🟡 Proceed with cautions / 🔴 STOP & Fix Blocker Risks)

### Phase Confirmation Request
End the output with this exact template (replace bracketed values):
```markdown
---
本阶段分析了 [X] 个文件，发现 [Y] 个安全问题（🔴[a]个/⚠️[b]个），
识别出 [Z] 个入口点，核心价值主张候选为 [...]。

三个关键问题需要你确认：
① 入口点清单有没有漏掉你平时会用的启动方式或常用命令？
② 核心价值主张候选是否准确？有没有功能是你并不想作为核心展示的？
③ 是否存在 🔴 级别安全问题？如果有，建议新开会话先进行修复，修完告诉我。

如无异议，回复「继续」；如有修改，直接告诉我。
---
```
