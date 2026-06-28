#!/usr/bin/env python3
"""Contract tests for conditional live testing and evidence-backed AI evals."""

import importlib.util
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


def read(path):
    return path.read_text(encoding="utf-8")


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_evaluator():
    spec = importlib.util.spec_from_file_location("benchmark_evaluator_template", EVALUATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BenchmarkEvaluator


def test_orchestrator_is_conditional_and_persists_manifest():
    skill = read(SKILL_ROOT / "SKILL.md")
    assert "description: >-\n  Use when" in skill
    assert "verification_manifest.md" in skill
    assert "pending / in_progress / completed / blocked / skipped / not_applicable / failed" in skill
    assert "Phase 1 through Phase 3" in skill
    assert "Phase 6" in skill and "optional" in skill.lower()


def test_phase_gates_and_optional_outputs():
    phase2 = read(SKILL_ROOT / "workflows/phase2_diagrams.md")
    phase3 = read(SKILL_ROOT / "workflows/phase3_quality.md")
    phase4 = read(SKILL_ROOT / "workflows/phase4_usability.md")
    phase6 = read(SKILL_ROOT / "workflows/phase6_interview.md")

    assert "before writing the document package" in phase2.lower()
    assert "README update copy" in phase2 and "optional" in phase2.lower()
    assert "Do not record live traffic" in phase3
    assert "phase4_usability_plan.md" in phase4
    assert "preflight" in phase4 and "execution authorization" in phase4.lower()
    assert "explicitly opted in" in phase6
    assert "Do not silently select a generic role" in phase6
    assert "80%" not in phase6
    assert "vcrpy" not in phase3


def test_phase5_is_guided_ai_eval_and_decoupled_from_interview_pack():
    phase5 = read(SKILL_ROOT / "workflows/phase5_benchmark.md")
    for required in (
        "AI / AI-assisted / non-AI / unknown",
        "ready_now / needs_setup / plan_only / rejected",
        "Accept recommended set",
        "phase5_benchmark_plan.md",
        "pilot_only",
        "benchmarks/results/benchmark_radar.html",
        "whether to enter Phase 6",
    ):
        assert required in phase5
    assert "interview_evidence_pack/benchmark_radar.html" not in phase5
    assert "resume evidence pitch" not in phase5.lower()


def test_readme_documents_conditional_three_tier_flow():
    readme = read(REPO_ROOT / "README.md")
    assert "L1 Mock Quality" in readme
    assert "L2 Live Usability/E2E" in readme
    assert "L3 AI Comparative Eval" in readme
    assert "Phase 6" in readme and "可选" in readme
    assert "plan-only" in readme


def test_eval_suite_covers_six_conditional_scenarios():
    payload = json.loads(EVALS_PATH.read_text(encoding="utf-8"))
    assert payload["skill_name"] == "project-verifier"
    assert [item["id"] for item in payload["evals"]] == [1, 2, 3, 4, 5, 6]
    combined = json.dumps(payload, ensure_ascii=False)
    for required in (
        "non-AI",
        "OPENAI_API_KEY",
        "explicit execution authorization",
        "status skipped",
        "pilot_only",
        "execution_mode full",
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
        assert all(result["score"] is None for result in evaluator.scores["tool"].values())


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
        result = evaluator.scores["tool"]["stability"]
        assert result["score"] is None
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
        write_json(task, {"task_id": "BM_PILOT", "metrics": [{
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
        result = evaluator.scores["tool"]["completeness"]
        assert result["score"] is None
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
        write_json(task, {"task_id": "BM_PLAN", "metrics": [{
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
        result = evaluator.scores["tool"]["completeness"]
        assert result["score"] is None
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
        write_json(task, {"task_id": "BM_MODE", "metrics": [{
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
        result = evaluator.scores["tool"]["completeness"]
        assert result["score"] is None
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
        write_json(task, {"task_id": "BM_EXIT", "metrics": [{
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
        result = evaluator.scores["tool"]["completeness"]
        assert result["score"] is None
        assert "exit_code" in result["not_measured_reason"]


def test_evaluator_rejects_out_of_range_score_mapping():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        payload = {"task_id": "BM_RANGE", "status": "completed", "execution_mode": "full", "exit_code": 0, "token_count": 10}
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_RANGE", "metrics": [{
            "id": "cost_efficiency",
            "measurement_method": "numeric_ratio",
            "success_threshold": {"operator": "<=", "value": 1.0},
            "score_mapping": [{"max_ratio": 1.0, "score": 999}],
            "minimum_samples": 1,
            "evidence_fields": ["token_count"],
            "source_field": "token_count",
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.scores["tool"]["cost_efficiency"]
        assert result["score"] is None
        assert "0 and 10" in result["not_measured_reason"]


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
        write_json(task, {"task_id": "BM_SAMPLE", "metrics": [{
            "id": "cost_efficiency",
            "measurement_method": "numeric_ratio",
            "success_threshold": {"operator": "<=", "value": 1.0},
            "score_mapping": [{"max_ratio": 1.0, "score": 5}, {"score": 2}],
            "minimum_samples": 1,
            "evidence_fields": ["token_count"],
            "source_field": "token_count",
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.scores["tool"]["cost_efficiency"]
        assert result["score"] is None
        assert "sample_count" in result["not_measured_reason"]


def test_evaluator_supports_traceable_llm_judge_results():
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
            "confidence": "medium",
        }]
        payload = {"task_id": "BM_JUDGE", "status": "completed", "execution_mode": "full", "exit_code": 0, "judge_results": judge_result}
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_JUDGE", "metrics": [{
            "id": "completeness",
            "measurement_method": "llm_judge_score",
            "success_threshold": {"operator": ">=", "value": 7.0},
            "score_mapping": "judge_score_0_to_10",
            "minimum_samples": 1,
            "evidence_fields": ["judge_results"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.scores["tool"]["completeness"]
        assert result["score"] == 8
        assert result["threshold_met"] is True
        assert "judge-model" in " ".join(result["evidence"])


def test_evaluator_rejects_unknown_judge_confidence():
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
            "confidence": "certain",
        }]
        payload = {"task_id": "BM_JUDGE_BAD", "status": "completed", "execution_mode": "full", "exit_code": 0, "judge_results": judge_result}
        write_json(tool, {**payload, "runner_type": "tool"})
        write_json(baseline, {**payload, "runner_type": "baseline"})
        write_json(task, {"task_id": "BM_JUDGE_BAD", "metrics": [{
            "id": "completeness",
            "measurement_method": "llm_judge_score",
            "success_threshold": {"operator": ">=", "value": 7.0},
            "score_mapping": "judge_score_0_to_10",
            "minimum_samples": 1,
            "evidence_fields": ["judge_results"],
        }]})

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        result = evaluator.scores["tool"]["completeness"]
        assert result["score"] is None
        assert "traceable judge result" in result["not_measured_reason"]


def test_evaluator_scores_only_approved_assertion_rubric():
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
                "metrics": [{
                    "id": "completeness",
                    "measurement_method": "assertion_rate",
                    "success_threshold": {"operator": ">=", "value": 1.0},
                    "score_mapping": "pass_rate_x_10",
                    "minimum_samples": 2,
                    "evidence_fields": ["assertions"],
                    "assertion_tags": ["completeness"],
                }],
            },
        )

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        assert evaluator.scores["tool"]["completeness"]["score"] == 5
        assert evaluator.scores["baseline"]["completeness"]["score"] == 10
        assert evaluator.scores["tool"]["completeness"]["threshold_met"] is False
        assert evaluator.scores["baseline"]["completeness"]["threshold_met"] is True


def test_evaluator_report_separates_score_from_threshold_result():
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
        write_json(task, {"task_id": "BM_REPORT", "metrics": [{
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
        assert "| **Completeness** | 0.500 | 1.000 | 5 | 10 | No | Yes |" in report_text
        assert "## Not Yet Proven" in report_text


def test_evaluator_does_not_create_radar_for_too_few_metrics():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        html = root / "radar.html"
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
        write_json(task, {"task_id": "BM_004", "metrics": [{
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
        assert evaluator.generate_html_dashboard(str(html)) is False
        assert not html.exists()


def test_evaluator_creates_radar_for_three_approved_metrics():
    Evaluator = load_evaluator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = root / "tool.json"
        baseline = root / "baseline.json"
        task = root / "task.json"
        html = root / "radar.html"
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
                "score_mapping": "pass_rate_x_10",
                "minimum_samples": 1,
                "evidence_fields": ["assertions"],
                "assertion_tags": [metric],
            })
        write_json(task, {
            "task_id": "BM_RADAR",
            "tool_label": "Project App",
            "baseline": {"type": "raw_llm", "label": "Approved Raw Model"},
            "metrics": metrics,
        })

        evaluator = Evaluator(str(tool), str(baseline), str(task))
        evaluator.load_data()
        evaluator.evaluate()
        assert evaluator.generate_html_dashboard(str(html)) is True
        html_text = html.read_text(encoding="utf-8")
        assert "Project App" in html_text
        assert "Approved Raw Model" in html_text


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
        assert evaluator.scores["tool"]["completeness"]["score"] == 10
        assert evaluator.scores["tool"]["stability"]["score"] == 10


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
        result = evaluator.scores["tool"]["latency"]
        assert result["score"] is None
        assert "finite numeric" in result["not_measured_reason"]


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
        result = evaluator.scores["tool"]["completeness"]
        assert result["score"] is None
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
        result = evaluator.scores["tool"]["completeness"]
        assert result["score"] is None
        assert "list" in result["not_measured_reason"]


def make_usability_fixture(root):
    runner = root / "run_usability.sh"
    runner.write_text(read(USABILITY_RUNNER), encoding="utf-8")
    runner.chmod(0o755)
    tests = root / "tests/usability"
    tests.mkdir(parents=True)
    marker = root / "executed.txt"
    script = tests / "usability_P0_guard.sh"
    script.write_text(f"#!/bin/sh\nprintf executed > '{marker}'\n", encoding="utf-8")
    script.chmod(0o755)
    return runner, marker


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
        env = {**os.environ, "USABILITY_RESULTS_JSON": str(results)}
        result = run_command([str(runner), "run"], root, env=env)
        assert result.returncode == 0, result.stdout
        payload = json.loads(results.read_text(encoding="utf-8"))
        assert payload["status"] == "completed"
        assert payload["execution_authorization"] is True
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
        script.write_text("#!/bin/sh\nexit 42\n", encoding="utf-8")
        script.chmod(0o755)
        results = root / "workbench/phase4_usability_results.json"
        env = {**os.environ, "USABILITY_RESULTS_JSON": str(results)}
        result = run_command([str(runner), "run"], root, env=env)
        assert result.returncode == 1
        payload = json.loads(results.read_text(encoding="utf-8"))
        assert payload["status"] == "failed"
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
