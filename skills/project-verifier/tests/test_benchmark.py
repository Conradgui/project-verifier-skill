import json
import tempfile
import unittest
from pathlib import Path

from helpers import REPO_ROOT, SKILL_ROOT, load_module, run, write_json


TASK_TEMPLATE = SKILL_ROOT / "templates/benchmark_task_template.json"
CONTRACT = SKILL_ROOT / "scripts/validate_benchmark_task.py"
EVALUATOR = SKILL_ROOT / "templates/benchmark_evaluator_template.py"
RUNNER = SKILL_ROOT / "templates/run_benchmark_template.sh"
WORKFLOW = SKILL_ROOT / "workflows/stage4_benchmark.md"

CONTRACT_MODULE = load_module(CONTRACT, "benchmark_contract")


def task_definition(rubric_approved=True, minimum_samples=3):
    task = {
        "schema_version": "3.0",
        "task_id": "BM_001",
        "feature_id": "retrieval_answering",
        "characteristic_source": {
            "evidence_refs": ["project_profile.json#feature.retrieval"],
            "candidate_characteristic": "grounded_answers",
        },
        "user_selected_direction": "answer_quality",
        "comparison_claim": "The retrieval path improves grounded answer accuracy over the approved baseline.",
        "decision_use": "Choose whether to retain the retrieval configuration.",
        "user_path_ids": ["P0_answer_question"],
        "backend": {"name": "built_in", "version": "fixture-v1", "fallback_reason": None},
        "baseline": {"type": "no_retrieval", "identity": "baseline-fixture", "equivalence_deviations": []},
        "dataset": {
            "dataset_id": "fixture-dataset",
            "sha256": "a" * 64,
            "samples": [
                {"id": "S1", "provenance": "existing_test", "evidence_refs": ["tests/fixture_s1.json"]},
                {"id": "S2", "provenance": "existing_test", "evidence_refs": ["tests/fixture_s2.json"]},
                {"id": "S3", "provenance": "existing_test", "evidence_refs": ["tests/fixture_s3.json"]},
            ],
        },
        "final_plan_approval": {
            "decision_id": "DEC-PLAN-001",
            "proposal_sha256": "",
            "source_revision": "git:fixture-revision",
            "receipt_path": "project_verification_workbench/authorizations/BM_001_plan.json",
            "envelope_path": "project_verification_workbench/authorizations/BM_001_plan_envelope.json",
        },
        "rubric_approved": rubric_approved,
        "metrics": [
            {
                "id": "grounded_accuracy",
                "label": "Grounded accuracy",
                "measurement_method": "numeric_value",
                "source_field": "grounded_accuracy",
                "per_sample_field": "grounded_accuracy_by_sample",
                "judge_category": "quality",
                "success_threshold": {"operator": ">=", "value": 0.7},
                "comparison_contract": {"operator": ">=", "minimum_margin": 0.1},
                "minimum_samples": minimum_samples,
                "evidence_fields": ["sample_evidence"],
            }
        ],
        "execution": {
            "mode": "full",
            "minimum_samples": minimum_samples,
            "max_calls": 3,
            "max_retries": 1,
            "timeout_seconds": 30,
        },
    }
    task["final_plan_approval"]["proposal_sha256"] = CONTRACT_MODULE.proposal_sha256(task)
    return task


def runner_output(role, value=0.8, sample_ids=None, evidence=True):
    sample_ids = sample_ids or ["S1", "S2", "S3"]
    return {
        "task_id": "BM_001",
        "runner_type": role,
        "status": "completed",
        "execution_mode": "full",
        "exit_code": 0,
        "grounded_accuracy": value,
        "grounded_accuracy_by_sample": {sample_id: value for sample_id in sample_ids},
        "sample_ids": sample_ids,
        "sample_evidence": {sample_id: [f"fixture-{role}-{sample_id}.json"] for sample_id in sample_ids} if evidence else {},
    }


