#!/usr/bin/env python3
"""Offline contract and behavior tests for Stage Gate Quality V2."""

import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills/project-verifier"
VALIDATOR = SKILL_ROOT / "scripts/validate_gate.py"
MANIFEST_TEMPLATE = SKILL_ROOT / "templates/verification_manifest_template.json"
RUNNER = SKILL_ROOT / "templates/run_usability_template.sh"
BENCHMARK_RUNNER = SKILL_ROOT / "templates/run_benchmark_template.sh"
EVALUATOR = SKILL_ROOT / "templates/benchmark_evaluator_template.py"
FIXTURES = SKILL_ROOT / "evals/fixtures"


def read(path):
    return path.read_text(encoding="utf-8")


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def source_fixture(root, name="source_project"):
    source_root = root / name
    source_root.mkdir()
    run(["git", "init"], source_root)
    run(["git", "config", "user.email", "fixture@example.com"], source_root)
    run(["git", "config", "user.name", "Fixture"], source_root)
    (source_root / "app.py").write_text("print('fixture')\n", encoding="utf-8")
    run(["git", "add", "app.py"], source_root)
    committed = run(["git", "commit", "-m", "fixture"], source_root)
    assert committed.returncode == 0, committed.stdout
    revision = run(["python3", str(VALIDATOR), "fingerprint", "--root", str(source_root)], root)
    assert revision.returncode == 0, revision.stdout
    return source_root, revision.stdout.strip()


