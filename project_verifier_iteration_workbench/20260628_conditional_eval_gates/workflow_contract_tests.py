#!/usr/bin/env python3
"""Contract tests for conditional live testing and evidence-backed AI evals."""

import importlib.util
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills/project-verifier"
EVALUATOR_PATH = SKILL_ROOT / "templates/benchmark_evaluator_template.py"
USABILITY_RUNNER = SKILL_ROOT / "templates/run_usability_template.sh"
EVALS_PATH = SKILL_ROOT / "evals/evals.json"
GATE_VALIDATOR = SKILL_ROOT / "scripts/validate_gate.py"


def read(path):
    return path.read_text(encoding="utf-8")


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def source_fixture(root):
    source_root = root / "source_project"
    source_root.mkdir()
    run_command(["git", "init"], source_root)
    run_command(["git", "config", "user.email", "fixture@example.com"], source_root)
    run_command(["git", "config", "user.name", "Fixture"], source_root)
    (source_root / "app.py").write_text("print('fixture')\n", encoding="utf-8")
    run_command(["git", "add", "app.py"], source_root)
    committed = run_command(["git", "commit", "-m", "fixture"], source_root)
    assert committed.returncode == 0, committed.stdout
    revision = run_command(["python3", str(GATE_VALIDATOR), "fingerprint", "--root", str(source_root)], root)
    assert revision.returncode == 0, revision.stdout
    return source_root, revision.stdout.strip()


