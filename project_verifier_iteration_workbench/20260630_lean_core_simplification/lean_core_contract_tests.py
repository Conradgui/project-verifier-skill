#!/usr/bin/env python3
"""Offline contract tests for the credibility-first lean core."""

import importlib.util
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills/project-verifier"
README = REPO_ROOT / "README.md"
EVALUATOR = SKILL_ROOT / "templates/benchmark_evaluator_template.py"
VALIDATOR = SKILL_ROOT / "scripts/validate_gate.py"
HOOK_ROOT = REPO_ROOT / "optional/codex-hook"


def read(path):
    return path.read_text(encoding="utf-8")


def test_five_phase_core_and_single_optional_interview_export():
    skill = read(SKILL_ROOT / "SKILL.md")
    readme = read(README)
    workflow_names = sorted(path.name for path in (SKILL_ROOT / "workflows").glob("phase*.md"))
    assert workflow_names == [
        "phase1_explore.md",
        "phase2_diagrams.md",
        "phase3_quality.md",
        "phase4_usability.md",
        "phase5_benchmark.md",
    ]
    assert "five-phase" in skill.lower()
    assert "interview_evidence_pack.md" in skill and "interview_evidence_pack/" not in skill
    assert "interview_evidence_pack.md" in readme and "interview_evidence_pack/" not in readme


def test_compact_human_artifacts_keep_flow_matrix_compatibility():
    contract = read(SKILL_ROOT / "SKILL.md") + read(SKILL_ROOT / "workflows/phase2_diagrams.md")
    assert "project_verification_workbench/project_report.md" in contract
    assert "project_verification_workbench/flow_matrix.md" in contract
    assert "project_verification_workbench/phase2_flow_matrix.md" in contract
    assert "project_understanding/project_understanding_report.md" not in contract


def test_current_contract_has_no_record_replay_or_multihost_platform_claims():
    active = "\n".join(
        read(path)
        for path in [README, SKILL_ROOT / "SKILL.md", *sorted((SKILL_ROOT / "workflows").glob("*.md"))]
    ).lower()
    prohibited = (
        "record & replay",
        "recorded flow",
        "录制",
        "回放",
        "browser verification adapter",
        "guarded mode",
        "isolated mode",
        "claude hook",
        "gemini hook",
        "cursor hook",
    )
    assert not [term for term in prohibited if term in active]


def test_credibility_boundaries_remain_explicit():
    contract = read(SKILL_ROOT / "SKILL.md") + read(SKILL_ROOT / "workflows/phase5_benchmark.md")
    manifest = json.loads(read(SKILL_ROOT / "templates/verification_manifest_template.json"))
    phase = manifest["phases"]["phase1"]
    assert {"phase_status", "result_outcome", "execution_scope", "claim_eligibility"} <= set(phase)
    for phrase in (
        "proposal_sha256",
        "source_revision",
        "inconclusive",
        "minimum_samples",
        "not_measured",
        "single run",
    ):
        assert phrase.lower() in contract.lower()


def test_evaluator_has_raw_metrics_without_scores_or_radar():
    source = read(EVALUATOR)
    assert "raw_value" in source and "sample_adequacy" in source and "not_measured_reason" in source
    for removed in ("auxiliary_score", "score_mapping", "generate_html_dashboard", "radar", "chart.js"):
        assert removed not in source.lower()


