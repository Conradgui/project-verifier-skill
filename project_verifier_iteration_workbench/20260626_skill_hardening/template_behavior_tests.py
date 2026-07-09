#!/usr/bin/env python3
"""Behavior checks for project-verifier template hardening."""

import importlib.util
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATOR_PATH = REPO_ROOT / "skills/project-verifier/templates/benchmark_evaluator_template.py"
RUNNER_TEMPLATE = REPO_ROOT / "skills/project-verifier/templates/run_usability_template.sh"
GATE_VALIDATOR = REPO_ROOT / "skills/project-verifier/scripts/validate_gate.py"


def load_evaluator():
    spec = importlib.util.spec_from_file_location("benchmark_evaluator_template", EVALUATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BenchmarkEvaluator


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def source_fixture(root):
    source_root = root / "source_project"
    source_root.mkdir()
    subprocess.run(["git", "init"], cwd=source_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=source_root, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=source_root, check=True)
    (source_root / "app.py").write_text("print('fixture')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=source_root, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=source_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    revision = subprocess.run(
        ["python3", str(GATE_VALIDATOR), "fingerprint", "--root", str(source_root)],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    return source_root, revision


def authorized_runner_env(root, results_path, max_paths):
    source_root, source_revision = source_fixture(root)
    plan = root / "phase4_usability_plan.md"
    plan.write_text("approved behavior test plan\n", encoding="utf-8")
    digest = hashlib.sha256(plan.read_bytes()).hexdigest()
    decision = {
        "decision_id": "DEC-BEHAVIOR-P4",
        "phase": "phase4",
        "decision_type": "live_execution",
        "proposal_sha256": digest,
        "source_revision": source_revision,
        "user_choice": "approved",
        "approved_limits": {"max_paths": max_paths, "max_calls_per_path": 0, "max_retries": 0, "timeout_seconds": 10},
        "approved_at": "2026-06-29T12:00:00+08:00",
        "invalidated_at": None,
    }
    manifest = {
        "schema_version": "2.0",
        "source_revision": {"revision": source_revision, "dirty": False, "captured_at": "2026-06-29T11:00:00+08:00"},
        "user_intent": {"goal": "runner behavior", "target_users": ["owner"], "in_scope": ["P0"], "out_of_scope": [], "success_criteria": ["dispatch works"], "risk_tolerance": "low"},
        "permissions": {"write_scope": ["tests/usability"], "production_code_changes": False, "dependency_install": False, "live_calls": True, "public_claims": False},
        "phases": {"phase4": {"phase_status": "in_progress", "result_outcome": "not_run", "execution_scope": "none", "claim_eligibility": "none", "gate_state": "approved"}},
        "decisions": [decision],
    }
    manifest_path = root / "verification_manifest.json"
    receipt_path = root / "phase4_live_execution.json"
    write_json(manifest_path, manifest)
    write_json(receipt_path, decision)
    return {
        **os.environ,
        "PROJECT_VERIFIER_GATE_VALIDATOR": str(GATE_VALIDATOR),
        "USABILITY_MANIFEST_FILE": str(manifest_path),
        "USABILITY_AUTHORIZATION_FILE": str(receipt_path),
        "USABILITY_PLAN_FILE": str(plan),
        "USABILITY_SOURCE_REVISION": source_revision,
        "PROJECT_VERIFIER_PROJECT_ROOT": str(source_root),
        "USABILITY_MAX_PATHS": str(max_paths),
        "USABILITY_MAX_CALLS_PER_PATH": "0",
        "USABILITY_MAX_RETRIES": "0",
        "USABILITY_TIMEOUT_SECONDS": "10",
        "USABILITY_RESULTS_JSON": str(results_path),
    }


def test_evaluator_requires_evidence_for_high_scores():
    BenchmarkEvaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tool_output = tmp_path / "tool.json"
        baseline_output = tmp_path / "baseline.json"
        task_definition = tmp_path / "task.json"
        write_json(
            tool_output,
            {
                "task_id": "BM_001",
                "runner_type": "tool",
                "status": "completed",
                "execution_mode": "full",
                "exit_code": 0,
                "duration_seconds": 1.2,
                "artifacts_created": [],
                "logs_created": False,
                "token_count": 0,
                "assertions": [],
                "errors": [],
            },
        )
        write_json(
            baseline_output,
            {
                "task_id": "BM_001",
                "runner_type": "baseline",
                "status": "completed",
                "execution_mode": "full",
                "exit_code": 0,
                "duration_seconds": 1.0,
                "artifacts_created": [],
                "logs_created": False,
                "token_count": 0,
                "assertions": [],
                "errors": [],
            },
        )
        write_json(task_definition, {"task_id": "BM_001", "metrics": []})

        evaluator = BenchmarkEvaluator(str(tool_output), str(baseline_output), str(task_definition))
        evaluator.load_data()
        evaluator.evaluate()

        assert evaluator.results["tool"] == {}


def test_evaluator_reports_complete_raw_evidence():
    BenchmarkEvaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tool_output = tmp_path / "tool.json"
        baseline_output = tmp_path / "baseline.json"
        task_definition = tmp_path / "task.json"
        write_json(
            tool_output,
            {
                "task_id": "BM_002",
                "runner_type": "tool",
                "status": "completed",
                "execution_mode": "full",
                "exit_code": 0,
                "duration_seconds": 1.0,
                "artifacts_created": ["output/result.json"],
                "logs_created": True,
                "log_paths": ["logs/tool.log"],
                "token_count": 500,
                "sample_count": 1,
                "assertions": [
                    {"text": "Output exists", "passed": True, "evidence": "output/result.json", "tags": ["completeness"]},
                    {"text": "Path traversal rejected", "passed": True, "evidence": "logs/tool.log", "tags": ["safety"]},
                    {"text": "Failure message is actionable", "passed": True, "evidence": "logs/tool.log", "tags": ["ux"]},
                ],
                "control_evidence": ["Sandboxed output directory"],
                "diagnostics": ["Failure stage is logged"],
                "errors": [],
            },
        )
        write_json(
            baseline_output,
            {
                "task_id": "BM_002",
                "runner_type": "baseline",
                "status": "completed",
                "execution_mode": "full",
                "exit_code": 0,
                "duration_seconds": 2.0,
                "artifacts_created": ["baseline/response.txt"],
                "logs_created": True,
                "log_paths": ["logs/baseline.log"],
                "token_count": 1000,
                "sample_count": 1,
                "assertions": [
                    {"text": "Response exists", "passed": True, "evidence": "baseline/response.txt", "tags": ["completeness"]}
                ],
                "diagnostics": ["Raw response stored"],
                "errors": [],
            },
        )
        write_json(
            task_definition,
            {
                "task_id": "BM_002",
                "metrics": [
                    {
                        "id": "completeness",
                        "measurement_method": "assertion_rate",
                        "success_threshold": {"operator": ">=", "value": 1.0},
                        "minimum_samples": 1,
                        "evidence_fields": ["assertions"],
                        "assertion_tags": ["completeness"],
                    },
                    {
                        "id": "control",
                        "measurement_method": "assertion_rate",
                        "success_threshold": {"operator": ">=", "value": 1.0},
                        "minimum_samples": 1,
                        "evidence_fields": ["assertions"],
                        "assertion_tags": ["safety"],
                    },
                    {
                        "id": "cost_efficiency",
                        "measurement_method": "numeric_ratio",
                        "success_threshold": {"operator": "<=", "value": 1.0},
                        "minimum_samples": 1,
                        "evidence_fields": ["token_count"],
                        "source_field": "token_count",
                    },
                    {
                        "id": "latency",
                        "measurement_method": "numeric_ratio",
                        "success_threshold": {"operator": "<=", "value": 1.0},
                        "minimum_samples": 1,
                        "evidence_fields": ["duration_seconds"],
                        "source_field": "duration_seconds",
                    },
                    {
                        "id": "ux",
                        "measurement_method": "assertion_rate",
                        "success_threshold": {"operator": ">=", "value": 1.0},
                        "minimum_samples": 1,
                        "evidence_fields": ["assertions"],
                        "assertion_tags": ["ux"],
                    },
                ],
            },
        )

        evaluator = BenchmarkEvaluator(str(tool_output), str(baseline_output), str(task_definition))
        evaluator.load_data()
        evaluator.evaluate()

        tool_results = evaluator.results["tool"]
        assert tool_results["completeness"]["raw_value"] == 1.0
        assert tool_results["control"]["raw_value"] == 1.0
        assert tool_results["cost_efficiency"]["raw_value"] == 0.5
        assert tool_results["latency"]["raw_value"] == 0.5
        assert tool_results["ux"]["raw_value"] == 1.0
        assert all("score" not in result for result in tool_results.values())


def test_evaluator_records_runner_failure():
    BenchmarkEvaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tool_output = tmp_path / "tool.json"
        baseline_output = tmp_path / "baseline.json"
        task_definition = tmp_path / "task.json"
        write_json(
            tool_output,
            {
                "task_id": "BM_003",
                "runner_type": "tool",
                "status": "failed",
                "execution_mode": "full",
                "exit_code": 1,
                "duration_seconds": 0.4,
                "artifacts_created": [],
                "logs_created": False,
                "token_count": 100,
                "assertions": [],
                "errors": ["Tool runner crashed"],
            },
        )
        write_json(
            baseline_output,
            {
                "task_id": "BM_003",
                "runner_type": "baseline",
                "status": "completed",
                "execution_mode": "full",
                "exit_code": 0,
                "duration_seconds": 0.5,
                "artifacts_created": ["baseline/response.txt"],
                "logs_created": False,
                "token_count": 100,
                "assertions": [{"text": "Response exists", "passed": True, "evidence": "baseline/response.txt"}],
                "errors": [],
            },
        )
        write_json(
            task_definition,
            {
                "task_id": "BM_003",
                "metrics": [{
                    "id": "completeness",
                    "measurement_method": "assertion_rate",
                    "success_threshold": {"operator": ">=", "value": 1.0},
                    "score_mapping": "pass_rate_x_10",
                    "minimum_samples": 1,
                    "evidence_fields": ["assertions"],
                    "assertion_tags": ["completeness"],
                }],
            },
        )

        evaluator = BenchmarkEvaluator(str(tool_output), str(baseline_output), str(task_definition))
        evaluator.load_data()
        evaluator.evaluate()

        assert "score" not in evaluator.results["tool"]["completeness"]
        assert evaluator.results["tool"]["completeness"]["raw_value"] is None
        assert "status is failed" in evaluator.results["tool"]["completeness"]["not_measured_reason"]


def test_usability_runner_dispatches_python_and_shell_scripts():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        runner = tmp_path / "run_usability.sh"
        shutil.copy(RUNNER_TEMPLATE, runner)
        runner.chmod(0o755)

        tests_dir = tmp_path / "tests/usability"
        tests_dir.mkdir(parents=True)
        py_script = tests_dir / "usability_P0_python.py"
        reports = tests_dir / "reports"
        py_telemetry = reports / "usability_P0_python.telemetry.json"
        sh_telemetry = reports / "usability_P0_shell.telemetry.json"
        py_script.write_text(
            "from pathlib import Path\n"
            "print('python-dispatch-ok')\n"
            f"Path({str(py_telemetry)!r}).parent.mkdir(parents=True, exist_ok=True)\n"
            f"Path({str(py_telemetry)!r}).write_text('{{\"external_calls_actual\":0,\"retries_actual\":0,\"side_effects\":[]}}')\n",
            encoding="utf-8",
        )
        script = tests_dir / "usability_P0_shell.sh"
        script.write_text(
            f"#!/bin/sh\necho shell-dispatch-ok\nmkdir -p '{reports}'\nprintf '%s' '{{\"external_calls_actual\":0,\"retries_actual\":0,\"side_effects\":[]}}' > '{sh_telemetry}'\n",
            encoding="utf-8",
        )
        script.chmod(0o755)

        result = subprocess.run(
            [str(runner), "preflight"],
            cwd=tmp_path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert result.returncode == 0, result.stdout

        results_path = tmp_path / "workbench/phase4_usability_results.json"
        result = subprocess.run(
            [str(runner), "run"],
            cwd=tmp_path,
            env=authorized_runner_env(tmp_path, results_path, 2),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        assert result.returncode == 0, result.stdout
        assert "python-dispatch-ok" in (tests_dir / "reports/usability_P0_python.log").read_text(
            encoding="utf-8"
        )
        assert "shell-dispatch-ok" in (tests_dir / "reports/usability_P0_shell.log").read_text(
            encoding="utf-8"
        )


def test_usability_runner_reports_missing_typescript_runtime():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        runner = tmp_path / "run_usability.sh"
        shutil.copy(RUNNER_TEMPLATE, runner)
        runner.chmod(0o755)

        tests_dir = tmp_path / "tests/usability"
        tests_dir.mkdir(parents=True)
        ts_script = tests_dir / "usability_P0_typescript.ts"
        ts_script.write_text("console.log('typescript-dispatch-ok')\n", encoding="utf-8")

        result = subprocess.run(
            [str(runner), "preflight"],
            cwd=tmp_path,
            env={**os.environ, "PATH": "/usr/bin:/bin"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        assert result.returncode == 1, result.stdout
        assert "Missing TypeScript runtime" in result.stdout


def main():
    tests = [
        test_evaluator_requires_evidence_for_high_scores,
        test_evaluator_reports_complete_raw_evidence,
        test_evaluator_records_runner_failure,
        test_usability_runner_dispatches_python_and_shell_scripts,
        test_usability_runner_reports_missing_typescript_runtime,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
