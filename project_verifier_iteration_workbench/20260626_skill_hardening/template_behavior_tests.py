#!/usr/bin/env python3
"""Behavior checks for project-verifier template hardening."""

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATOR_PATH = REPO_ROOT / "skills/project-verifier/templates/benchmark_evaluator_template.py"
RUNNER_TEMPLATE = REPO_ROOT / "skills/project-verifier/templates/run_usability_template.sh"


def load_evaluator():
    spec = importlib.util.spec_from_file_location("benchmark_evaluator_template", EVALUATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BenchmarkEvaluator


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_evaluator_requires_evidence_for_high_scores():
    BenchmarkEvaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tool_output = tmp_path / "tool.json"
        baseline_output = tmp_path / "baseline.json"
        write_json(
            tool_output,
            {
                "task_id": "BM_001",
                "runner_type": "tool",
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
                "exit_code": 0,
                "duration_seconds": 1.0,
                "artifacts_created": [],
                "logs_created": False,
                "token_count": 0,
                "assertions": [],
                "errors": [],
            },
        )

        evaluator = BenchmarkEvaluator(str(tool_output), str(baseline_output))
        evaluator.load_data()
        evaluator.evaluate()

        tool_scores = evaluator.scores["tool"]
        assert tool_scores["control"]["score"] is None
        assert tool_scores["control"]["confidence"] == "not_measured"
        assert tool_scores["ux"]["score"] is None
        assert tool_scores["ux"]["confidence"] == "not_measured"
        assert tool_scores["cost_efficiency"]["score"] is None
        assert tool_scores["cost_efficiency"]["confidence"] == "not_measured"


def test_evaluator_scores_complete_evidence():
    BenchmarkEvaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tool_output = tmp_path / "tool.json"
        baseline_output = tmp_path / "baseline.json"
        write_json(
            tool_output,
            {
                "task_id": "BM_002",
                "runner_type": "tool",
                "exit_code": 0,
                "duration_seconds": 1.0,
                "artifacts_created": ["output/result.json"],
                "logs_created": True,
                "log_paths": ["logs/tool.log"],
                "token_count": 500,
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
                "exit_code": 0,
                "duration_seconds": 2.0,
                "artifacts_created": ["baseline/response.txt"],
                "logs_created": True,
                "log_paths": ["logs/baseline.log"],
                "token_count": 1000,
                "assertions": [
                    {"text": "Response exists", "passed": True, "evidence": "baseline/response.txt", "tags": ["completeness"]}
                ],
                "diagnostics": ["Raw response stored"],
                "errors": [],
            },
        )

        evaluator = BenchmarkEvaluator(str(tool_output), str(baseline_output))
        evaluator.load_data()
        evaluator.evaluate()

        tool_scores = evaluator.scores["tool"]
        assert tool_scores["completeness"]["score"] == 10
        assert tool_scores["control"]["score"] == 10
        assert tool_scores["cost_efficiency"]["score"] == 10
        assert tool_scores["latency"]["score"] == 10
        assert tool_scores["ux"]["score"] == 10


def test_evaluator_records_runner_failure():
    BenchmarkEvaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tool_output = tmp_path / "tool.json"
        baseline_output = tmp_path / "baseline.json"
        write_json(
            tool_output,
            {
                "task_id": "BM_003",
                "runner_type": "tool",
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
                "exit_code": 0,
                "duration_seconds": 0.5,
                "artifacts_created": ["baseline/response.txt"],
                "logs_created": False,
                "token_count": 100,
                "assertions": [{"text": "Response exists", "passed": True, "evidence": "baseline/response.txt"}],
                "errors": [],
            },
        )

        evaluator = BenchmarkEvaluator(str(tool_output), str(baseline_output))
        evaluator.load_data()
        evaluator.evaluate()

        assert evaluator.scores["tool"]["completeness"]["score"] == 2
        assert evaluator.scores["tool"]["stability"]["score"] == 2
        assert "Tool runner crashed" in " ".join(evaluator.scores["tool"]["stability"]["evidence"])


def test_usability_runner_dispatches_python_and_shell_scripts():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        runner = tmp_path / "run_usability.sh"
        shutil.copy(RUNNER_TEMPLATE, runner)
        runner.chmod(0o755)

        tests_dir = tmp_path / "tests/usability"
        tests_dir.mkdir(parents=True)
        py_script = tests_dir / "usability_P0_python.py"
        py_script.write_text("print('python-dispatch-ok')\n", encoding="utf-8")
        script = tests_dir / "usability_P0_shell.sh"
        script.write_text("#!/bin/sh\necho shell-dispatch-ok\n", encoding="utf-8")
        script.chmod(0o755)

        result = subprocess.run(
            [str(runner)],
            cwd=tmp_path,
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
            [str(runner)],
            cwd=tmp_path,
            env={**os.environ, "PATH": "/usr/bin:/bin"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        log_text = (tests_dir / "reports/usability_P0_typescript.log").read_text(encoding="utf-8")
        assert result.returncode == 1, result.stdout
        assert "Missing TypeScript runtime" in log_text


def main():
    tests = [
        test_evaluator_requires_evidence_for_high_scores,
        test_evaluator_scores_complete_evidence,
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
