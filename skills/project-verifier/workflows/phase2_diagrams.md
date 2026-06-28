# Phase 2: Project Understanding, Diagrams, & Documentation Integration

## Purpose
Translate codebase logic and paths into a fixed project understanding document package, visual workflows (Mermaid format), architecture/module diagrams, a testing matrix, and an optional README optimization copy.

---

## Instructions & Steps

### Step 0: Load Phase 1 Evidence
Read `project_verification_workbench/verification_manifest.md` and `project_verification_workbench/phase1_audit.md` first. If audit evidence is missing, perform a quick non-destructive recovery pass before continuing. Set Phase 2 to `in_progress` in the manifest.

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

| Path ID | Path Name | Priority | Entry point | Step Count | Shared Junctions | Failure Modes | Quality Test Type | Requires Live Backend | AI Eval Candidate |
|---------|-----------|----------|-------------|------------|------------------|---------------|-------------------|-------------------|---------------------|

*   Mark **AI Eval Candidate** as Yes only when the path contains an AI or AI-assisted user-facing outcome and a meaningful comparison baseline. Mark non-AI paths `not_applicable` with a short justification.

### Step 4: Scope Review Gate
Before writing the document package, show the proposed P0/P1/P2 paths, diagram list, and matrix summary. Ask the user to:

1. Confirm or revise path priorities and missing flows.
2. Confirm the architecture and module diagrams to generate.
3. Choose whether the optional README update copy should be created.

Do not write the final package or README copy until this scope is approved. Record the decision in `verification_manifest.md`.

### Step 5: Generate Approved Project Understanding Package
After approval, write the complete matrix to both:
    *   `project_verification_workbench/project_understanding/flow_matrix.md` for human reading.
    *   `project_verification_workbench/phase2_flow_matrix.md` as the compatibility source of truth for Phase 3-5.

Create `project_verification_workbench/project_understanding/` and write these four Markdown documents:

1.  **`project_understanding_report.md`**
    *   Explain what the project is in plain language.
    *   List entry points, runtime commands, major modules, external integrations, state/storage locations, and top risks.
    *   Include a short "How to read this project" section for a user who is new to the codebase.
2.  **`architecture_diagrams.md`**
    *   Include the top-level technical architecture Mermaid diagram.
    *   Include module/data-flow diagrams when helpful.
    *   Explain each diagram in 1-2 sentences and call out risk joints such as file writes, shell commands, database calls, and external APIs.
3.  **`user_flows.md`**
    *   Include P0/P1/P2 user flow Mermaid diagrams.
    *   For each path, document user intent, inputs, outputs, success criteria, and failure/recovery behavior.
4.  **`flow_matrix.md`**
    *   Include the full path testing matrix from Step 3.
    *   Keep path IDs stable because later phases use them as references.

These documents are the primary human-facing project understanding package. They do not replace the README copy below and do not replace `phase2_flow_matrix.md`.

### Step 6: Optional Documentation Integration (README Safety Copy)
Run this step only when the user selected the README update copy at the scope gate.

1.  **Do not modify the original `README.md` file.**
2.  Get the current system date in `YYYYMMDD` format and generate a 4-character random hexadecimal alphanumeric code (e.g., `a8f9`).
3.  Copy the contents of the original `README.md` and write it to a new file named:
    `README_updated_[Date]_[RandomID].md` (Example: `README_updated_20260626_f4e1.md`).
4.  Insert the generated Mermaid flowcharts and architecture diagrams into the copied file:
    *   **Directly show** the P0 flow diagram and top-level architecture diagram.
    *   **Use `<details><summary>...</summary>` tags** to collapse complex sub-graphs, P1/P2 flows, or detailed sub-architectures to keep the document readable.
    *   Prepend each diagram with a 1-sentence explanatory introduction.

If the user declines the README copy, record `not requested` in the manifest and do not create `README_updated_*`.

---

## Output Requirements
When completing Phase 2, provide the user with the following confirmation details:
```markdown
---
本阶段生成了用户流程图（[X] 条路径，P0:[a] / P1:[b] / P2:[c]）、
架构图（[Y] 个模块）、流程矩阵（[Z] 条路径，其中 AI Eval 候选 [n] 条）。

已成功创建项目理解文档包：
[project_understanding_report.md](file:///absolute/path/to/project/project_verification_workbench/project_understanding/project_understanding_report.md)
[architecture_diagrams.md](file:///absolute/path/to/project/project_verification_workbench/project_understanding/architecture_diagrams.md)
[user_flows.md](file:///absolute/path/to/project/project_verification_workbench/project_understanding/user_flows.md)
[flow_matrix.md](file:///absolute/path/to/project/project_verification_workbench/project_understanding/flow_matrix.md)

[如用户选择] 已创建 README 副本并写入图表：
[README_updated_[Date]_[RandomID].md](file:///absolute/path/to/copied/readme)
[如用户未选择] README update copy：未请求，未创建。

三个关键问题需要你确认：
① 流程矩阵里的 P0 主路径是否覆盖了你最关心的核心使用场景？
② 有没有路径被标为 P1/P2 但你认为它其实是 P0？
③ AI Eval 候选路径是否对应真实且值得比较的用户价值？

请选择：回复「继续」进入 Phase 3；回复「修改」调整文档；或回复「停止」并保留当前产物。
---
```