def load_evaluator():
    spec = importlib.util.spec_from_file_location("benchmark_evaluator_template", EVALUATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BenchmarkEvaluator


def test_orchestrator_is_conditional_and_persists_manifest():
    skill = read(SKILL_ROOT / "SKILL.md")
    assert "description: >-\n  Use when" in skill
    assert "verification_manifest.json" in skill
    assert "five-phase" in skill
    assert "Phase 1–3" in skill
    assert "Optional Exports" in skill


def test_phase_gates_and_optional_outputs():
    phase2 = read(SKILL_ROOT / "workflows/phase2_diagrams.md")
    phase3 = read(SKILL_ROOT / "workflows/phase3_quality.md")
    phase4 = read(SKILL_ROOT / "workflows/phase4_usability.md")
    export = read(SKILL_ROOT / "workflows/optional_interview_export.md")

    assert "before writing" in phase2.lower()
    assert "Optional README Copy" in phase2
    assert "real first call is not Phase 3" in phase3
    assert "phase4_usability_plan.md" in phase4
    assert "preflight" in phase4 and "Execution Gate" in phase4
    assert "explicitly requests" in export
    assert "general mode or stop" in export
    assert "80%" not in export
    assert "vcrpy" not in phase3


def test_phase5_is_guided_ai_eval_and_decoupled_from_interview_pack():
    phase5 = read(SKILL_ROOT / "workflows/phase5_benchmark.md")
    for required in (
        "AI or AI-assisted",
        "ready_now`, `needs_setup`, `plan_only`, or `rejected",
        "accept recommendations",
        "phase5_benchmark_plan.md",
        "execution_scope: pilot",
        "sample_adequacy",
        "optional README or interview/portfolio export",
    ):
        assert required.lower() in phase5.lower()
    assert "interview_evidence_pack.md" not in phase5
    assert "resume evidence pitch" not in phase5.lower()


def test_readme_documents_conditional_three_tier_flow():
    readme = read(REPO_ROOT / "README.md")
    assert "L1 Offline Behavior" in readme
    assert "L2 Live E2E" in readme
    assert "L3 AI Comparative Eval" in readme
    assert "interview_evidence_pack.md" in readme and "可选" in readme
    assert "plan_only" in readme


def test_eval_suite_covers_six_conditional_scenarios():
    payload = json.loads(EVALS_PATH.read_text(encoding="utf-8"))
    assert payload["skill_name"] == "project-verifier"
    assert [item["id"] for item in payload["evals"]] == [1, 2, 3, 4, 5, 6]
    combined = json.dumps(payload, ensure_ascii=False)
    for required in (
        "non-AI",
        "MODEL_API_KEY",
        "revision-bound execution authorization",
        "proposal_sha256",
        "result_outcome partial",
        "feature-level classifications",
    ):
        assert required in combined
    for item in payload["evals"]:
        assert item["prompt"]
        assert item["expected_output"]
        assert len(item["expectations"]) >= 3


def test_evaluator_requires_preapproved_rubric():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        payload = {
            "task_id": "BM_001",
            "status": "completed",
            "execution_mode": "full",
            "exit_code": 0,
            "assertions": [{"text": "Output exists", "passed": True, "evidence": "result.json", "tags": ["completeness"]}],
            "errors": [],
        }
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_001", "metrics": []})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        assert evaluator.results["tool"] == {}


def test_evaluator_refuses_stability_from_single_run():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        write_json(tool, {"task_id": "BM_002", "status": "completed", "execution_mode": "full", "runner_type": "tool", "exit_code": 0, "runs": [{"exit_code": 0, "errors": []}], "errors": []})
        write_json(baseline, {"task_id": "BM_002", "status": "completed", "execution_mode": "full", "runner_type": "baseline", "exit_code": 0, "runs": [{"exit_code": 0, "errors": []}], "errors": []})
        write_json(
            task,
            {
                "task_id": "BM_002",
                "rubric_approved": True,
                "metrics": [{
                    "id": "stability",
                    "measurement_method": "repeated_success_rate",
                    "success_threshold": {"operator": ">=", "value": 0.95},
                    "score_mapping": "success_rate_x_10",
                    "minimum_samples": 3,
                    "evidence_fields": ["runs"],
                }],
            },
        )

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["stability"]
        assert "score" not in result
        assert "minimum_samples=3" in result["not_measured_reason"]


def test_evaluator_never_scores_pilot_only_output():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        payload = {
            "task_id": "BM_PILOT",
            "status": "pilot_only",
            "execution_mode": "pilot",
            "exit_code": 0,
            "assertions": [{"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]}],
            "errors": [],
        }
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_PILOT", "rubric_approved": True, "metrics": [{
            "id": "completeness",
            "measurement_method": "assertion_rate",
            "success_threshold": {"operator": ">=", "value": 1.0},
            "score_mapping": "pass_rate_x_10",
            "minimum_samples": 1,
            "evidence_fields": ["assertions"],
            "assertion_tags": ["completeness"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["completeness"]
        assert "score" not in result
        assert "pilot_only" in result["not_measured_reason"]


def test_evaluator_rejects_mismatched_task_identity():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        assertion = [{"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]}]
        write_json(tool, {"task_id": "BM_TOOL", "runner_type": "tool", "status": "completed", "execution_mode": "full", "exit_code": 0, "assertions": assertion})
        write_json(baseline, {"task_id": "BM_BASE", "runner_type": "baseline", "status": "completed", "execution_mode": "full", "exit_code": 0, "assertions": assertion})
        write_json(task, {"task_id": "BM_PLAN", "rubric_approved": True, "metrics": [{
            "id": "completeness",
            "measurement_method": "assertion_rate",
            "success_threshold": {"operator": ">=", "value": 1.0},
            "score_mapping": "pass_rate_x_10",
            "minimum_samples": 1,
            "evidence_fields": ["assertions"],
            "assertion_tags": ["completeness"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["completeness"]
        assert "score" not in result
        assert "task_id" in result["not_measured_reason"]


def test_evaluator_requires_full_execution_mode():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        assertion = [{"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]}]
        payload = {"task_id": "BM_MODE", "status": "completed", "execution_mode": "pilot", "exit_code": 0, "assertions": assertion}
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_MODE", "rubric_approved": True, "metrics": [{
            "id": "completeness",
            "measurement_method": "assertion_rate",
            "success_threshold": {"operator": ">=", "value": 1.0},
            "score_mapping": "pass_rate_x_10",
            "minimum_samples": 1,
            "evidence_fields": ["assertions"],
            "assertion_tags": ["completeness"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["completeness"]
        assert "score" not in result
        assert "execution_mode" in result["not_measured_reason"]


def test_evaluator_rejects_nonzero_exit_for_completed_run():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        assertion = [{"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]}]
        write_json(tool, {"task_id": "BM_EXIT", "runner_type": "tool", "status": "completed", "execution_mode": "full", "exit_code": 1, "assertions": assertion})
        write_json(baseline, {"task_id": "BM_EXIT", "runner_type": "baseline", "status": "completed", "execution_mode": "full", "exit_code": 0, "assertions": assertion})
        write_json(task, {"task_id": "BM_EXIT", "rubric_approved": True, "metrics": [{
            "id": "completeness",
            "measurement_method": "assertion_rate",
            "success_threshold": {"operator": ">=", "value": 1.0},
            "score_mapping": "pass_rate_x_10",
            "minimum_samples": 1,
            "evidence_fields": ["assertions"],
            "assertion_tags": ["completeness"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["completeness"]
        assert "score" not in result
        assert "exit_code" in result["not_measured_reason"]


def test_evaluator_ignores_deprecated_score_mapping_and_keeps_raw_result():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        payload = {"task_id": "BM_RANGE", "status": "completed", "execution_mode": "full", "exit_code": 0, "token_count": 10, "sample_count": 1}
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_RANGE", "rubric_approved": True, "auxiliary_views": {"normalized_scores": {"approved": True}}, "metrics": [{
            "id": "cost_efficiency",
            "measurement_method": "numeric_ratio",
            "success_threshold": {"operator": "<=", "value": 1.0},
            "score_mapping": [{"max_value": 1.0, "score": 5}, {"score": 999}],
            "minimum_samples": 1,
            "evidence_fields": ["token_count"],
            "source_field": "token_count",
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["cost_efficiency"]
        assert "score" not in result
        assert result["raw_value"] == 1.0


def test_evaluator_handles_invalid_sample_count_without_crash():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        payload = {"task_id": "BM_SAMPLE", "status": "completed", "execution_mode": "full", "exit_code": 0, "token_count": 10, "sample_count": "invalid"}
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_SAMPLE", "rubric_approved": True, "metrics": [{
            "id": "cost_efficiency",
            "measurement_method": "numeric_ratio",
            "success_threshold": {"operator": "<=", "value": 1.0},
            "score_mapping": [{"max_value": 1.0, "score": 5}, {"score": 2}],
            "minimum_samples": 1,
            "evidence_fields": ["token_count"],
            "source_field": "token_count",
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["cost_efficiency"]
        assert "score" not in result
        assert "sample_count" in result["not_measured_reason"]


def test_evaluator_supports_traceable_blinded_llm_judge_results():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        judge_result = [{
            "metric_id": "completeness",
            "score": 8,
            "evidence": "judge-output.json",
            "judge_prompt": "Score against the approved rubric.",
            "model": "judge-model",
            "model_version": "2026-06",
            "blinded": True,
            "randomized_order": True,
        }]
        payload = {"task_id": "BM_JUDGE", "status": "completed", "execution_mode": "full", "exit_code": 0, "judge_results": judge_result}
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_JUDGE", "rubric_approved": True, "auxiliary_views": {"normalized_scores": {"approved": True}}, "metrics": [{
            "id": "completeness",
            "measurement_method": "llm_judge_score",
            "success_threshold": {"operator": ">=", "value": 7.0},
            "score_mapping": [{"min_value": 8, "score": 8}, {"score": 2}],
            "minimum_samples": 1,
            "evidence_fields": ["judge_results"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["completeness"]
        assert "score" not in result
        assert result["raw_value"] == 8
        assert result["threshold_met"] is True
        assert "judge-model" in " ".join(result["evidence"])


def test_evaluator_rejects_unblinded_judge_results():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        judge_result = [{
            "metric_id": "completeness",
            "score": 8,
            "evidence": "judge-output.json",
            "judge_prompt": "Score against the approved rubric.",
            "model": "judge-model",
            "model_version": "2026-06",
            "blinded": False,
            "randomized_order": True,
        }]
        payload = {"task_id": "BM_JUDGE_BAD", "status": "completed", "execution_mode": "full", "exit_code": 0, "judge_results": judge_result}
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_JUDGE_BAD", "rubric_approved": True, "metrics": [{
            "id": "completeness",
            "measurement_method": "llm_judge_score",
            "success_threshold": {"operator": ">=", "value": 7.0},
            "minimum_samples": 1,
            "evidence_fields": ["judge_results"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["completeness"]
        assert "score" not in result
        assert "blinded judge results" in result["not_measured_reason"]


def test_evaluator_reports_raw_assertion_rate_against_threshold():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        write_json(
            tool,
            {
                "status": "completed",
                "execution_mode": "full",
                "task_id": "BM_003",
                "runner_type": "tool",
                "exit_code": 0,
                "assertions": [
                    {"text": "A", "passed": True, "evidence": "a.json", "tags": ["completeness"]},
                    {"text": "B", "passed": False, "evidence": "b.log", "tags": ["completeness"]},
                ],
                "errors": [],
            },
        )
        write_json(
            baseline,
            {
                "status": "completed",
                "execution_mode": "full",
                "task_id": "BM_003",
                "runner_type": "baseline",
                "exit_code": 0,
                "assertions": [
                    {"text": "A", "passed": True, "evidence": "a.txt", "tags": ["completeness"]},
                    {"text": "B", "passed": True, "evidence": "b.txt", "tags": ["completeness"]},
                ],
                "errors": [],
            },
        )
        write_json(
            task,
            {
                "task_id": "BM_003",
                "rubric_approved": True,
                "auxiliary_views": {"normalized_scores": {"approved": True}},
                "metrics": [{
                    "id": "completeness",
                    "measurement_method": "assertion_rate",
                    "success_threshold": {"operator": ">=", "value": 1.0},
                    "score_mapping": [{"min_value": 1.0, "score": 10}, {"min_value": 0.5, "score": 5}, {"score": 0}],
                    "minimum_samples": 2,
                    "evidence_fields": ["assertions"],
                    "assertion_tags": ["completeness"],
                }],
            },
        )

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        assert evaluator.results["tool"]["completeness"]["raw_value"] == 0.5
        assert evaluator.results["baseline"]["completeness"]["raw_value"] == 1.0
        assert evaluator.results["tool"]["completeness"]["threshold_met"] is False
        assert evaluator.results["baseline"]["completeness"]["threshold_met"] is True


def test_evaluator_report_separates_raw_value_from_threshold_result():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        report = root / "report.md"
        tool_assertions = [
            {"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]},
            {"text": "B", "passed": False, "evidence": "b", "tags": ["completeness"]},
        ]
        baseline_assertions = [
            {"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]},
            {"text": "B", "passed": True, "evidence": "b", "tags": ["completeness"]},
        ]
        common = {"task_id": "BM_REPORT", "status": "completed", "execution_mode": "full", "exit_code": 0}
        write_json(tool, {**common, "runner_type": "tool", "assertions": tool_assertions})
        write_json(baseline, {**common, "runner_type": "baseline", "assertions": baseline_assertions})
        write_json(task, {"task_id": "BM_REPORT", "rubric_approved": True, "metrics": [{
            "id": "completeness",
            "measurement_method": "assertion_rate",
            "success_threshold": {"operator": ">=", "value": 1.0},
            "score_mapping": "pass_rate_x_10",
            "minimum_samples": 2,
            "evidence_fields": ["assertions"],
            "assertion_tags": ["completeness"],
        }]})
        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        evaluator.generate_report(str(report))
        report_text = report.read_text(encoding="utf-8")
        assert "| Completeness | 0.5 | 1 | No | Yes | 2 | 2 |" in report_text
        assert "## Measurement Coverage" in report_text


def test_evaluator_exposes_no_html_dashboard_for_one_metric():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        payload = {
            "task_id": "BM_004",
            "status": "completed",
            "execution_mode": "full",
            "exit_code": 0,
            "assertions": [{"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]}],
            "errors": [],
        }
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_004", "rubric_approved": True, "metrics": [{
            "id": "completeness",
            "measurement_method": "assertion_rate",
            "success_threshold": {"operator": ">=", "value": 1.0},
            "score_mapping": "pass_rate_x_10",
            "minimum_samples": 1,
            "evidence_fields": ["assertions"],
            "assertion_tags": ["completeness"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        assert not hasattr(evaluator, "generate_html_dashboard")


def test_evaluator_reports_three_raw_metrics_without_visual_normalization():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        report = root / "report.md"
        assertions = [
            {"text": "Complete", "passed": True, "evidence": "a", "tags": ["completeness"]},
            {"text": "Controlled", "passed": True, "evidence": "b", "tags": ["control"]},
            {"text": "Usable", "passed": True, "evidence": "c", "tags": ["ux"]},
        ]
        write_json(tool, {"task_id": "BM_RADAR", "status": "completed", "execution_mode": "full", "runner_type": "tool", "exit_code": 0, "assertions": assertions, "errors": []})
        write_json(baseline, {"task_id": "BM_RADAR", "status": "completed", "execution_mode": "full", "runner_type": "baseline", "exit_code": 0, "assertions": assertions, "errors": []})
        metrics = []
        for metric in ("completeness", "control", "ux"):
            metrics.append({
                "id": metric,
                "measurement_method": "assertion_rate",
                "success_threshold": {"operator": ">=", "value": 1.0},
                "minimum_samples": 1,
                "evidence_fields": ["assertions"],
                "assertion_tags": [metric],
            })
        write_json(task, {
            "task_id": "BM_RADAR",
            "rubric_approved": True,
            "tool_label": "Project App",
            "baseline": {"type": "raw_llm", "label": "Approved Raw Model"},
            "metrics": metrics,
        })

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        evaluator.generate_report(str(report))
        report_text = report.read_text(encoding="utf-8")
        assert "Project App" in report_text
        assert "Approved Raw Model" in report_text
        assert all(result["raw_value"] == 1.0 for result in evaluator.results["tool"].values())
        assert "Auxiliary Score" not in report_text
        assert "0-10" not in report_text


def test_evaluator_ignores_malformed_evidence_entries():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        common = {
            "task_id": "BM_MALFORMED",
            "status": "completed",
            "execution_mode": "full",
            "exit_code": 0,
            "assertions": [
                None,
                "bad",
                {"passed": True, "evidence": "missing-name", "tags": ["completeness"]},
                {"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]},
            ],
            "runs": [None, "bad", {"exit_code": 0, "errors": []}],
        }
        write_json(tool, {**common, "runner_type": "tool"})
        write_json(baseline, {**common, "runner_type": "baseline"})
        write_json(task, {
            "task_id": "BM_MALFORMED",
            "rubric_approved": True,
            "metrics": [
                {
                    "id": "completeness",
                    "measurement_method": "assertion_rate",
                    "success_threshold": {"operator": ">=", "value": 1.0},
                    "score_mapping": "pass_rate_x_10",
                    "minimum_samples": 1,
                    "evidence_fields": ["assertions"],
                    "assertion_tags": ["completeness"],
                },
                {
                    "id": "stability",
                    "measurement_method": "repeated_success_rate",
                    "success_threshold": {"operator": ">=", "value": 1.0},
                    "score_mapping": "success_rate_x_10",
                    "minimum_samples": 1,
                    "evidence_fields": ["runs"],
                },
            ],
        })

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        assert evaluator.results["tool"]["completeness"]["raw_value"] == 1.0
        assert evaluator.results["tool"]["stability"]["raw_value"] == 1.0


def test_evaluator_rejects_nonfinite_or_boolean_numeric_evidence():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        common = {
            "task_id": "BM_NUMERIC_TYPE",
            "status": "completed",
            "execution_mode": "full",
            "exit_code": 0,
            "sample_count": 1,
        }
        write_json(tool, {**common, "runner_type": "tool", "duration_seconds": True})
        write_json(baseline, {**common, "runner_type": "baseline", "duration_seconds": 1.0})
        write_json(task, {
            "task_id": "BM_NUMERIC_TYPE",
            "rubric_approved": True,
            "metrics": [{
                "id": "latency",
                "measurement_method": "numeric_ratio",
                "source_field": "duration_seconds",
                "success_threshold": {"operator": "<=", "value": 1.0},
                "score_mapping": [{"max_ratio": 1.0, "score": 10}, {"score": 0}],
                "minimum_samples": 1,
                "evidence_fields": ["duration_seconds"],
            }],
        })

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["latency"]
        assert "score" not in result
        assert "finite" in result["not_measured_reason"]


def test_evaluator_rejects_non_string_evidence_field_names():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        common = {
            "task_id": "BM_BAD_FIELDS",
            "status": "completed",
            "execution_mode": "full",
            "exit_code": 0,
            "assertions": [{"text": "A", "passed": True, "evidence": "a", "tags": ["completeness"]}],
        }
        write_json(tool, {**common, "runner_type": "tool"})
        write_json(baseline, {**common, "runner_type": "baseline"})
        write_json(task, {
            "task_id": "BM_BAD_FIELDS",
            "rubric_approved": True,
            "metrics": [{
                "id": "completeness",
                "measurement_method": "assertion_rate",
                "success_threshold": {"operator": ">=", "value": 1.0},
                "score_mapping": "pass_rate_x_10",
                "minimum_samples": 1,
                "evidence_fields": [[]],
                "assertion_tags": ["completeness"],
            }],
        })

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["completeness"]
        assert "score" not in result
        assert "field names" in result["not_measured_reason"]


def test_evaluator_handles_malformed_evidence_containers_without_crash():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        common = {
            "task_id": "BM_BAD_CONTAINERS",
            "status": "completed",
            "execution_mode": "full",
            "exit_code": 0,
            "assertions": 42,
        }
        write_json(tool, {**common, "runner_type": "tool"})
        write_json(baseline, {**common, "runner_type": "baseline"})
        write_json(task, {
            "task_id": "BM_BAD_CONTAINERS",
            "rubric_approved": True,
            "metrics": [{
                "id": "completeness",
                "measurement_method": "assertion_rate",
                "success_threshold": {"operator": ">=", "value": 1.0},
                "score_mapping": "pass_rate_x_10",
                "minimum_samples": 1,
                "evidence_fields": ["assertions"],
                "assertion_tags": ["completeness"],
            }],
        })

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.results["tool"]["completeness"]
        assert "score" not in result
        assert "list" in result["not_measured_reason"]


def make_usability_fixture(root):
    runner = root / "run_usability.sh"
    runner.write_text(read(USABILITY_RUNNER), encoding="utf-8")
    runner.chmod(0o755)
    tests = root / "tests/usability"
    tests.mkdir(parents=True)
    marker = root / "executed.txt"
    script = tests / "usability_P0_guard.sh"
    telemetry = tests / "reports/usability_P0_guard.telemetry.json"
    script.write_text(
        f"#!/bin/sh\nprintf executed > '{marker}'\nmkdir -p '{telemetry.parent}'\nprintf '%s' '{{\"external_calls_actual\":0,\"retries_actual\":0,\"side_effects\":[]}}' > '{telemetry}'\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return runner, marker


def authorized_usability_env(root, results, max_paths=1):
    source_root, source_revision = source_fixture(root)
    plan = root / "phase4_usability_plan.md"
    plan.write_text("approved usability plan\n", encoding="utf-8")
    digest = hashlib.sha256(plan.read_bytes()).hexdigest()
    decision = {
        "decision_id": "DEC-TEST-P4",
        "phase": "phase4",
        "decision_type": "live_execution",
        "proposal_sha256": digest,
        "source_revision": source_revision,
        "user_choice": "approved",
        "approved_limits": {"max_paths": max_paths, "max_calls_per_path": 1, "max_retries": 0, "timeout_seconds": 10},
        "approved_at": "2026-06-29T12:00:00+08:00",
        "invalidated_at": None,
    }
    manifest = {
        "schema_version": "2.0",
        "source_revision": {"revision": source_revision, "dirty": False, "captured_at": "2026-06-29T11:00:00+08:00"},
        "user_intent": {"goal": "runner regression", "target_users": ["owner"], "in_scope": ["P0"], "out_of_scope": [], "success_criteria": ["runner completes"], "risk_tolerance": "low"},
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
        "USABILITY_MAX_CALLS_PER_PATH": "1",
        "USABILITY_MAX_RETRIES": "0",
        "USABILITY_TIMEOUT_SECONDS": "10",
        "USABILITY_RESULTS_JSON": str(results),
    }


def run_command(command, cwd, env=None):
    return subprocess.run(
        command,
        cwd=cwd,
        env=env or os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_usability_runner_requires_explicit_mode():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner, marker = make_usability_fixture(root)
        result = run_command([str(runner)], root)
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert not marker.exists()


def test_usability_runner_does_not_grant_blanket_deno_permissions():
    assert "--allow-all" not in read(USABILITY_RUNNER)


def test_usability_preflight_never_executes_live_scripts():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner, marker = make_usability_fixture(root)
        result = run_command([str(runner), "preflight"], root)
        assert result.returncode == 0, result.stdout
        assert "Preflight passed" in result.stdout
        assert not marker.exists()


def test_usability_preflight_fails_when_no_scripts_exist():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner = root / "run_usability.sh"
        runner.write_text(read(USABILITY_RUNNER), encoding="utf-8")
        runner.chmod(0o755)
        result = run_command([str(runner), "preflight"], root)
        assert result.returncode == 1
        assert "No usability test directory" in result.stdout


def test_usability_preflight_reports_names_without_secret_values():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner, marker = make_usability_fixture(root)
        env = {**os.environ, "USABILITY_REQUIRED_ENV": "PRESENT_KEY MISSING_KEY", "PRESENT_KEY": "super-secret-value"}
        result = run_command([str(runner), "preflight"], root, env=env)
        assert result.returncode == 1
        assert "MISSING_KEY" in result.stdout
        assert "super-secret-value" not in result.stdout
        assert not marker.exists()


def test_usability_preflight_rejects_invalid_environment_names_cleanly():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner, marker = make_usability_fixture(root)
        env = {**os.environ, "USABILITY_REQUIRED_ENV": "INVALID-NAME"}
        result = run_command([str(runner), "preflight"], root, env=env)
        assert result.returncode == 1
        assert "Invalid environment variable name" in result.stdout
        assert "bad substitution" not in result.stdout.lower()
        assert not marker.exists()


def test_usability_run_writes_machine_readable_results():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner, marker = make_usability_fixture(root)
        results = root / "workbench/phase4_usability_results.json"
        env = authorized_usability_env(root, results)
        result = run_command([str(runner), "run"], root, env=env)
        assert result.returncode == 0, result.stdout
        payload = json.loads(results.read_text(encoding="utf-8"))
        assert payload["status"] == "completed"
        assert payload["execution_authorization"]["decision_id"] == "DEC-TEST-P4"
        assert payload["paths"][0]["path_id"] == "P0_guard"
        assert payload["paths"][0]["exit_code"] == 0
        assert marker.exists()


def test_usability_preflight_rejects_invalid_execution_bounds():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner, _ = make_usability_fixture(root)
        results = root / "workbench/phase4_usability_results.json"
        env = {
            **os.environ,
            "USABILITY_RESULTS_JSON": str(results),
            "USABILITY_MAX_CALLS_PER_PATH": "not-a-number",
            "USABILITY_MAX_RETRIES": "-3",
            "USABILITY_TIMEOUT_SECONDS": "60",
        }
        result = run_command([str(runner), "run"], root, env=env)
        assert result.returncode == 1
        assert "Invalid execution bound" in result.stdout
        assert not results.exists()


def test_usability_preflight_enforces_max_paths():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner, marker = make_usability_fixture(root)
        tests = root / "tests/usability"
        second = tests / "usability_P0_second.sh"
        second.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        second.chmod(0o755)
        env = {**os.environ, "USABILITY_MAX_PATHS": "1"}
        result = run_command([str(runner), "run"], root, env=env)
        assert result.returncode == 1
        assert "approved max_paths=1" in result.stdout
        assert not marker.exists()


def test_usability_results_preserve_script_exit_code():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner = root / "run_usability.sh"
        runner.write_text(read(USABILITY_RUNNER), encoding="utf-8")
        runner.chmod(0o755)
        tests = root / "tests/usability"
        tests.mkdir(parents=True)
        script = tests / "usability_P0_failure.sh"
        telemetry = tests / "reports/usability_P0_failure.telemetry.json"
        script.write_text(
            f"#!/bin/sh\nmkdir -p '{telemetry.parent}'\nprintf '%s' '{{\"external_calls_actual\":0,\"retries_actual\":0,\"side_effects\":[]}}' > '{telemetry}'\nexit 42\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        results = root / "workbench/phase4_usability_results.json"
        env = authorized_usability_env(root, results)
        result = run_command([str(runner), "run"], root, env=env)
        assert result.returncode == 1
        payload = json.loads(results.read_text(encoding="utf-8"))
        assert payload["phase_status"] == "completed"
        assert payload["result_outcome"] == "fail"
        assert payload["paths"][0]["exit_code"] == 42
        assert payload["paths"][0]["failure_stage"] == "script_execution"


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