def test_evaluator_rejects_empty_success_output():
    spec = importlib.util.spec_from_file_location("lean_evaluator", EVALUATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        task = {
            "task_id": "BM_EMPTY",
            "execution_mode": "full",
            "rubric_approved": True,
            "metrics": [{
                "id": "completion",
                "label": "Completion",
                "measurement_method": "assertion_rate",
                "success_threshold": {"operator": ">=", "value": 1},
                "minimum_samples": 1,
                "evidence_fields": ["assertions"],
                "assertion_tags": ["completion"],
            }],
        }
        empty = {
            "task_id": "BM_EMPTY",
            "runner_type": "tool",
            "execution_scope": "full",
            "status": "completed",
            "exit_code": 0,
            "assertions": [],
            "errors": [],
        }
        baseline = {**empty, "runner_type": "baseline"}
        paths = []
        for name, payload in (("task.json", task), ("tool.json", empty), ("baseline.json", baseline)):
            path = root / name
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths.append(path)
        evaluator = module.BenchmarkEvaluator(str(paths[1]), str(paths[2]), str(paths[0]))
        evaluator.load_data()
        results = evaluator.evaluate()
        assert results["tool"]["completion"]["raw_value"] is None
        assert results["tool"]["completion"]["not_measured_reason"]


def test_evaluator_requires_explicit_rubric_approval_before_metrics():
    spec = importlib.util.spec_from_file_location("lean_evaluator_rubric_gate", EVALUATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        task = {
            "task_id": "BM_RUBRIC_GATE",
            "metrics": [{
                "id": "completion",
                "label": "Completion",
                "measurement_method": "assertion_rate",
                "success_threshold": {"operator": ">=", "value": 1},
                "minimum_samples": 1,
                "evidence_fields": ["assertions"],
                "assertion_tags": ["completion"],
            }],
        }
        output = {
            "task_id": "BM_RUBRIC_GATE",
            "status": "completed",
            "execution_mode": "full",
            "exit_code": 0,
            "assertions": [{"text": "Output exists", "passed": True, "evidence": "result.json", "tags": ["completion"]}],
            "errors": [],
        }
        paths = {}
        for name, payload in (("task.json", task), ("tool.json", {**output, "runner_type": "tool"}), ("baseline.json", {**output, "runner_type": "baseline"})):
            path = root / name
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths[name] = path
        evaluator = module.BenchmarkEvaluator(str(paths["tool.json"]), str(paths["baseline.json"]), str(paths["task.json"]))
        evaluator.load_data()
        results = evaluator.evaluate()
        result = results["tool"]["completion"]
        assert result["raw_value"] is None
        assert "rubric_approved" in result["not_measured_reason"]


def test_evaluator_requires_declared_file_evidence_to_exist():
    spec = importlib.util.spec_from_file_location("lean_evaluator_files", EVALUATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        task = {
            "task_id": "BM_FILE_EVIDENCE",
            "evidence_root": str(root),
            "rubric_approved": True,
            "metrics": [{
                "id": "verified_output",
                "label": "Verified Output",
                "measurement_method": "assertion_rate",
                "success_threshold": {"operator": ">=", "value": 1},
                "minimum_samples": 1,
                "evidence_fields": ["assertions"],
                "assertion_tags": ["output"],
                "require_evidence_files": True,
            }],
        }
        output = {
            "task_id": "BM_FILE_EVIDENCE",
            "status": "completed",
            "execution_mode": "full",
            "exit_code": 0,
            "assertions": [{"text": "Output exists", "passed": True, "evidence": "missing/result.json", "tags": ["output"]}],
        }
        paths = {}
        for name, payload in (("task.json", task), ("tool.json", {**output, "runner_type": "tool"}), ("baseline.json", {**output, "runner_type": "baseline"})):
            path = root / name
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths[name] = path

        def evaluate():
            evaluator = module.BenchmarkEvaluator(str(paths["tool.json"]), str(paths["baseline.json"]), str(paths["task.json"]))
            evaluator.load_data()
            return evaluator.evaluate()["tool"]["verified_output"]

        missing = evaluate()
        assert missing["raw_value"] is None
        assert "existing evidence files" in missing["not_measured_reason"]
        evidence = root / "missing/result.json"
        evidence.parent.mkdir()
        evidence.write_text("{}", encoding="utf-8")
        assert evaluate()["raw_value"] == 1.0


def test_optional_codex_hook_is_narrow_and_fail_closed():
    hook = HOOK_ROOT / "pre_tool_guard.py"
    config = HOOK_ROOT / "hooks/hooks.json"
    assert hook.is_file() and config.is_file()
    config_payload = json.loads(read(config))
    assert "PreToolUse" in json.dumps(config_payload)
    help_result = subprocess.run(
        ["python3", str(hook), "--help"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert help_result.returncode == 0
    source = read(hook).lower()
    for action in ("project_write", "dependency_install", "live_network", "destructive", "git_publish"):
        assert action in source
    assert "claude" not in source and "gemini" not in source and "cursor" not in source

    def guard(payload):
        env = os.environ.copy()
        for name in (
            "PROJECT_VERIFIER_HOOK_MANIFEST",
            "PROJECT_VERIFIER_HOOK_RECEIPT",
            "PROJECT_VERIFIER_HOOK_PROPOSAL",
            "PROJECT_VERIFIER_GATE_VALIDATOR",
        ):
            env.pop(name, None)
        result = subprocess.run(
            ["python3", str(hook), "--project-root", str(REPO_ROOT)],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=env,
        )
        assert result.returncode == 0, result.stdout
        return json.loads(result.stdout)["hookSpecificOutput"]

    assert guard({"tool_name": "Read", "tool_input": {"path": "README.md"}})["permissionDecision"] == "allow"
    assert guard({"tool_name": "Write", "tool_input": {"path": "project_verification_workbench/report.md"}})["permissionDecision"] == "allow"
    guarded = {
        "project_write": {"tool_name": "Write", "tool_input": {"path": "src/app.py"}},
        "dependency_install": {"tool_name": "Bash", "tool_input": {"command": "npm install"}},
        "live_network": {"tool_name": "Bash", "tool_input": {"command": "curl https://example.com"}},
        "destructive": {"tool_name": "Bash", "tool_input": {"command": "rm -rf build"}},
        "git_publish": {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
    }
    for action, payload in guarded.items():
        decision = guard(payload)
        assert decision["permissionDecision"] == "deny"
        assert action in decision["permissionDecisionReason"]


def test_usability_runner_marks_script_telemetry_as_self_reported():
    source = read(SKILL_ROOT / "templates/run_usability_template.sh")
    assert '"telemetry_provenance"' in source
    assert '"script_self_reported"' in source
    assert '"wrapper_observed"' in source


def test_docs_and_ci_match_lean_release_scope():
    contributing = read(REPO_ROOT / "CONTRIBUTING.md").lower()
    assert "vcrpy" not in contributing
    assert "bug report template" not in contributing
    assert "66" in contributing
    assert (REPO_ROOT / ".github/workflows/offline-validation.yml").is_file()


def test_source_fingerprint_ignores_workbench_but_tracks_source_changes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
        source = root / "app.py"
        source.write_text("print('v1')\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def fingerprint():
            result = subprocess.run(
                ["python3", str(VALIDATOR), "fingerprint", "--root", str(root)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            assert result.returncode == 0, result.stdout
            return result.stdout.strip()

        clean = fingerprint()
        workbench = root / "project_verification_workbench/phase1.md"
        workbench.parent.mkdir()
        workbench.write_text("evidence\n", encoding="utf-8")
        assert fingerprint() == clean
        source.write_text("print('v2')\n", encoding="utf-8")
        assert fingerprint() != clean


def test_optional_codex_hook_accepts_exact_authorization_and_rejects_stale_source():
    hook = HOOK_ROOT / "pre_tool_guard.py"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
        source = root / "src/app.py"
        source.parent.mkdir()
        source.write_text("print('v1')\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/app.py"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        revision = subprocess.run(
            ["python3", str(VALIDATOR), "fingerprint", "--root", str(root)],
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.strip()
        event = {"tool_name": "Write", "tool_input": {"path": "src/app.py", "content": "print('v2')\n"}}
        classified = subprocess.run(
            ["python3", str(hook), "--classify", "--project-root", str(root)],
            input=json.dumps(event),
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        )
        action_hash = json.loads(classified.stdout)["action_sha256"]

        workbench = root / "project_verification_workbench"
        authorizations = workbench / "authorizations"
        authorizations.mkdir(parents=True)
        plan = workbench / "production_write_plan.md"
        plan.write_text("Update src/app.py after user approval.\n", encoding="utf-8")
        decision = {
            "decision_id": "DEC-HOOK-001",
            "phase": "phase3",
            "decision_type": "project_write",
            "proposal_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
            "source_revision": revision,
            "user_choice": "approved",
            "approved_limits": {"action_sha256": action_hash},
            "approved_at": "2026-06-30T12:00:00+08:00",
            "invalidated_at": None,
        }
        manifest = {
            "schema_version": "2.0",
            "source_revision": {"revision": revision, "dirty": False, "captured_at": "2026-06-30T11:00:00+08:00"},
            "user_intent": {"goal": "test hook", "target_users": ["owner"], "in_scope": ["src/app.py"], "out_of_scope": [], "success_criteria": ["authorized write"], "risk_tolerance": "low"},
            "permissions": {"write_scope": ["src/app.py"], "production_code_changes": True, "dependency_install": False, "live_calls": False, "public_claims": False},
            "phases": {"phase3": {"phase_status": "in_progress", "result_outcome": "not_run", "execution_scope": "none", "claim_eligibility": "none", "gate_state": "approved"}},
            "decisions": [decision],
        }
        manifest_path = workbench / "verification_manifest.json"
        receipt_path = authorizations / "DEC-HOOK-001.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        receipt_path.write_text(json.dumps(decision), encoding="utf-8")
        env = {
            **os.environ,
            "PROJECT_VERIFIER_HOOK_MANIFEST": str(manifest_path),
            "PROJECT_VERIFIER_HOOK_RECEIPT": str(receipt_path),
            "PROJECT_VERIFIER_HOOK_PROPOSAL": str(plan),
            "PROJECT_VERIFIER_GATE_VALIDATOR": str(VALIDATOR),
        }

        def guard():
            result = subprocess.run(
                ["python3", str(hook), "--project-root", str(root)],
                input=json.dumps(event),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=env,
            )
            assert result.returncode == 0, result.stdout
            return json.loads(result.stdout)["hookSpecificOutput"]

        assert guard()["permissionDecision"] == "allow"
        source.write_text("print('changed-before-approved-action')\n", encoding="utf-8")
        stale = guard()
        assert stale["permissionDecision"] == "deny"
        assert "source revision" in stale["permissionDecisionReason"].lower()


def test_gate_check_recomputes_current_source_revision():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
        source = root / "app.py"
        source.write_text("print('v1')\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        revision = subprocess.run(
            ["python3", str(VALIDATOR), "fingerprint", "--root", str(root)],
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.strip()
        workbench = root / "project_verification_workbench"
        workbench.mkdir()
        plan = workbench / "plan.md"
        plan.write_text("Approved live plan.\n", encoding="utf-8")
        decision = {
            "decision_id": "DEC-CURRENT-001",
            "phase": "phase4",
            "decision_type": "live_execution",
            "proposal_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
            "source_revision": revision,
            "user_choice": "approved",
            "approved_limits": {"max_calls": 1},
            "approved_at": "2026-06-30T12:00:00+08:00",
            "invalidated_at": None,
        }
        manifest = {
            "schema_version": "2.0",
            "source_revision": {"revision": revision, "dirty": False, "captured_at": "2026-06-30T11:00:00+08:00"},
            "user_intent": {"goal": "verify", "target_users": ["owner"], "in_scope": ["app.py"], "out_of_scope": [], "success_criteria": ["run"], "risk_tolerance": "low"},
            "permissions": {"write_scope": ["project_verification_workbench"], "production_code_changes": False, "dependency_install": False, "live_calls": True, "public_claims": False},
            "phases": {"phase4": {"phase_status": "in_progress", "result_outcome": "not_run", "execution_scope": "none", "claim_eligibility": "none", "gate_state": "approved"}},
            "decisions": [decision],
        }
        manifest_path = workbench / "verification_manifest.json"
        receipt_path = workbench / "receipt.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        receipt_path.write_text(json.dumps(decision), encoding="utf-8")
        command = [
            "python3", str(VALIDATOR), "check",
            "--manifest", str(manifest_path),
            "--receipt", str(receipt_path),
            "--proposal", str(plan),
            "--source-revision", revision,
            "--project-root", str(root),
            "--phase", "phase4",
            "--decision-type", "live_execution",
            "--limit", "max_calls=1",
        ]
        assert subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).returncode == 0
        source.write_text("print('v2')\n", encoding="utf-8")
        stale = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert stale.returncode != 0
        assert "current source revision" in stale.stdout.lower()


def main():
    tests = sorted((name, value) for name, value in globals().items() if name.startswith("test_") and callable(value))
    failures = []
    for name, test in tests:
        try:
            test()
            print(f"PASS {name}")
        except Exception as exc:
            failures.append((name, exc))
            print(f"FAIL {name}: {exc}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