def execution_receipt(task, tool, baseline, mode="full", wrapper_exit_code=0, telemetry_status="valid"):
    telemetry = {
        "status": telemetry_status,
        "actual_calls": 2 if telemetry_status == "valid" else None,
        "actual_retries": 0 if telemetry_status == "valid" else None,
        "side_effects": [] if telemetry_status == "valid" else None,
    }
    return {
        "schema_version": "1.0",
        "receipt_type": "stage4_benchmark_execution",
        "receipt_id": "RCP-BM-001",
        "task_id": task["task_id"],
        "proposal_sha256": CONTRACT_MODULE.proposal_sha256(task),
        "dataset_sha256": task["dataset"]["sha256"],
        "execution_mode": mode,
        "wrapper_exit_code": wrapper_exit_code,
        "duration_seconds": 1.25,
        "tool_output": {
            "runner_type": "tool",
            "path": "project_verification_workbench/benchmarks/tool_result.json",
            "sha256": CONTRACT_MODULE.canonical_object_hash(tool),
        },
        "baseline_output": {
            "runner_type": "baseline",
            "path": "project_verification_workbench/benchmarks/baseline_result.json",
            "sha256": CONTRACT_MODULE.canonical_object_hash(baseline),
        },
        "backend": task["backend"],
        "baseline": task["baseline"],
        "log_path": "project_verification_workbench/benchmarks/execution.log",
        "plan_approval": {
            "decision_id": task["final_plan_approval"]["decision_id"],
            "proposal_sha256": task["final_plan_approval"]["proposal_sha256"],
            "source_revision": task["final_plan_approval"]["source_revision"],
        },
        "execution_authorization": {
            "decision_id": "DEC-EXEC-001",
            "decision_envelope_sha256": "b" * 64,
            "source_revision": task["final_plan_approval"]["source_revision"],
            "approved_limits": {"max_calls": 3, "max_retries": 1, "timeout_seconds": 30},
            "receipt_path": "project_verification_workbench/authorizations/BM_001_execution.json",
            "envelope_path": "project_verification_workbench/authorizations/BM_001_execution_envelope.json",
        },
        "telemetry": telemetry,
    }


