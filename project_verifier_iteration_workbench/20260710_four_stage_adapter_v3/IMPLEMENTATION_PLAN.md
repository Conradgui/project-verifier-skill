# Project Verifier Four-Stage Adapter V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current five-phase contract with a four-stage, project-adapted verification workflow while preserving fail-closed authorization, raw evidence, negative results, and low user decision load.

**Architecture:** Keep `SKILL.md` as the concise controller, move detailed artifact and tool contracts into one-level references, and use standard-library validators plus shell runners as the deterministic enforcement layer. Execute the task graph with fresh serial subagents when available and the same file-based contract inline when unavailable. External security and AI evaluation tools remain replaceable backends: project-specific task scripts translate tool inputs and outputs, while Project Verifier owns authorization, preflight, normalized evidence, and claims.

**Tech Stack:** Markdown Skill workflows, Python 3 standard library, Bash 3.2-compatible shell templates, JSON artifacts, `unittest`, GitHub Actions.

## Global Constraints

- Work only in `.worktrees/codex-stage-gate-quality-v2` on `codex/project-verifier-release-closeout`.
- Do not merge to `main`, push, install the Skill, install dependencies, call real APIs, or run active security scans without separate authorization.
- Preserve `phase_status`, `result_outcome`, `execution_scope`, and `claim_eligibility` as separate state dimensions.
- `preflight` must not execute a project path, target scan, external API, model, or Baseline.
- Never read, print, or persist secret values; record environment-variable names only.
- Use task-defined raw metrics and thresholds. Do not add universal scores or radar charts.
- Missing evidence, missing telemetry, empty output, runner failure, negative results, and stale evidence cannot become positive claims.
- Before Stage 2, Stage 3, or Stage 4 consumes Stage 1 facts, run the V3
  Profile handoff gate against the current source revision; an unconfirmed,
  incomplete, mismatched, or stale Profile blocks the dependent stage.
- Recommend the best-fit tool with trade-offs. If the user rejects it, disclose the fallback and reduced coverage; never silently install or downgrade.
- The user approves material product, risk, cost, sensitive-data, Baseline, metric, and public-claim decisions. The Agent owns reversible implementation details inside the approved decision envelope.
- Remove the repository `LICENSE` and README License section only in the documentation migration task.
- Detect subagent capability before Task 1. Prefer `subagent_serial`; fall back to `inline_serial` without repeated approval when scope, cost, permissions, and interpretation do not change.
- Keep implementation serial unless every parallel-safety condition in the approved design passes. The current eight-task graph is serial.
- Use controller-mediated task briefs, reports, reviews, and a durable progress ledger. Never use free-form agent-to-agent conversation as project state.
- Record `review_independence: self_review_only` when the inline fallback has no independent reviewer.
- Do not add a multi-agent orchestration framework dependency.
- When a task ports historical behavior, update `test_migration_matrix.json` in the same commit. Its test must prove complete legacy coverage and real V3 target-test existence; only Task 7 may require zero `pending` rows.

## File Responsibility Map

### Create