def run(command, cwd, env=None):
    return subprocess.run(
        command,
        cwd=cwd,
        env=env or os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def load_evaluator():
    spec = importlib.util.spec_from_file_location("v2_evaluator", EVALUATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BenchmarkEvaluator


def gate_fixture(root, source_revision="rev-a", invalidated_at=None):
    plan = root / "phase4_usability_plan.md"
    plan.write_text("approved plan\n", encoding="utf-8")
    plan_hash = hashlib.sha256(plan.read_bytes()).hexdigest()
    decision = {
        "decision_id": "DEC-P4-001",
        "phase": "phase4",
        "decision_type": "live_execution",
        "proposal_sha256": plan_hash,
        "source_revision": source_revision,
        "user_choice": "approved",
        "approved_limits": {
            "max_paths": 1,
            "max_calls_per_path": 2,
            "max_retries": 1,
            "timeout_seconds": 10,
        },
        "approved_at": "2026-06-29T12:00:00+08:00",
        "invalidated_at": invalidated_at,
    }
    manifest = {
        "schema_version": "2.0",
        "source_revision": {"revision": source_revision, "dirty": False, "captured_at": "2026-06-29T11:00:00+08:00"},
        "user_intent": {"goal": "verify", "target_users": ["owner"], "in_scope": ["P0"], "out_of_scope": [], "success_criteria": ["P0 runs"], "risk_tolerance": "low"},
        "permissions": {"write_scope": ["tests/usability"], "production_code_changes": False, "dependency_install": False, "live_calls": True, "public_claims": False},
        "phases": {"phase4": {"phase_status": "in_progress", "result_outcome": "not_run", "execution_scope": "none", "claim_eligibility": "none", "gate_state": "approved", "artifacts": [], "blockers": [], "recovery_conditions": []}},
        "decisions": [decision],
    }
    manifest_path = root / "verification_manifest.json"
    receipt_path = root / "phase4_live_execution.json"
    write_json(manifest_path, manifest)
    write_json(receipt_path, decision)
    return plan, manifest_path, receipt_path


def validator_command(plan, manifest, receipt, revision="rev-a"):
    return [
        "python3", str(VALIDATOR), "check",
        "--manifest", str(manifest),
        "--receipt", str(receipt),
        "--proposal", str(plan),
        "--source-revision", revision,
        "--phase", "phase4",
        "--decision-type", "live_execution",
        "--limit", "max_paths=1",
        "--limit", "max_calls_per_path=2",
        "--limit", "max_retries=1",
        "--limit", "timeout_seconds=10",
    ]


def test_manifest_template_separates_state_dimensions():
    payload = json.loads(read(MANIFEST_TEMPLATE))
    phase = payload["phases"]["phase1"]
    assert set(("phase_status", "result_outcome", "execution_scope", "claim_eligibility")) <= set(phase)
    assert "decisions" in payload
    assert "source_revision" in payload


def test_gate_validator_accepts_exact_current_approval():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        plan, manifest, receipt = gate_fixture(root)
        result = run(validator_command(plan, manifest, receipt), root)
        assert result.returncode == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["approved"] is True
        assert payload["decision_id"] == "DEC-P4-001"


def test_gate_validator_rejects_changed_plan_revision_and_invalidation():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        plan, manifest, receipt = gate_fixture(root)
        plan.write_text("changed plan\n", encoding="utf-8")
        changed = run(validator_command(plan, manifest, receipt), root)
        assert changed.returncode != 0
        assert "proposal" in changed.stdout.lower()

        plan, manifest, receipt = gate_fixture(root)
        stale = run(validator_command(plan, manifest, receipt, revision="rev-b"), root)
        assert stale.returncode != 0
        assert "source revision" in stale.stdout.lower()

        plan, manifest, receipt = gate_fixture(root, invalidated_at="2026-06-29T13:00:00+08:00")
        invalidated = run(validator_command(plan, manifest, receipt), root)
        assert invalidated.returncode != 0
        assert "invalidated" in invalidated.stdout.lower()


def test_gate_validator_rejects_missing_permissions_and_unfingerprinted_dirty_source():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        plan, manifest, receipt = gate_fixture(root)
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload.pop("permissions")
        write_json(manifest, payload)
        missing = run(validator_command(plan, manifest, receipt), root)
        assert missing.returncode != 0 and "permissions" in missing.stdout.lower()

        plan, manifest, receipt = gate_fixture(root)
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["source_revision"]["dirty"] = True
        write_json(manifest, payload)
        dirty = run(validator_command(plan, manifest, receipt), root)
        assert dirty.returncode != 0 and "dirty" in dirty.stdout.lower()


def test_write_scope_validator_rejects_unapproved_production_paths():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _, manifest, _ = gate_fixture(root)
        allowed = run(
            ["python3", str(VALIDATOR), "paths", "--manifest", str(manifest), "--changed-file", "tests/usability/test_p0.py"],
            root,
        )
        assert allowed.returncode == 0, allowed.stdout
        rejected = run(
            ["python3", str(VALIDATOR), "paths", "--manifest", str(manifest), "--changed-file", "src/app.py"],
            root,
        )
        assert rejected.returncode != 0
        assert "write scope" in rejected.stdout.lower()


def test_source_fingerprint_changes_with_tracked_or_untracked_state_without_exposing_content():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run(["git", "init"], root)
        run(["git", "config", "user.email", "fixture@example.com"], root)
        run(["git", "config", "user.name", "Fixture"], root)
        tracked = root / "app.txt"
        tracked.write_text("v1\n", encoding="utf-8")
        run(["git", "add", "app.txt"], root)
        commit = run(["git", "commit", "-m", "fixture"], root)
        assert commit.returncode == 0, commit.stdout

        clean = run(["python3", str(VALIDATOR), "fingerprint", "--root", str(root)], root)
        assert clean.returncode == 0 and clean.stdout.strip().startswith("git:")
        tracked.write_text("v2\n", encoding="utf-8")
        dirty_tracked = run(["python3", str(VALIDATOR), "fingerprint", "--root", str(root)], root)
        assert dirty_tracked.returncode == 0 and dirty_tracked.stdout.strip().startswith("dirty:")
        secret = "never-print-this-secret"
        (root / ".env").write_text(secret, encoding="utf-8")
        dirty_untracked = run(["python3", str(VALIDATOR), "fingerprint", "--root", str(root)], root)
        assert dirty_untracked.returncode == 0
        assert dirty_untracked.stdout != dirty_tracked.stdout
        assert secret not in dirty_untracked.stdout


def runner_fixture(root, with_telemetry=True):
    tests = root / "tests/usability"
    tests.mkdir(parents=True)
    marker = root / "executed.txt"
    script = tests / "usability_P0_local.sh"
    telemetry = root / "tests/usability/reports/usability_P0_local.telemetry.json"
    telemetry_write = ""
    if with_telemetry:
        telemetry_write = (
            f"mkdir -p '{telemetry.parent}'\n"
            f"printf '%s' '{{\"external_calls_actual\":1,\"retries_actual\":0,\"side_effects\":[]}}' > '{telemetry}'\n"
        )
    script.write_text(f"#!/bin/sh\nprintf executed > '{marker}'\n{telemetry_write}", encoding="utf-8")
    script.chmod(0o755)
    runner = root / "run_usability.sh"
    runner.write_text(read(RUNNER), encoding="utf-8")
    runner.chmod(0o755)
    return runner, marker


def runner_env(root, plan, manifest, receipt):
    source_root, revision = source_fixture(root)
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    manifest_payload["source_revision"]["revision"] = revision
    manifest_payload["source_revision"]["dirty"] = False
    manifest_payload["decisions"][0]["source_revision"] = revision
    receipt_payload["source_revision"] = revision
    write_json(manifest, manifest_payload)
    write_json(receipt, receipt_payload)
    return {
        **os.environ,
        "PROJECT_VERIFIER_GATE_VALIDATOR": str(VALIDATOR),
        "USABILITY_MANIFEST_FILE": str(manifest),
        "USABILITY_AUTHORIZATION_FILE": str(receipt),
        "USABILITY_PLAN_FILE": str(plan),
        "USABILITY_SOURCE_REVISION": revision,
        "PROJECT_VERIFIER_PROJECT_ROOT": str(source_root),
        "USABILITY_MAX_PATHS": "1",
        "USABILITY_MAX_CALLS_PER_PATH": "2",
        "USABILITY_MAX_RETRIES": "1",
        "USABILITY_TIMEOUT_SECONDS": "10",
        "USABILITY_RESULTS_JSON": str(root / "project_verification_workbench/phase4_usability_results.json"),
    }


def test_usability_run_requires_machine_valid_authorization():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner, marker = runner_fixture(root)
        result = run([str(runner), "run"], root)
        assert result.returncode != 0
        assert "authorization" in result.stdout.lower()
        assert not marker.exists()


def test_benchmark_runner_preflight_is_no_call_and_full_requires_authorization():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner = root / "run_benchmark.sh"
        runner.write_text(read(BENCHMARK_RUNNER), encoding="utf-8")
        runner.chmod(0o755)
        marker = root / "benchmark-executed.txt"
        executor = root / "benchmark_executor.sh"
        executor.write_text(f"#!/bin/sh\nprintf '%s' \"$1\" > '{marker}'\n", encoding="utf-8")
        executor.chmod(0o755)
        task_dir = root / "benchmarks/tasks"
        task_dir.mkdir(parents=True)
        write_json(task_dir / "task_BM_001.json", {"task_id": "BM_001", "metrics": []})
        env = {**os.environ, "BENCHMARK_EXECUTOR": str(executor)}

        preflight = run([str(runner), "preflight"], root, env)
        assert preflight.returncode == 0, preflight.stdout
        assert not marker.exists()
        full = run([str(runner), "full"], root, env)
        assert full.returncode != 0
        assert "authorization" in full.stdout.lower()
        assert not marker.exists()

        plan = root / "phase5_benchmark_plan.md"
        plan.write_text("approved benchmark plan\n", encoding="utf-8")
        source_root, source_revision = source_fixture(root, "benchmark_source")
        digest = hashlib.sha256(plan.read_bytes()).hexdigest()
        decision = {
            "decision_id": "DEC-P5-001",
            "phase": "phase5",
            "decision_type": "benchmark_execution",
            "proposal_sha256": digest,
            "source_revision": source_revision,
            "user_choice": "approved",
            "approved_limits": {"max_calls": 1, "max_retries": 0, "timeout_seconds": 10},
            "approved_at": "2026-06-29T12:00:00+08:00",
            "invalidated_at": None,
        }
        manifest = {
            "schema_version": "2.0",
            "source_revision": {"revision": source_revision, "dirty": False, "captured_at": "2026-06-29T11:00:00+08:00"},
            "user_intent": {"goal": "benchmark fixture", "target_users": ["owner"], "in_scope": ["BM_001"], "out_of_scope": [], "success_criteria": ["gate works"], "risk_tolerance": "low"},
            "permissions": {"write_scope": ["benchmarks"], "production_code_changes": False, "dependency_install": False, "live_calls": True, "public_claims": False},
            "phases": {"phase5": {"phase_status": "in_progress", "result_outcome": "not_run", "execution_scope": "none", "claim_eligibility": "none", "gate_state": "approved"}},
            "decisions": [decision],
        }
        manifest_path = root / "verification_manifest.json"
        receipt_path = root / "phase5_benchmark_execution.json"
        write_json(manifest_path, manifest)
        write_json(receipt_path, decision)
        authorized_env = {
            **env,
            "PROJECT_VERIFIER_GATE_VALIDATOR": str(VALIDATOR),
            "BENCHMARK_MANIFEST_FILE": str(manifest_path),
            "BENCHMARK_AUTHORIZATION_FILE": str(receipt_path),
            "BENCHMARK_PLAN_FILE": str(plan),
            "BENCHMARK_SOURCE_REVISION": source_revision,
            "PROJECT_VERIFIER_PROJECT_ROOT": str(source_root),
            "BENCHMARK_MAX_CALLS": "1",
            "BENCHMARK_MAX_RETRIES": "0",
            "BENCHMARK_TIMEOUT_SECONDS": "10",
        }
        full = run([str(runner), "full"], root, authorized_env)
        assert full.returncode == 0, full.stdout
        assert marker.read_text(encoding="utf-8") == "full"


def test_usability_result_records_decision_state_and_actual_telemetry():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        plan, manifest, receipt = gate_fixture(root)
        runner, marker = runner_fixture(root)
        env = runner_env(root, plan, manifest, receipt)
        result = run([str(runner), "run"], root, env)
        assert result.returncode == 0, result.stdout
        payload = json.loads(Path(env["USABILITY_RESULTS_JSON"]).read_text(encoding="utf-8"))
        assert payload["phase_status"] == "completed"
        assert payload["result_outcome"] == "pass"
        assert payload["execution_scope"] == "full"
        assert payload["claim_eligibility"] == "full"
        assert payload["execution_authorization"]["decision_id"] == "DEC-P4-001"
        assert payload["paths"][0]["external_calls_actual"] == 1
        assert marker.exists()


def test_usability_missing_telemetry_is_inconclusive():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        plan, manifest, receipt = gate_fixture(root)
        runner, _ = runner_fixture(root, with_telemetry=False)
        env = runner_env(root, plan, manifest, receipt)
        result = run([str(runner), "run"], root, env)
        payload = json.loads(Path(env["USABILITY_RESULTS_JSON"]).read_text(encoding="utf-8"))
        assert result.returncode != 0
        assert payload["result_outcome"] == "inconclusive"
        assert payload["claim_eligibility"] == "none"


def evaluator_fixture(root):
    task = root / "task.json"
    tool = root / "tool.json"
    baseline = root / "baseline.json"
    metric = {
        "id": "answer_accuracy",
        "label": "Answer Accuracy",
        "measurement_method": "numeric_value",
        "source_field": "accuracy",
        "success_threshold": {"operator": ">=", "value": 0.8},
        "minimum_samples": 5,
        "evidence_fields": ["evidence"],
    }
    write_json(task, {
        "task_id": "BM_DYNAMIC",
        "rubric_approved": True,
        "metrics": [metric],
    })
    common = {"task_id": "BM_DYNAMIC", "status": "completed", "execution_mode": "full", "exit_code": 0, "sample_count": 5, "evidence": ["cases.json"]}
    write_json(tool, {**common, "runner_type": "tool", "accuracy": 0.8})
    write_json(baseline, {**common, "runner_type": "baseline", "accuracy": 0.6})
    return tool, baseline, task


def test_evaluator_uses_task_defined_raw_metrics_without_default_scores():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool, baseline, task = evaluator_fixture(root)
        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        assert list(evaluator.results["tool"]) == ["answer_accuracy"]
        result = evaluator.results["tool"]["answer_accuracy"]
        assert result["raw_value"] == 0.8
        assert result["threshold_met"] is True
        assert "score" not in result
        assert result["sample_adequacy"] == "meets_minimum"
        assert "confidence" not in result


def test_evaluator_report_is_raw_only_and_has_no_html_dashboard():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool, baseline, task = evaluator_fixture(root)
        report = root / "report.md"
        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        evaluator.generate_report(str(report))
        assert "Raw Value" in read(report)
        assert "Score (0-10)" not in read(report)
        assert not hasattr(evaluator, "generate_html_dashboard")


def test_phase_workflows_encode_v2_decision_boundaries():
    phase1 = read(SKILL_ROOT / "workflows/phase1_explore.md")
    phase3 = read(SKILL_ROOT / "workflows/phase3_quality.md")
    phase4 = read(SKILL_ROOT / "workflows/phase4_usability.md")
    phase5 = read(SKILL_ROOT / "workflows/phase5_benchmark.md")
    export = read(SKILL_ROOT / "workflows/optional_interview_export.md")
    assert "Scoped" in phase1 and "penetration testing" in phase1
    assert "coverage ledger" in phase1.lower()
    assert "Do not modify production code" in phase3
    assert "oracle provenance" in phase3.lower()
    assert "verification_manifest.json" in phase4 and "decision_id" in phase4
    assert "raw" in phase5.lower() and "sample_adequacy" in phase5
    assert "candidate-claim" in export.lower() and "claim approval" in export.lower()
    assert "interview_evidence_pack.md" in export


def test_readme_distinguishes_three_evidence_levels_and_limits():
    readme = read(REPO_ROOT / "README.md")
    assert readme.startswith("# Project Verifier")
    for phrase in ("静态 contract tests", "本地 fixture tests", "Agent behavior evals", "可信度边界", "Stage Gate"):
        assert phrase in readme
    assert "渗透测试" in readme and "合规认证" in readme


def test_six_eval_fixtures_are_bound_to_prompts():
    evals = json.loads(read(SKILL_ROOT / "evals/evals.json"))["evals"]
    assert len(evals) == 6
    assert all(item.get("files") for item in evals)
    fixture_names = {path.name for path in FIXTURES.iterdir() if path.is_dir()}
    assert fixture_names == {
        "non_ai_cli",
        "ai_missing_credentials",
        "ai_local_backend",
        "ai_assisted_mixed",
        "stale_authorization",
        "partial_e2e_failure",
    }
    assert all((path / "fixture.json").is_file() for path in FIXTURES.iterdir() if path.is_dir())


def test_non_ai_and_ai_fixture_entrypoints_behave_as_declared():
    non_ai = FIXTURES / "non_ai_cli"
    result = run(["python3", "app.py", "input.csv", "output.csv"], non_ai)
    assert result.returncode == 0, result.stdout
    assert (non_ai / "output.csv").read_text(encoding="utf-8") == "name,value\nalpha,2\n"
    (non_ai / "output.csv").unlink()

    missing = FIXTURES / "ai_missing_credentials"
    env = {key: value for key, value in os.environ.items() if key != "MODEL_API_KEY"}
    result = run(["python3", "app.py", "hello"], missing, env)
    assert result.returncode == 2
    assert "MODEL_API_KEY" in result.stdout

    local = FIXTURES / "ai_local_backend"
    result = run(["python3", "app.py", "hello"], local)
    assert result.returncode == 0
    assert json.loads(result.stdout)["answer"] == "local:hello"

    mixed = FIXTURES / "ai_assisted_mixed"
    result = run(["python3", "app.py", "local", " hello "], mixed)
    assert result.returncode == 0 and result.stdout.strip() == "hello"
    result = run(["python3", "app.py", "ai", "hello"], mixed, env)
    assert result.returncode == 2 and "MODEL_API_KEY" in result.stdout


def test_stale_authorization_and_partial_e2e_fixtures_expose_expected_failure():
    stale = FIXTURES / "stale_authorization"
    result = run(
        validator_command(
            stale / "phase4_usability_plan.md",
            stale / "verification_manifest.json",
            stale / "phase4_live_execution.json",
            revision="fixture-rev",
        ),
        stale,
    )
    assert result.returncode != 0 and "proposal" in result.stdout.lower()

    partial = FIXTURES / "partial_e2e_failure/tests/usability"
    success = run(["sh", "usability_P0_success.sh"], partial)
    failure = run(["sh", "usability_P0_failure.sh"], partial)
    assert success.returncode == 0
    assert failure.returncode == 7


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
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
