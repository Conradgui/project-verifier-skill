# Phase 2: User Flows, Architecture Diagrams, & Documentation Integration

## Purpose
Translate codebase logic and paths into visual workflows (Mermaid format), compile a testing matrix, and integrate these assets into a copy of the project's main documentation.

---

## Instructions & Steps

### Step 0: Load Phase 1 Evidence
Read `project_verification_workbench/phase1_audit.md` first. If it is missing, perform a quick non-destructive exploration to recover entry points and risk areas, then write the recovered context to that file before continuing.

### Step 1: User Flow Mapping (User Perspective)
Map out how users interact with the system. Focus entirely on user-facing actions and business terms (e.g., "User starts tool", "System runs query", "User reviews diff"), avoiding technical class/function names.

1.  **Categorize Paths**:
    *   **P0 (Core Happy Path)**: Most common path illustrating core project value.
    *   **P1 (Alternate Branches)**: Secondary success paths or optional settings.
    *   **P2 (Failure & Recovery)**: Unhappy paths, error inputs, fallback mechanisms.
2.  **Path Listing**: Document each path with an ID (e.g., `P0_001`, `P1_001`), descriptions of the inputs, successful outputs, and recovery behaviors.
3.  **Mermaid Flowchart (LR)**: Create a Mermaid `flowchart LR`.
    *   Declare all nodes at the top first, then define connection links on separate lines.
    *   Use semantic uppercase IDs (`START_NODE`, `INPUT_VALIDATION`).
    *   Apply style classes:
        ```mermaid
        classDef main fill:#dbeafe,stroke:#3b82f6,color:#111827
        classDef decision fill:#fef9c3,stroke:#ca8a04,color:#111827
        classDef error fill:#fee2e2,stroke:#ef4444,color:#111827
        classDef success fill:#dcfce7,stroke:#22c55e,color:#111827
        classDef terminal fill:#f3f4f6,stroke:#6b7280,color:#111827,rx:20
        ```
    *   If nodes exceed 35, split into separate flowcharts for P0, P1, and P2.

### Step 2: System Architecture Diagram (Technical Perspective)
Represent the code layout at a module or package level. Do not display individual classes or helper methods.

1.  **Trace Module Layout**: Define layers (e.g., Interface Layer, Core Logic, Storage, External Services).
2.  **Highlight Risk Joints**: Note connections that read/write data, run shell commands, or query external APIs.
3.  **Mermaid Architecture (TD)**: Create a Mermaid `flowchart TD` using similar structured styles:
    ```mermaid
    classDef core fill:#dbeafe,stroke:#3b82f6,color:#111827
    classDef shared fill:#ede9fe,stroke:#8b5cf6,color:#111827,stroke-width:2px
    classDef external fill:#fef3c7,stroke:#f59e0b,color:#111827
    classDef storage fill:#dcfce7,stroke:#22c55e,color:#111827
    classDef risk fill:#fee2e2,stroke:#ef4444,color:#111827,stroke-width:2px
    ```
    *   Use dotted lines `-.->` to call out external dependencies.
    *   Use caution flags on high-risk pathways (e.g. `-.->|⚠️ Unbounded cost| API_KEY`).

### Step 3: Compile Flow Testing Matrix
Create a Markdown table documenting testing targets for subsequent phases:

| Path ID | Path Name | Priority | Entry point | Step Count | Shared Junctions | Failure Modes | Quality Test Type | Requires Real API | Benchmark Candidate |
|---------|-----------|----------|-------------|------------|------------------|---------------|-------------------|-------------------|---------------------|

*   Mark **Benchmark Candidate** as Yes/No with a short justification.
*   Write the complete matrix and diagram source snippets to `project_verification_workbench/phase2_flow_matrix.md`. Later phases must treat this file as the source of truth for P0/P1/P2 paths.

### Step 4: Documentation Integration (Safety Copy)
1.  **Do not modify the original `README.md` file.**
2.  Get the current system date in `YYYYMMDD` format and generate a 4-character random hexadecimal alphanumeric code (e.g., `a8f9`).
3.  Copy the contents of the original `README.md` and write it to a new file named:
    `README_updated_[Date]_[RandomID].md` (Example: `README_updated_20260626_f4e1.md`).
4.  Insert the generated Mermaid flowcharts and architecture diagrams into the copied file:
    *   **Directly show** the P0 flow diagram and top-level architecture diagram.
    *   **Use `<details><summary>...</summary>` tags** to collapse complex sub-graphs, P1/P2 flows, or detailed sub-architectures to keep the document readable.
    *   Prepend each diagram with a 1-sentence explanatory introduction.

---

## Output Requirements
When completing Phase 2, provide the user with the following confirmation details:
```markdown
---
本阶段生成了用户流程图（[X] 条路径，P0:[a] / P1:[b] / P2:[c]）、
架构图（[Y] 个模块）、流程矩阵（[Z] 条路径，其中 Benchmark 候选 [n] 条）。

已成功创建 README 副本文件并写入图表：
[README_updated_[Date]_[RandomID].md](file:///absolute/path/to/copied/readme)

三个关键问题需要你确认：
① 流程矩阵里的 P0 主路径是否覆盖了你最关心的核心使用场景？
② 有没有路径被标为 P1/P2 但你认为它其实是 P0？
③ Benchmark 候选路径是否包含了你最想在面试中展示的场景？

如无异议，回复「继续」；如有修改，直接告诉我。
---
```