- `skills/project-verifier/references/artifact_contracts.md`: canonical human and machine artifact schemas, state semantics, and evidence/claim rules.
- `skills/project-verifier/references/tool_adapters.md`: project-fit selection criteria and the `detect -> propose -> preflight -> run -> normalize` adapter contract.
- `skills/project-verifier/templates/project_profile_template.json`: stable facts produced by Stage 1.
- `skills/project-verifier/templates/decision_envelope_template.json`: only material approval fields; canonical JSON is hashed.
- `skills/project-verifier/templates/benchmark_task_template.json`: dual-input claim, dataset provenance, backend, metric, and minimum-sample contract.
- `skills/project-verifier/scripts/validate_gate_v3.py`: transitional V3 validator kept beside the V2 canonical validator until Task 7.
- `skills/project-verifier/templates/verification_manifest_v3_template.json`: transitional V3 manifest kept beside the V2 canonical template until Task 7.
- `skills/project-verifier/templates/run_quality_template.sh`: V3 Stage 2 runner; the V2 usability runner remains until Task 7.
- `skills/project-verifier/templates/run_benchmark_v3_template.sh`: V3 Stage 4 runner kept beside the V2 benchmark runner until Task 7.
- `skills/project-verifier/templates/benchmark_evaluator_v3_template.py`: V3 evaluator kept beside the V2 evaluator until Task 7.
- `skills/project-verifier/templates/run_security_template.sh`: gated Stage 3 task runner with no-call preflight.
- `skills/project-verifier/templates/security_normalizer_template.py`: validate, redact, deduplicate, and summarize adapter-intermediate findings.
- `skills/project-verifier/workflows/stage1_understanding.md`: merged exploration, mapping, diagrams, flow matrix, and Profile gate.
- `skills/project-verifier/workflows/stage2_quality.md`: static quality, offline tests, runnability, Smoke, and authorized live E2E.
- `skills/project-verifier/workflows/stage3_security.md`: security applicability, tool recommendation, authorization, triage, and report flow.
- `skills/project-verifier/workflows/stage4_benchmark.md`: conditional dual-input AI Benchmark and claim review.
- `skills/project-verifier/tests/__init__.py`: standard-library test package marker.
- `skills/project-verifier/tests/helpers.py`: temporary Git fixture, JSON, command, and dynamic-module helpers.
- `skills/project-verifier/tests/test_control_plane.py`: manifest, envelope, limits, source, and write-scope tests.
- `skills/project-verifier/tests/test_contract.py`: four-stage Skill/workflow/docs/artifact consistency tests.
- `skills/project-verifier/tests/test_quality_runner.py`: Stage 2 preflight, dispatch, authorization, telemetry, and partial-result tests.
- `skills/project-verifier/tests/test_security.py`: Stage 3 preflight, authorization, normalization, deduplication, and redaction tests.
- `skills/project-verifier/tests/test_benchmark.py`: raw evaluator, dual inputs, backend metadata, sample sufficiency, and claim-status tests.
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json`: machine-checked mapping from every historical executable test to a retained V3 test or a documented retired five-phase assertion.
- `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/verification_report.md`: final executed checks, results, limitations, and deferred Agent behavior Eval.

### Promote Atomically in Task 7

- `skills/project-verifier/scripts/validate_gate_v3.py` -> `skills/project-verifier/scripts/validate_gate.py` after the V2 file is removed.
- `skills/project-verifier/templates/verification_manifest_v3_template.json` -> `verification_manifest_template.json` after the V2 file is removed.
- `skills/project-verifier/templates/run_benchmark_v3_template.sh` -> `run_benchmark_template.sh` after the V2 file is removed.
- `skills/project-verifier/templates/benchmark_evaluator_v3_template.py` -> `benchmark_evaluator_template.py` after the V2 file is removed.
- Remove `run_usability_template.sh`; `run_quality_template.sh` is already the final V3 filename.
- `skills/project-verifier/evals/fixtures/stale_authorization/phase4_live_execution.json` -> `stage2_live_execution.json`.
- `skills/project-verifier/evals/fixtures/stale_authorization/phase4_usability_plan.md` -> `stage2_quality_plan.md`.
- `skills/project-verifier/evals/fixtures/stale_authorization/verification_manifest_v3.json` -> `verification_manifest.json` after the V2 manifest is removed.

### Modify

- `skills/project-verifier/SKILL.md`: concise four-stage controller and progressive-disclosure links.
- `skills/project-verifier/workflows/optional_interview_export.md`: current-revision four-stage source map and neutral claim approval.
- `skills/project-verifier/agents/openai.yaml`: four-stage, script-first, evidence-backed prompt.
- `skills/project-verifier/evals/evals.json` and six fixture descriptors: V3 stage names and expected decisions.
- `README.md`: four-stage user model, Stage Gate, outputs, boundaries, private-use scope, and current validation command.
- `.github/workflows/offline-validation.yml`: run consolidated V3 `unittest`, syntax, compile, JSON, metadata, and whitespace checks.
- `bootstrap.sh`, `AGENTS.md`, `CONTRIBUTING.md`: only if a stale LICENSE, five-phase, or removed path reference is found.

### Delete After Replacements Exist

- `skills/project-verifier/workflows/phase1_explore.md`
- `skills/project-verifier/workflows/phase2_diagrams.md`
- `skills/project-verifier/workflows/phase3_quality.md`
- `skills/project-verifier/workflows/phase4_usability.md`
- `skills/project-verifier/workflows/phase5_benchmark.md`
- `LICENSE`

Historical iteration reports remain unchanged. Executable historical test fixtures remain unchanged except for the Task 1 baseline-repair entry below: it adds the already-required `rubric_approved: true` field to `BM_002`, restoring the current evaluator/test contract without weakening any Gate. Transitional `*_v3*` files exist only to keep current V2 CI green during Tasks 1-6 and are promoted to canonical names in Task 7 after the complete V3 suite passes.

### Runtime Orchestration Artifacts

During this repository implementation, controller artifacts live under `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution/` and are committed with the iteration evidence. When the finished Skill later verifies a target project, the same contract uses:

```text
project_verification_workbench/agent_execution/
├── execution_manifest.json
├── progress.md
├── task-N-brief.md
├── task-N-report.md
├── task-N-review.md
└── review-packages/
```

`execution_manifest.json` records `execution_backend`, capability detection, active task, dependency graph, review independence, source identity, and backend transitions. The ledger prevents completed tasks from being repeated after context compaction or fallback.

## Execution Orchestration Contract

1. Before Task 1, detect `spawn_agent`, `wait_agent`, and reviewer capability. Record `subagent_serial` or `inline_serial`.
2. Execute the approved graph serially. Parallel dispatch requires no dependency edge, disjoint writes, no shared contract ownership, isolated/read-only execution, defined integration ownership, and failure independence.
3. The controller is the only role that communicates material questions to the user.
4. Each implementer receives one extracted task brief, global constraints, consumed interfaces, allowed paths, forbidden actions, source identity, and report path.
5. Implementers report `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED` and persist exact test evidence.
6. A fresh reviewer reads the brief, report, and actual diff. It returns separate `spec_compliance` and `code_quality` verdicts.
7. Critical or important findings require one fix wave and re-review before progress advances.
8. The controller verifies Git and test evidence independently of agent summaries and appends the progress ledger only after approval.
9. If subagent execution becomes unavailable, finish or safely stop the active task, record the transition, resume inline at the first incomplete task, and do not re-run completed tasks.
10. If no independent reviewer remains, disclose `review_independence: self_review_only`; deterministic tests still run, but the report cannot claim independent review.
11. Before every commit, stage only that task's declared files, inspect `git diff --cached --name-only`, and stop if unrelated paths are present.

---

### Task 1: Add the V3 Contract Test Harness

**Why:** Establish a current standard-library test entrypoint and a machine-checked migration ledger without rewriting historical workbench evidence or committing a long-lived RED suite.

**Files:**
- Create: `skills/project-verifier/tests/__init__.py`
- Create: `skills/project-verifier/tests/helpers.py`
- Create: `skills/project-verifier/tests/test_contract.py`
- Create: `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json`
- Modify: `project_verifier_iteration_workbench/20260626_skill_hardening/template_behavior_tests.py` only to add `rubric_approved: true` to the existing `BM_002` task definition

**Interfaces:**
- Produces: `run(command: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess`
- Produces: `write_json(path: Path, payload: dict) -> None`
- Produces: `read(path: Path) -> str`
- Test entrypoint: `python3 -m unittest discover -s skills/project-verifier/tests -p 'test_*.py' -v`

- [ ] **Step 1: Write a failing helper round-trip test**

Create `test_contract.py` first:

```python
import tempfile
import unittest
from pathlib import Path

from helpers import read, write_json

class HarnessTests(unittest.TestCase):
    def test_json_helper_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json"
            write_json(path, {"value": 1})
            self.assertIn('"value": 1', read(path))
```

- [ ] **Step 2: Run the test and confirm RED**

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_contract.py' -v
```

Expected: import failure because `helpers.py` does not exist.

- [ ] **Step 3: Create shared test helpers and turn the test GREEN**

```python
from __future__ import annotations

import json
import importlib.util
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills/project-verifier"

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run(command: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env or os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
```

- [ ] **Step 4: Create and validate the machine-readable migration matrix**

Create `test_migration_matrix.json` with one entry per historical `test_*` function:

```json
{
  "schema_version": "1.0",
  "retired_contract_allowlist": [],
  "entries": [
    {
      "legacy_id": "project_verifier_iteration_workbench/20260629_stage_gate_quality_v2/stage_gate_v2_tests.py::test_manifest_template_separates_state_dimensions",
      "status": "pending",
      "v3_test": null,
      "reason": "Ported when the V3 control-plane test is added in Task 2"
    }
  ]
}
```

Add tests that use `ast` to enumerate all `test_*` functions in the four historical suites and assert:

- every legacy ID appears exactly once;
- status is `pending / ported / covered_by / retired_contract`;
- `ported` and `covered_by` rows name a real V3 test function found by AST;
- `retired_contract` is accepted only when its exact legacy ID appears in `retired_contract_allowlist`;
- only `pending` rows may omit `v3_test` before Task 7.

For this V3 migration, `retired_contract_allowlist` is empty. Every historical test must therefore map to a real V3 test. Tests that mix obsolete numbering with still-valid credibility assertions are ported or split, never retired as a whole.

Use this exact enumeration command to audit the generated row count:

```bash
python3 - <<'PY'
import ast
from pathlib import Path

paths = [
    Path("project_verifier_iteration_workbench/20260626_skill_hardening/template_behavior_tests.py"),
    Path("project_verifier_iteration_workbench/20260628_conditional_eval_gates/workflow_contract_tests.py"),
    Path("project_verifier_iteration_workbench/20260629_stage_gate_quality_v2/stage_gate_v2_tests.py"),
    Path("project_verifier_iteration_workbench/20260630_lean_core_simplification/lean_core_contract_tests.py"),
]
names = []
for path in paths:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names.extend(f"{path}::{node.name}" for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
print(len(names))
print("\n".join(sorted(names)))
PY
```

- [ ] **Step 5: Run the current V3 suite GREEN**

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_*.py' -v
```

Expected: all current V3 harness and matrix checks pass. No final four-stage assertion is added until its owning implementation task, so the suite does not remain RED between commits.

The Task 1 baseline repair preserves the current evaluator Gate: add `rubric_approved: true` only to the existing `BM_002` task definition. Do not change Evaluator code, assertions, historical reports, or unrelated fixtures.

- [ ] **Step 6: Confirm existing CI consumers still pass**

Run the four historical commands currently listed in `.github/workflows/offline-validation.yml`. Expected: all pass because Task 1 changes no canonical V2 consumer.

- [ ] **Step 7: Stage only Task 1 files and commit GREEN**

```bash
git add skills/project-verifier/tests
git add project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json
git add project_verifier_iteration_workbench/20260626_skill_hardening/template_behavior_tests.py
git diff --cached --name-only
git commit -m "test: define project verifier v3 contract"
```

The staged list must contain only the Task 1 files. If any pre-existing staged path appears, stop and repair the index before committing.

---

### Task 2: Replace Full-Plan Hashing With Decision Envelopes

**Why:** This is the P0 control-plane change. Formatting or log-path edits must not revoke approval, while risk, interpretation, source, and upper-limit changes must still fail closed.

**Files:**
- Create: `skills/project-verifier/templates/decision_envelope_template.json`
- Create: `skills/project-verifier/templates/project_profile_template.json`
- Create: `skills/project-verifier/references/artifact_contracts.md`
- Create: `skills/project-verifier/tests/test_control_plane.py`
- Create: `skills/project-verifier/scripts/validate_gate_v3.py`
- Create: `skills/project-verifier/templates/verification_manifest_v3_template.json`

**Interfaces:**
- `canonical_object_hash(payload: dict) -> str`
- `validate_decision_envelope(envelope: dict) -> None`
- `requested_limit_is_within(approved: object, requested: object) -> bool`
- CLI: `validate_gate_v3.py check --manifest <manifest.json> --receipt <receipt.json> --envelope <decision-envelope.json> --source-revision <fingerprint> --stage <stage-id> --decision-type <type> [--limit key=value] [--project-root <project>]`
- CLI: `validate_gate_v3.py fingerprint --root <project>` preserves secret-safe fingerprint behavior.
- CLI: `validate_gate_v3.py paths --manifest <manifest.json> --changed-file <relative-path>` remains fail-closed.
- CLI: `validate_gate_v3.py profile --manifest <manifest.json> --profile <project_profile.json> --project-root <project>` validates Stage 1 handoff before a later stage consumes Profile facts.

The authorization receipt fields are exactly:

```text
decision_id
stage
decision_type
decision_envelope_sha256
source_revision
user_choice
approved_limits
approved_at
invalidated_at
```

`source_revision` is the approved base fingerprint. Under `source_policy.mode=exact`, it must equal the current fingerprint. Under `approved_fix_scope`, the current fingerprint may differ only when Git independently proves every changed path is inside `allowed_fix_paths`; the returned gate result records both base and current fingerprints.

- [ ] **Step 1: Write failing canonical-envelope tests**

Test these exact cases in `test_control_plane.py`:

The first four tests directly call the validator helpers:

```python
from helpers import SKILL_ROOT, load_module

VALIDATOR_MODULE = load_module(SKILL_ROOT / "scripts/validate_gate_v3.py", "v3_gate")
canonical_object_hash = VALIDATOR_MODULE.canonical_object_hash
requested_limit_is_within = VALIDATOR_MODULE.requested_limit_is_within

class DecisionEnvelopeUnitTests(unittest.TestCase):
    def test_json_formatting_does_not_change_envelope_hash(self):
        payload = {"stage": "stage2", "limits": {"timeout_seconds": 10}}
        formatted_copy = json.loads(json.dumps(payload, indent=4))
        self.assertEqual(canonical_object_hash(payload), canonical_object_hash(formatted_copy))

    def test_material_field_change_invalidates_receipt(self):
        approved = {"scope": {"network": False}}
        changed = {"scope": {"network": True}}
        self.assertNotEqual(canonical_object_hash(approved), canonical_object_hash(changed))

    def test_lower_numeric_execution_limit_is_allowed(self):
        self.assertTrue(requested_limit_is_within(10, 5))

    def test_higher_numeric_execution_limit_is_rejected(self):
        self.assertFalse(requested_limit_is_within(10, 11))
```

CLI fixture tests then cover missing/duplicate manifest decisions, exact-source rejection, approved-fix acceptance for only Git-verified paths, dirty-base rejection, and absence of secret-value fields in templates. Each negative case asserts a nonzero exit and the specific failure category.

Use a clean temporary Git repository for source-policy tests. Cover all source states:

- an allowed working-tree change to `src/approved.py` passes;
- an allowed staged change to `src/approved.py` passes;
- a new commit containing only `src/approved.py` passes;
- a new commit containing `config/prod.yml` fails even when the working tree is clean;
- an untracked out-of-scope file fails;
- a non-ancestor base commit fails closed.

- [ ] **Step 2: Run the control-plane tests and confirm RED**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_control_plane.py' -v
```

Expected: import or CLI failures because envelope functions and schema `3.0` do not exist.

- [ ] **Step 3: Define the decision envelope template**

Create a template with this material surface:

```json
{
  "schema_version": "1.0",
  "stage": "stage2",
  "decision_type": "live_e2e",
  "source_policy": {
    "mode": "exact",
    "base_revision": "unknown",
    "allowed_fix_paths": []
  },
  "scope": {
    "path_ids": [],
    "targets": [],
    "write_scope": ["project_verification_workbench"],
    "network": false,
    "credential_names": [],
    "sensitive_data": false,
    "side_effects": []
  },
  "interpretation": {
    "claim": null,
    "baseline": null,
    "dataset_id": null,
    "metric_ids": []
  },
  "limits": {}
}
```

The receipt stores `decision_envelope_sha256`, not a hash of a Markdown/plan file.

- [ ] **Step 4: Implement canonical JSON hashing and limit containment**

Add to `validate_gate_v3.py`:

```python
def canonical_object_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def requested_limit_is_within(approved, requested):
    if isinstance(approved, bool) or isinstance(requested, bool):
        return approved is requested
    if isinstance(approved, (int, float)) and isinstance(requested, (int, float)):
        return requested <= approved
    return requested == approved
```

Require exact equality for strings, booleans, lists, and objects. Allow only lower-or-equal numeric maxima.

- [ ] **Step 5: Implement the two source policies**

- `exact`: current fingerprint must equal the envelope base revision.
- `approved_fix_scope`: base revision must be `git:<commit>` and that commit must be an ancestor of `HEAD`. Use `git diff --name-only <base-commit> -- .` to cover committed `HEAD`, index, and working-tree changes relative to the base, then add `git ls-files --others --exclude-standard` for untracked files. Normalize and require every resulting path to be within `allowed_fix_paths`.
- A dirty fingerprint cannot be used as the base for `approved_fix_scope`; return a clear renewal condition.
- Do not compare the receipt's base fingerprint to the current fingerprint unconditionally. The source-policy branch owns that decision.
- The manifest records the new fingerprint and marks affected prior artifacts stale, but the old decision ID remains the authority for the unchanged objective.

- [ ] **Step 6: Create the V3 manifest beside the V2 canonical template**

Use `stages.stage1` through `stages.stage4`, keep the four state dimensions, and add:

```json
"source_history": [],
"project_profile": {
  "path": "project_verification_workbench/project_profile.json",
  "status": "pending",
  "approved_fields_sha256": null
}
```

Do not retain duplicate `phases` and `stages` structures inside the V3 template. Keep the V2 canonical template unchanged until Task 7 so current CI remains valid.

- [ ] **Step 7: Define the stable Profile template and artifact reference**

The Profile contains source identity, reviewed scope, runtimes, entry points, P0/P1/P2 paths, modules, state changes, trust boundaries, sensitive-data categories, feature-level AI classification, existing capabilities, evidence references, inferences, and unknowns. It contains no commands, tool choices, secret values, or transient execution limits.

- [ ] **Step 8: Run control-plane tests GREEN**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_control_plane.py' -v
```

Expected: all decision-envelope, source-policy, state, and write-scope tests pass.

Then run the complete current V3 suite and the four historical CI commands. Expected: all pass; Task 2 has not modified a canonical V2 consumer.

- [ ] **Step 9: Commit the control plane**

```bash
git add skills/project-verifier/scripts/validate_gate_v3.py \
  skills/project-verifier/templates/verification_manifest_v3_template.json \
  skills/project-verifier/templates/decision_envelope_template.json \
  skills/project-verifier/templates/project_profile_template.json \
  skills/project-verifier/references/artifact_contracts.md \
  skills/project-verifier/tests/test_control_plane.py \
  project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json
git diff --cached --name-only
git commit -m "feat: add decision-envelope control plane"
```

---

### Task 3: Build Stage 1 Understanding and the Project Profile Gate

**Files:**
- Create: `skills/project-verifier/workflows/stage1_understanding.md`
- Modify: `skills/project-verifier/tests/test_contract.py`
- Modify: six `skills/project-verifier/evals/fixtures/*/fixture.json` files

**Interfaces:**
- Produces: `project_verification_workbench/project_report.md`
- Produces: `project_verification_workbench/flow_matrix.md`
- Produces: `project_verification_workbench/project_profile.json`
- Gate: user confirms goal, P0 paths, factual corrections, and interpretation-changing Profile fields once.

- [ ] **Step 1: Add failing Stage 1 artifact and boundary tests**

Assert that Stage 1:

- records checked files, excluded directories, unreviewed areas, and coverage limitations;
- uses repository-wide inventory plus risk-based deep reading, not a false line-by-line completeness claim;
- classifies AI capability per feature;
- binds every flow to source evidence;
- embeds architecture, module/data-flow, user-flow, and failure-recovery Mermaid source in `project_report.md`;
- does not write production source or read secret values;
- separates facts, inferences, and unknowns in the Profile.

- [ ] **Step 2: Run the Stage 1 contract test and confirm RED**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_contract.py' -v
```

Expected: fail because `stage1_understanding.md` does not exist.

- [ ] **Step 3: Write the Stage 1 workflow**

The workflow sequence is:

1. capture user goal, success criteria, scope, exclusions, and risk tolerance;
2. fingerprint source and initialize the manifest;
3. inventory the repository and publish a reading plan for large repositories;
4. trace entry points, modules, state, dependencies, trust boundaries, user paths, and recovery paths;
5. draft the report, flow matrix, and stable Profile;
6. show one concise confirmation containing P0 paths and interpretation-changing unknowns;
7. hash approved Profile fields and mark Stage 1 complete.

- [ ] **Step 4: Update fixture descriptors with feature-level facts**

Each fixture records `feature_classification`, `entry_points`, `path_ids`, `trust_boundaries`, and `expected_capabilities`. Do not add expected conclusions that are absent from fixture code.

- [ ] **Step 5: Run Stage 1 tests GREEN**

Run the targeted contract test, then parse all fixture JSON files:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_contract.py' -v
python3 -c 'import json; from pathlib import Path; paths=list(Path("skills/project-verifier/evals/fixtures").rglob("*.json")); [json.loads(path.read_text(encoding="utf-8")) for path in paths]; print(f"parsed {len(paths)} fixture json files")'
```

Run the complete current V3 suite and four historical CI commands. Expected: all pass.

- [ ] **Step 6: Commit Stage 1**

```bash
git add skills/project-verifier/workflows/stage1_understanding.md \
  skills/project-verifier/tests/test_contract.py \
  skills/project-verifier/evals/fixtures \
  project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json
git diff --cached --name-only
git commit -m "feat: add project understanding profile stage"
```

---

### Task 4: Merge Quality, Runnability, Smoke, and Live E2E Into Stage 2

**Files:**
- Create: `skills/project-verifier/templates/run_quality_template.sh` while retaining `run_usability_template.sh` for V2 CI until Task 7
- Create: `skills/project-verifier/workflows/stage2_quality.md`
- Create: `skills/project-verifier/tests/test_quality_runner.py`
- Create Stage 2 copies of the stale-authorization fixture files while retaining V2 fixture paths until Task 7
- Modify: `skills/project-verifier/tests/test_contract.py`

**Interfaces:**
- Runner: `bash run_quality.sh preflight|run`
- Gate: `stage2 / live_e2e`
- Envelope limits: `max_paths`, `max_calls_per_path`, `max_retries`, `timeout_seconds`
- Produces: `quality_report.md`, `phase2_quality_plan.json`, `phase2_quality_plan.md`, `phase2_quality_results.json`

- [ ] **Step 1: Port existing runner tests and add Stage 2 boundary tests**

Cover:

- no argument prints help and executes nothing;
- `preflight` checks environment names, files, commands, runtimes, task count, and bounds without running scripts;
- `.py`, `.sh`, and `.ts` dispatch remains correct;
- `run` rejects missing, stale, material-change, and over-limit authorization;
- a lower timeout/call limit remains valid;
- offline mode blocks network and uses fixture/mock oracles;
- production source cannot be changed under the test-only write scope;
- pass rate is never labeled code coverage;
- partial path failure yields `phase_status: completed`, `result_outcome: partial`;
- missing call/retry/side-effect telemetry yields `inconclusive`.

- [ ] **Step 2: Run Stage 2 tests RED**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_quality_runner.py' -v
```

Expected: failures because the new runner and Stage 2 envelope interface do not exist.

- [ ] **Step 3: Create the runner from the mature V2 behavior and migrate identifiers**

Mechanically preserve tested dispatch and telemetry behavior while replacing:

- `USABILITY_*` with `QUALITY_*`;
- `tests/usability` with `tests/quality-e2e`;
- `phase4_usability_*` with `phase2_quality_*`;
- gate `phase4/live_execution` with `stage2/live_e2e`;
- `--proposal` with `--envelope`.

Point the runner to `validate_gate_v3.py`. Do not modify or remove `run_usability_template.sh` in this task.

The runner must not execute offline unit tests itself; it runs only approved Smoke/live path scripts. The workflow runs project-native lint/build/unit/integration commands separately and records them in the same Stage 2 report.

- [ ] **Step 4: Write the Stage 2 workflow**

Keep one user gate for the selected quality scope. Ask again only for production fixes, dependency installation, live calls, sensitive data, or changed external side effects. Existing project commands are preferred; generated tests live outside production source unless a source-fix envelope is separately approved.

- [ ] **Step 5: Add V3 stale-authorization fixture copies**

Create `stage2_live_execution.json`, `stage2_quality_plan.md`, and `verification_manifest_v3.json` using schema `3.0` and a decision-envelope hash. Keep the V2 `phase4_*` files and `verification_manifest.json` unchanged until Task 7. The V3 fixture must prove stale or material-change rejection without running a path.

- [ ] **Step 6: Run Stage 2 tests GREEN and shell syntax**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_quality_runner.py' -v
bash -n skills/project-verifier/templates/run_quality_template.sh
bash skills/project-verifier/templates/run_quality_template.sh
```

The no-argument invocation must print help and exit zero. Then run the complete current V3 suite and four historical CI commands; all must pass.

- [ ] **Step 7: Commit Stage 2**

```bash
git add skills/project-verifier/templates/run_quality_template.sh \
  skills/project-verifier/workflows/stage2_quality.md \
  skills/project-verifier/tests/test_quality_runner.py \
  skills/project-verifier/tests/test_contract.py \
  skills/project-verifier/evals/fixtures/stale_authorization \
  project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json
git diff --cached --name-only
git commit -m "feat: combine quality and live verification"
```

---

### Task 5: Add the Project-Fit Security Boundary Adapter

**Why:** Security must be a real, bounded verification stage, not a generic instruction to download one scanner.

**Files:**
- Create: `skills/project-verifier/workflows/stage3_security.md`
- Create: `skills/project-verifier/references/tool_adapters.md`
- Create: `skills/project-verifier/templates/run_security_template.sh`
- Create: `skills/project-verifier/templates/security_normalizer_template.py`
- Create: `skills/project-verifier/tests/test_security.py`
- Modify: `skills/project-verifier/tests/test_contract.py`

**Interfaces:**
- Runner: `bash run_security.sh preflight|run`
- Gate: `stage3 / security_execution`
- Task scripts: `security/tasks/security_P0_*.py|.sh`
- Adapter-intermediate input: `{ "tool": {"name": "semgrep", "version": "1.0"}, "findings": [] }`
- Normalized output: `{ "status", "tools", "findings", "deduplication", "limitations" }`
- Finding fields: `finding_id`, `category`, `severity`, `confidence`, `triage_status`, `source_location`, `affected_user_path`, `evidence`, `exploit_preconditions`, `tool_and_version`, `recommended_action`, `verification_method`, `limitations`.

- [ ] **Step 1: Write failing security tests**

Test:

- detection does not install or scan;
- preflight validates tools, task scripts, targets, output paths, and permissions without target execution;
- installed offline read-only tasks may batch under one approved envelope;
- download, vulnerability DB update, network, passive dynamic scan, and active scan cannot inherit one another's permission;
- active scan rejects non-local/non-isolated targets;
- missing tool produces a recommendation/fallback record, not silent installation;
- raw findings are preserved;
- duplicate findings collapse only when category, rule identity, and source location match;
- secret-like fields (`secret_value`, `match`, `raw_secret`, `token`) are replaced with `[REDACTED]` before normalized output;
- a clean result states only that no issue was found in executed scope;
- no security score is generated.

- [ ] **Step 2: Run security tests RED**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_security.py' -v
```

- [ ] **Step 3: Write the adapter reference**

Document project-fit comparison dimensions: language/file coverage, source versus dependency versus secret versus configuration scope, offline capability, output format, maintenance, version pinning, install cost, network/database behavior, target risk, and known blind spots.

Document optional backends without making them dependencies:

- Semgrep for source patterns;
- OSV-Scanner or Trivy for dependency/SBOM vulnerabilities;
- Gitleaks for secret scanning;
- ZAP for separately authorized passive/active Web/API testing;
- project-native scanners when they provide equal or better fit.

- [ ] **Step 4: Implement the security runner**

Mirror the mature quality runner's fail-closed structure. `preflight` may inspect files and `command -v`; it must not run scanner targets. `run` validates the Stage 3 envelope and limits before dispatching task scripts. Record command identity, exit code, duration, raw output path, network/active mode, target, side effects, and authorization ID.

Invoke `validate_gate_v3.py` and document runner usage as `bash run_security.sh preflight|run`; do not depend on an executable file mode.

- [ ] **Step 5: Implement normalization without tool SDKs**

Require project bridges to emit the adapter-intermediate schema. The normalizer validates fields, redacts denied secret keys recursively, creates deterministic IDs when absent, deduplicates exact finding identities, and leaves uncertain triage as `needs_review`. It does not infer exploitability or convert scanner severity into a project-wide score.

- [ ] **Step 6: Write the Stage 3 workflow**

The workflow:

1. derives relevant surfaces from the Profile and user paths;
2. compares existing and recommended tools;
3. shows one concise tool/scope/permission decision;
4. creates plan JSON plus a human summary;
5. runs no-target preflight;
6. requests separate authorization only for newly introduced high-risk capabilities;
7. normalizes, links, and asks the user to confirm triage for interpretation-changing findings;
8. writes `security_report.md` and results JSON with limitations.

- [ ] **Step 7: Run security tests GREEN**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_security.py' -v
bash -n skills/project-verifier/templates/run_security_template.sh
bash skills/project-verifier/templates/run_security_template.sh
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 -m py_compile skills/project-verifier/templates/security_normalizer_template.py
```

The no-argument runner must print help and exit zero. Then run the complete current V3 suite and four historical CI commands; all must pass.

- [ ] **Step 8: Commit Stage 3**

```bash
git add skills/project-verifier/workflows/stage3_security.md \
  skills/project-verifier/references/tool_adapters.md \
  skills/project-verifier/templates/run_security_template.sh \
  skills/project-verifier/templates/security_normalizer_template.py \
  skills/project-verifier/tests/test_security.py \
  skills/project-verifier/tests/test_contract.py \
  project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json
git diff --cached --name-only
git commit -m "feat: add security boundary verification adapter"
```

---

### Task 6: Rebuild Stage 4 as a Dual-Input, Backend-Neutral AI Benchmark

**Files:**
- Create: `skills/project-verifier/workflows/stage4_benchmark.md`
- Create: `skills/project-verifier/templates/benchmark_task_template.json`
- Create: `skills/project-verifier/tests/test_benchmark.py`
- Create: `skills/project-verifier/templates/run_benchmark_v3_template.sh`
- Create: `skills/project-verifier/templates/benchmark_evaluator_v3_template.py`
- Modify: `skills/project-verifier/references/tool_adapters.md`
- Modify: `skills/project-verifier/tests/test_contract.py`

**Interfaces:**
- Gate: `stage4 / benchmark_execution`
- Runner modes: `preflight`, `pilot <task_id>`, `full`
- Backends: `built_in`, `promptfoo`, `deepeval`, `ragas`, `inspect`, or an explicitly named project-native adapter.
- Final claim status: `supported`, `partially_supported`, `not_supported`, or `inconclusive`.

- [ ] **Step 1: Port raw-evaluator regressions and add V3 Benchmark tests**

Retain tests for rubric approval, empty output, task mismatch, nonzero exit, full versus pilot, minimum samples, repeated runs, existing evidence files, malformed/non-finite evidence, blinded Judge, no Judge-only safety claim, and no HTML/radar/score.

Add tests that require:

- evidence-derived characteristics and user highlight direction as separate inputs;
- 3-5 evidence-grounded proposals before user selection;
- selected characteristic, falsifiable claim, user path/value, Baseline, dataset provenance, metrics, budget, and stop conditions in the final plan;
- sample labels limited to `real`, `existing_test`, `user_confirmed`, `synthetic_candidate`;
- synthetic candidates excluded from ground truth without deterministic oracle or user confirmation;
- backend name/version/configuration and fallback limitation in task/result evidence;
- equivalent Tool/Baseline inputs and resources or an explicit deviation;
- negative and inconclusive outcomes preserved;
- full plan review before pilot/full authorization.

- [ ] **Step 2: Run Benchmark tests RED**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_benchmark.py' -v
```

- [ ] **Step 3: Define the Benchmark task template**

The template contains:

```json
{
  "schema_version": "3.0",
  "task_id": "BM_001",
  "feature_id": "unknown",
  "characteristic_source": "evidence",
  "user_selected_direction": "unknown",
  "comparison_claim": "unknown",
  "decision_use": "unknown",
  "user_path_ids": [],
  "backend": {"name": "built_in", "version": "unknown", "fallback_reason": null},
  "baseline": {"type": "unknown", "identity": "unknown", "equivalence_deviations": []},
  "dataset": {"dataset_id": "unknown", "sha256": "unknown", "samples": []},
  "rubric_approved": false,
  "metrics": [],
  "execution": {"mode": "plan_only", "minimum_samples": 1, "max_calls": 0, "max_retries": 0, "timeout_seconds": 0}
}
```

- [ ] **Step 4: Strengthen runner preflight and migrate Stage 4 paths**

Validate task identity, backend metadata, comparison claim, dataset sample provenance, metric contracts, execution bounds, and executor presence without invoking any backend. Replace Phase 5 paths and gate identifiers with Stage 4 and `--envelope`.

Build the V3 files beside the canonical V2 runner/evaluator and point the V3 runner to `validate_gate_v3.py`. Do not modify the V2 canonical files until Task 7.

- [ ] **Step 5: Add evidence-first claim status to the evaluator**

Add:

Each claim-bearing metric defines an approved comparison contract such as `{"operator": ">=", "minimum_margin": 0.05}`. Compute `comparison_met` from Tool and Baseline raw values, then aggregate only those approved comparisons:

```python
def claim_status(metric_results):
    outcomes = [item.get("comparison_met") for item in metric_results]
    if not outcomes or any(value is None for value in outcomes):
        return "inconclusive"
    if all(outcomes):
        return "supported"
    if any(outcomes):
        return "partially_supported"
    return "not_supported"
```

Individual success thresholds remain visible but do not by themselves prove Tool superiority. Report claim status as a summary of approved metric comparisons, not a universal score.

- [ ] **Step 6: Write the guided Stage 4 workflow**

The Agent performs evidence extraction and proposal drafting without asking the user about technical minutiae. The user makes two decisions: direction selection and final plan approval. Any new real calls, cost, sensitive data, Baseline meaning, dataset scope, or metric meaning requires renewal; file layout, backend glue, report wording, and lower limits do not.

- [ ] **Step 7: Run Benchmark tests GREEN**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_benchmark.py' -v
bash -n skills/project-verifier/templates/run_benchmark_v3_template.sh
bash skills/project-verifier/templates/run_benchmark_v3_template.sh
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 -m py_compile skills/project-verifier/templates/benchmark_evaluator_v3_template.py
```

The no-argument runner must print help and exit with its documented usage status without executing a backend. Then run the complete current V3 suite and four historical CI commands; all must pass.

- [ ] **Step 8: Commit Stage 4**

```bash
git add skills/project-verifier/workflows/stage4_benchmark.md \
  skills/project-verifier/templates/benchmark_task_template.json \
  skills/project-verifier/templates/run_benchmark_v3_template.sh \
  skills/project-verifier/templates/benchmark_evaluator_v3_template.py \
  skills/project-verifier/references/tool_adapters.md \
  skills/project-verifier/tests/test_benchmark.py \
  skills/project-verifier/tests/test_contract.py \
  project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json
git diff --cached --name-only
git commit -m "feat: add dual-input ai benchmark stage"
```

---

### Task 7: Switch the Public Contract to Four Stages and Remove Obsolete Files

**Files:**
- Modify: `skills/project-verifier/SKILL.md`
- Modify: `skills/project-verifier/workflows/optional_interview_export.md`
- Modify: `skills/project-verifier/agents/openai.yaml`
- Modify: `skills/project-verifier/evals/evals.json`
- Modify: `README.md`
- Modify: `.github/workflows/offline-validation.yml`
- Modify: `skills/project-verifier/tests/test_control_plane.py`
- Modify: `skills/project-verifier/tests/test_quality_runner.py`
- Modify: `skills/project-verifier/tests/test_security.py`
- Modify: `skills/project-verifier/tests/test_benchmark.py`
- Modify: `skills/project-verifier/templates/run_quality_template.sh`
- Modify: `skills/project-verifier/templates/run_security_template.sh`
- Modify if stale: `bootstrap.sh`, `AGENTS.md`, `CONTRIBUTING.md`
- Delete: five `skills/project-verifier/workflows/phase*.md` files
- Delete: `LICENSE`
- Replace V2 canonical validator, manifest, benchmark runner, and evaluator with their tested V3 transitional files
- Delete: `skills/project-verifier/templates/run_usability_template.sh`
- Rename V3 stale-authorization fixture copies to the final Stage 2 contract after removing V2 copies
- Modify: `skills/project-verifier/tests/test_contract.py`

**Interfaces:**
- `SKILL.md` remains below 500 lines and loads detailed references only when needed.
- Description starts with `Use when` and describes trigger conditions only.
- User-facing stages are exactly Stage 1-4; optional README/interview exports remain outside verification stages.

- [ ] **Step 1: Expand the contract tests before deleting old files**

Assert:

- exactly four current workflow files and no current `phase*.md` files;
- README, SKILL, agent prompt, eval expectations, templates, and manifest use the same Stage numbers and artifact names;
- human default files are `project_report.md`, `flow_matrix.md`, `quality_report.md`, `security_report.md`, and conditional `benchmark_report.md`;
- optional exports cite current workbench evidence and need claim approval;
- README states what the Skill cannot prove;
- no LICENSE section/link/file remains;
- no current claim promises complete audit, penetration-test coverage, compliance, vulnerability absence, stable Agent gate compliance, or guaranteed Benchmark advantage;
- no recording/replay, production-browser, multi-host guard platform, default score, or radar contract returns.
- orchestration defaults to serial subagents, has an inline fallback, persists task handoffs, and discloses review independence without adding a framework dependency.
- `test_migration_matrix.json` contains no `pending` row, every historical test is mapped exactly once, and every `ported/covered_by` target exists in the V3 suite.
- no current Skill, runner, test, fixture, or CI file references a runtime `*_v3*` path after canonical promotion.

- [ ] **Step 2: Run contract tests RED**

Run:

```bash
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_contract.py' -v
```

- [ ] **Step 3: Rewrite `SKILL.md` as the concise controller**

Keep only:

- identity and trigger boundaries;
- script-first, evidence-first, quality-first, and small-decision-surface rules;
- four state dimensions and decision-envelope gate;
- four-stage index and required human outputs;
- optional exports;
- credibility boundaries and common failures;
- direct links to `references/artifact_contracts.md` and `references/tool_adapters.md`.

Do not duplicate detailed schemas or tool-by-tool commands in `SKILL.md`.

- [ ] **Step 4: Rewrite README around the user's actual decisions**

README sections:

1. Project Understanding & Evidence-Backed Verification positioning;
2. four-stage diagram;
3. one Stage Gate table showing user decisions, Agent autonomy, exit evidence, and fallback;
4. default human outputs and machine evidence;
5. script-first and project adapter explanation;
6. conditional tool recommendations and explicit fallback;
7. what the Skill does not prove;
8. subagent capability detection, serial scheduling, inline fallback, structured handoffs, and the boundary that self-review is not independent review;
9. installation/use, optional Codex Hook, repository structure, and current validation command.

Remove public-release marketing and the License section. Do not claim the repository is open-source release-ready.

- [ ] **Step 5: Update metadata, eval scenarios, and optional exports**

The default prompt asks the Agent to understand, profile, verify quality, assess security boundaries, and conditionally Benchmark AI features using guided gates. Six eval scenarios remain: non-AI, missing credentials, local AI backend, mixed AI-assisted, stale authorization, and partial E2E failure. Update only their stage names and V3 decision expectations.

- [ ] **Step 6: Promote V3 canonical files and delete obsolete files atomically**

After all targeted V3 tests pass:

- replace `validate_gate.py` with tested `validate_gate_v3.py`;
- replace `verification_manifest_template.json` with tested `verification_manifest_v3_template.json`;
- replace `run_benchmark_template.sh` and `benchmark_evaluator_template.py` with their tested V3 files;
- remove `run_usability_template.sh` and keep `run_quality_template.sh`;
- update `run_quality_template.sh`, `run_security_template.sh`, and every V3 test to reference canonical `validate_gate.py`, `verification_manifest_template.json`, `run_benchmark_template.sh`, and `benchmark_evaluator_template.py` names;
- remove five `phase*.md` workflows and keep four `stage*.md` workflows;
- remove V2 stale-authorization fixture paths, promote `verification_manifest_v3.json` to `verification_manifest.json`, and keep the final Stage 2 fixture paths;
- remove `LICENSE` and its README section.

Execute only the paths listed in this task. Do not delete historical workbenches, the optional Codex Hook, `CONTRIBUTING.md`, fixture coverage, or mature evaluator behavior.

- [ ] **Step 7: Run contract tests GREEN and validate metadata**

First run the complete V3 suite and the migration-matrix test against the promoted canonical files. Only after both are GREEN, replace the four historical executable workbench commands in `.github/workflows/offline-validation.yml` with:

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_*.py' -v
```

Keep Shell syntax, Python compile, JSON parse, metadata, and whitespace jobs, and update their current file lists.

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_*.py' -v
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 /Users/conrad/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/project-verifier
```

- [ ] **Step 8: Commit the contract migration**

```bash
git add README.md skills/project-verifier .github/workflows/offline-validation.yml
git add -u LICENSE skills/project-verifier/workflows
git add project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/test_migration_matrix.json
git diff --cached --name-only
git commit -m "docs: publish four-stage project verifier contract"
```

Stage `bootstrap.sh`, `AGENTS.md`, or `CONTRIBUTING.md` only when the reviewed diff shows an actual stale reference that Task 7 intentionally changed.

---

### Task 8: Full Offline Verification and Evidence Closeout

**Files:**
- Create: `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/verification_report.md`
- Modify: `project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/execution_log.md`

**Interfaces:**
- Produces a truthful verification matrix with command, exit code, result count, limitations, and deferred work.

- [ ] **Step 1: Run the complete V3 unit suite**

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache \
python3 -m unittest discover -s skills/project-verifier/tests -p 'test_*.py' -v
```

Expected: zero failures and zero errors. Record the exact test count; do not reuse the old `66` count unless the new output reports it.

- [ ] **Step 2: Run Shell syntax checks**

```bash
bash -n bootstrap.sh
bash -n skills/project-verifier/templates/run_quality_template.sh
bash -n skills/project-verifier/templates/run_security_template.sh
bash -n skills/project-verifier/templates/run_benchmark_template.sh
```

- [ ] **Step 3: Compile current Python files**

```bash
PYTHONPYCACHEPREFIX=/tmp/project-verifier-v3-pycache python3 -m py_compile \
  skills/project-verifier/scripts/validate_gate.py \
  skills/project-verifier/templates/security_normalizer_template.py \
  skills/project-verifier/templates/benchmark_evaluator_template.py \
  optional/codex-hook/pre_tool_guard.py \
  skills/project-verifier/tests/helpers.py \
  skills/project-verifier/tests/test_control_plane.py \
  skills/project-verifier/tests/test_contract.py \
  skills/project-verifier/tests/test_quality_runner.py \
  skills/project-verifier/tests/test_security.py \
  skills/project-verifier/tests/test_benchmark.py
```

- [ ] **Step 4: Parse all current JSON artifacts**

```bash
python3 -c 'import json; from pathlib import Path; [json.loads(p.read_text(encoding="utf-8")) for p in Path("skills/project-verifier").rglob("*.json")]'
```

- [ ] **Step 5: Validate the Skill and dry-run installer**

```bash
python3 /Users/conrad/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/project-verifier
./bootstrap.sh codex --dry-run
```

The dry run must not overwrite the existing local installation.

- [ ] **Step 6: Check repository hygiene and current-contract residue**

```bash
git diff --check
git status --short
rg -n "five-phase|Phase [1-6]|phase[1-6]_|LICENSE|record & replay|录制|回放|radar" \
  README.md skills/project-verifier .github optional AGENTS.md CONTRIBUTING.md bootstrap.sh
```

Classify every match: prohibited current contract, intentional negative boundary, or historical/non-current reference. Fix prohibited current matches before proceeding.

- [ ] **Step 7: Write the verification report**

Include:

- implemented scope and explicit omissions;
- exact command results and test count;
- migration/deletion list;
- historical-to-V3 test migration totals with every retired assertion justified;
- evidence that preflight and authorization tests used fake fixtures only;
- confirmation that no real API, scan target, dependency install, Skill install, push, or merge occurred;
- known limitations, including that static and fixture tests do not prove future Agent behavior;
- execution backend, backend transitions, review-independence level, completed task ledger, and evidence that no completed task was repeated;
- separately authorized next option for model-backed Agent behavior comparison.

- [ ] **Step 8: Stage and review final evidence before the final commit**

```bash
git add project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/verification_report.md \
  project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/execution_log.md \
  project_verifier_iteration_workbench/20260710_four_stage_adapter_v3/agent_execution
git diff --cached --name-only
git diff --cached --check
```

Inspect the staged files and diff. Confirm they contain no secrets, caches, `.DS_Store`, generated runtime reports outside the iteration workbench, old current-contract workflow files, or unrequested feature work.

- [ ] **Step 9: Commit the verification evidence**

```bash
git commit -m "test: verify project verifier v3 offline"
```

Do not push or merge. Present the verified branch state and ask separately before either action.

## Execution Checkpoints

The approved plan authorizes reversible implementation details inside this repository branch. Do not ask for confirmation after every task. Pause only at these material checkpoints:

1. **Control-plane exception:** the decision-envelope implementation cannot preserve a P0 fail-closed property without changing the approved design.
2. **Tool acquisition:** any test or implementation would require installing/downloading a dependency or accessing a network target.
3. **Scope expansion:** a production-browser/replay system, multi-host Hook platform, generic plugin framework, or other removed feature appears necessary.
4. **Orchestration degradation:** the inline fallback would materially reduce an approved quality boundary beyond the disclosed loss of independent review.
5. **Final publication:** push, merge, local Skill overwrite, or real Agent/model comparison is proposed.

Everything else proceeds task-by-task with test evidence and execution-log updates.

## Deferred by Design

- Real security scans and vulnerability database updates.
- Real AI model/API Benchmark runs.
- Model-backed old-versus-new Agent behavior comparison.
- Automatic global tool installation.
- Browser recording/replay or production business operations.
- Multi-host Hook support.
- AutoGen, LangGraph, MetaGPT, OpenAI Agents SDK, or another multi-agent runtime dependency.
- Universal project/security scores and radar charts.
- `main` merge, GitHub push, and local Skill overwrite.