class Stage4BenchmarkContractTests(unittest.TestCase):
    def test_runner_without_arguments_is_help_only(self):
        result = run(["bash", str(RUNNER)], REPO_ROOT)
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn("Usage:", result.stdout)

    def test_task_template_has_dual_input_and_receipt_binding_fields(self):
        payload = json.loads(TASK_TEMPLATE.read_text(encoding="utf-8"))
        for field in (
            "characteristic_source",
            "user_selected_direction",
            "comparison_claim",
            "decision_use",
            "user_path_ids",
            "backend",
            "baseline",
            "dataset",
            "final_plan_approval",
            "rubric_approved",
            "metrics",
            "execution",
        ):
            with self.subTest(field=field):
                self.assertIn(field, payload)

    def test_workflow_limits_user_decisions_and_preserves_plan_only(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for phrase in (
            "证据派生特征",
            "用户突出方向",
            "3-5",
            "两次关键决策",
            "最终方案确认",
            "plan_only",
            "not_supported",
            "inconclusive",
            "不生成通用评分",
            "stage4_benchmark_results.json",
            "benchmark_report.md",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, workflow)

    def test_preflight_rejects_duplicate_dataset_samples_before_profile_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "benchmarks/tasks"
            task_dir.mkdir(parents=True)
            task = task_definition()
            task["dataset"]["samples"][2]["id"] = "S2"
            write_json(task_dir / "task_BM_001.json", task)
            executor = root / "benchmarks/benchmark_executor.sh"
            executor.parent.mkdir(exist_ok=True)
            executor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executor.chmod(0o755)
            result = run(
                ["bash", str(RUNNER), "preflight"],
                root,
                env={
                    "PROJECT_VERIFIER_PROJECT_ROOT": str(root),
                    "BENCHMARK_TASK_DIR": "benchmarks/tasks",
                    "BENCHMARK_EXECUTOR": "benchmarks/benchmark_executor.sh",
                },
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("unique", result.stdout.lower())
            self.assertFalse((root / "project_verification_workbench").exists())

    def test_runner_rejects_executor_inside_workbench_before_any_gate_or_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "benchmarks/tasks"
            task_dir.mkdir(parents=True)
            executor = root / "project_verification_workbench/benchmarks/benchmark_executor.sh"
            executor.parent.mkdir(parents=True)
            executor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executor.chmod(0o755)
            result = run(
                ["bash", str(RUNNER), "preflight"],
                root,
                env={
                    "PROJECT_VERIFIER_PROJECT_ROOT": str(root),
                    "BENCHMARK_TASK_DIR": "benchmarks/tasks",
                    "BENCHMARK_EXECUTOR": "project_verification_workbench/benchmarks/benchmark_executor.sh",
                },
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("must not live inside project_verification_workbench", result.stdout)

    def test_runner_receipt_writer_binds_outputs_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workbench = root / "project_verification_workbench/benchmarks"
            workbench.mkdir(parents=True)
            task = task_definition()
            task_path = root / "task.json"
            tool_path = workbench / "tool.json"
            baseline_path = workbench / "baseline.json"
            telemetry_path = workbench / "telemetry.json"
            log_path = workbench / "executor.log"
            receipt_path = workbench / "receipt.json"
            authorization_dir = root / "project_verification_workbench/authorizations"
            authorization_dir.mkdir(parents=True)
            authorization_receipt = authorization_dir / "BM_001_execution.json"
            authorization_envelope = authorization_dir / "BM_001_execution_envelope.json"
            tool = runner_output("tool", value=0.85)
            baseline = runner_output("baseline", value=0.7)
            write_json(task_path, task)
            write_json(tool_path, tool)
            write_json(baseline_path, baseline)
            write_json(telemetry_path, {"actual_calls": 2, "actual_retries": 0, "side_effects": []})
            log_path.write_text("fixture execution\n", encoding="utf-8")
            write_json(authorization_receipt, {"fixture": "authorization"})
            write_json(authorization_envelope, {"fixture": "envelope"})
            authorization = {
                "approved": True,
                "decision_id": "DEC-EXEC-001",
                "decision_envelope_sha256": "b" * 64,
                "approved_source_revision": "git:fixture-revision",
                "current_source_revision": "git:fixture-revision",
                "approved_limits": {"max_calls": 3, "max_retries": 1, "timeout_seconds": 30},
                "source_policy": "exact",
            }
            command = [
                "python3", str(CONTRACT), "write-receipt", "--task", str(task_path), "--project-root", str(root),
                "--mode", "full", "--exit-code", "0", "--duration-seconds", "1.25",
                "--tool-output", str(tool_path), "--baseline-output", str(baseline_path),
                "--telemetry", str(telemetry_path), "--log-path", str(log_path),
                "--execution-authorization", json.dumps(authorization),
                "--authorization-receipt", str(authorization_receipt),
                "--authorization-envelope", str(authorization_envelope), "--output", str(receipt_path),
            ]
            first = run(command, root)
            self.assertEqual(0, first.returncode, first.stdout)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual("project_verification_workbench/benchmarks/executor.log", receipt["log_path"])
            self.assertEqual(CONTRACT_MODULE.canonical_object_hash(tool), receipt["tool_output"]["sha256"])
            second = run(command, root)
            self.assertNotEqual(0, second.returncode)
            self.assertIn("already exists", second.stdout.lower())

    def test_contract_rejects_workbench_escape_and_unapproved_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(CONTRACT_MODULE.BenchmarkContractError):
                CONTRACT_MODULE.workbench_output_path(root, "project_verification_workbench/../../outside/receipt.json")

            task = task_definition(rubric_approved=False)
            task_path = root / "task.json"
            write_json(task_path, task)
            with self.assertRaises(CONTRACT_MODULE.BenchmarkContractError) as raised:
                CONTRACT_MODULE.validate_execution_envelope(task_path, root / "missing-envelope.json", 1, 0, 1)
            self.assertIn("rubric_approved", str(raised.exception))

    def test_evaluator_cli_rejects_receipt_outside_workbench(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            task_path = root / "task.json"
            write_json(task_path, task_definition())
            external_receipt = Path(tmp) / "external-receipt.json"
            write_json(external_receipt, {})
            result = run(
                ["python3", str(EVALUATOR), str(task_path), str(external_receipt), str(root), str(root / "manifest.json")],
                root,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("project_verification_workbench", result.stdout)


class Stage4BenchmarkEvaluatorTests(unittest.TestCase):
    def evaluator(self):
        module = load_module(EVALUATOR, "benchmark_evaluator_v3")

        class FixtureEvaluator:
            def evaluate(self, task, tool, baseline, receipt=None, current_source_revision=None):
                revision = current_source_revision
                if revision is None and isinstance(task, dict):
                    revision = task.get("final_plan_approval", {}).get("source_revision")
                return module.evaluate(task, tool, baseline, receipt, revision)

        return FixtureEvaluator()

    def test_evaluator_requires_matching_full_execution_receipt_for_supported_claim(self):
        task = task_definition()
        tool = runner_output("tool", value=0.85)
        baseline = runner_output("baseline", value=0.7)
        no_receipt = self.evaluator().evaluate(task, tool, baseline)
        self.assertEqual("inconclusive", no_receipt["claim_status"])
        self.assertEqual("not_measured", no_receipt["metrics"][0]["status"])

        receipt = execution_receipt(task, tool, baseline)
        unbound_revision = load_module(EVALUATOR, "benchmark_evaluator_unbound").evaluate(task, tool, baseline, receipt)
        self.assertEqual("inconclusive", unbound_revision["claim_status"])
        result = self.evaluator().evaluate(task, tool, baseline, receipt)
        self.assertEqual("supported", result["claim_status"])
        metric = result["metrics"][0]
        self.assertEqual(0.85, metric["tool"]["raw_value"])
        self.assertAlmostEqual(0.7, metric["baseline"]["raw_value"])
        self.assertTrue(metric["comparison_met"])
        self.assertTrue(metric["success_threshold_met"])
        self.assertNotIn("score", result)
        self.assertNotIn("radar", result)

    def test_evaluator_rejects_pilot_or_mismatched_receipt_even_with_good_raw_values(self):
        task = task_definition()
        tool = runner_output("tool", value=0.85)
        baseline = runner_output("baseline", value=0.7)
        pilot = execution_receipt(task, tool, baseline, mode="pilot")
        pilot_result = self.evaluator().evaluate(task, tool, baseline, pilot)
        self.assertEqual("inconclusive", pilot_result["claim_status"])

        mismatched = execution_receipt(task, tool, baseline)
        mismatched["dataset_sha256"] = "c" * 64
        mismatched_result = self.evaluator().evaluate(task, tool, baseline, mismatched)
        self.assertEqual("inconclusive", mismatched_result["claim_status"])

        stale = self.evaluator().evaluate(task, tool, baseline, execution_receipt(task, tool, baseline), "git:changed-revision")
        self.assertEqual("inconclusive", stale["claim_status"])

    def test_evaluator_uses_unique_dataset_samples_and_success_threshold(self):
        task = task_definition()
        tool = runner_output("tool", value=0.65)
        baseline = runner_output("baseline", value=0.4)
        threshold_result = self.evaluator().evaluate(task, tool, baseline, execution_receipt(task, tool, baseline))
        self.assertEqual("not_supported", threshold_result["claim_status"])
        self.assertFalse(threshold_result["metrics"][0]["success_threshold_met"])
        self.assertTrue(threshold_result["metrics"][0]["comparison_met"])

        aggregate_only = runner_output("tool", value=0.99)
        aggregate_only["grounded_accuracy_by_sample"] = {"S1": 0.4, "S2": 0.5, "S3": 0.6}
        aggregate_result = self.evaluator().evaluate(
            task, aggregate_only, baseline, execution_receipt(task, aggregate_only, baseline)
        )
        self.assertEqual("not_supported", aggregate_result["claim_status"])
        self.assertEqual(0.5, aggregate_result["metrics"][0]["tool"]["raw_value"])

        duplicate_tool = runner_output("tool", value=0.85, sample_ids=["S1", "S1", "S2"])
        duplicate_result = self.evaluator().evaluate(
            task,
            duplicate_tool,
            baseline,
            execution_receipt(task, duplicate_tool, baseline),
        )
        self.assertEqual("inconclusive", duplicate_result["claim_status"])
        self.assertEqual("not_measured", duplicate_result["metrics"][0]["status"])

    def test_evaluator_refuses_unapproved_rubric_or_missing_sample_evidence(self):
        task = task_definition(rubric_approved=False)
        tool = runner_output("tool")
        baseline = runner_output("baseline", value=0.6)
        unapproved = self.evaluator().evaluate(task, tool, baseline, execution_receipt(task, tool, baseline))
        self.assertEqual("inconclusive", unapproved["claim_status"])
        self.assertEqual("not_measured", unapproved["metrics"][0]["status"])

        approved_task = task_definition()
        missing_evidence_tool = runner_output("tool", evidence=False)
        missing_evidence = self.evaluator().evaluate(
            approved_task,
            missing_evidence_tool,
            baseline,
            execution_receipt(approved_task, missing_evidence_tool, baseline),
        )
        self.assertEqual("inconclusive", missing_evidence["claim_status"])
        self.assertEqual("not_measured", missing_evidence["metrics"][0]["status"])

    def test_evaluator_preserves_negative_comparison(self):
        task = task_definition()
        tool = runner_output("tool", value=0.72)
        baseline = runner_output("baseline", value=0.9)
        result = self.evaluator().evaluate(task, tool, baseline, execution_receipt(task, tool, baseline))
        self.assertEqual("not_supported", result["claim_status"])
        self.assertFalse(result["metrics"][0]["comparison_met"])

    def test_evaluator_requires_blinded_judge_evidence_and_refuses_judge_only_safety(self):
        task = task_definition()
        metric = task["metrics"][0]
        metric.update({
            "measurement_method": "llm_judge_score",
            "source_field": "judge_results",
            "evidence_fields": ["judge_results"],
            "success_threshold": {"operator": ">=", "value": 7.0},
            "comparison_contract": {"operator": ">=", "minimum_margin": 0.5},
        })
        task["final_plan_approval"]["proposal_sha256"] = CONTRACT_MODULE.proposal_sha256(task)
        tool = runner_output("tool")
        baseline = runner_output("baseline")
        for output, score in ((tool, 8.0), (baseline, 7.0)):
            output["judge_results"] = [
                {
                    "metric_id": "grounded_accuracy", "sample_id": sample_id, "score": score,
                    "evidence": f"judge-{sample_id}.json", "judge_prompt": "fixture prompt",
                    "model": "fixture-model", "model_version": "v1", "blinded": True, "randomized_order": True,
                }
                for sample_id in output["sample_ids"]
            ]
        supported = self.evaluator().evaluate(task, tool, baseline, execution_receipt(task, tool, baseline))
        self.assertEqual("supported", supported["claim_status"])

        tool["judge_results"][0]["blinded"] = False
        unblinded = self.evaluator().evaluate(task, tool, baseline, execution_receipt(task, tool, baseline))
        self.assertEqual("inconclusive", unblinded["claim_status"])

        tool["judge_results"][0]["blinded"] = True
        metric["judge_category"] = "safety_regression"
        task["final_plan_approval"]["proposal_sha256"] = CONTRACT_MODULE.proposal_sha256(task)
        safety = self.evaluator().evaluate(task, tool, baseline, execution_receipt(task, tool, baseline))
        self.assertEqual("inconclusive", safety["claim_status"])


if __name__ == "__main__":
    unittest.main()
