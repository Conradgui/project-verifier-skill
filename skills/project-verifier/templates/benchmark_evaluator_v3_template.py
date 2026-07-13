#!/usr/bin/env python3
"""Evaluate receipt-bound V3 Benchmark comparisons without universal scores."""

from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_benchmark_task_v3.py"
SPEC = importlib.util.spec_from_file_location("project_verifier_benchmark_contract_v3", CONTRACT_PATH)
CONTRACT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CONTRACT)
GATE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_gate_v3.py"
GATE_SPEC = importlib.util.spec_from_file_location("project_verifier_gate_v3", GATE_PATH)
GATE = importlib.util.module_from_spec(GATE_SPEC)
assert GATE_SPEC.loader is not None
GATE_SPEC.loader.exec_module(GATE)


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def compare(contract, value, reference=None, value_key="value"):
    if not isinstance(contract, dict):
        return None
    operator = contract.get("operator")
    if operator not in CONTRACT.OPERATORS:
        return None
    if reference is None:
        operand = contract.get(value_key)
        if not finite_number(operand):
            return None
        if operator == ">=":
            return value >= operand
        if operator == ">":
            return value > operand
        if operator == "<=":
            return value <= operand
        if operator == "<":
            return value < operand
        return value == operand
    margin = contract.get("minimum_margin")
    if not finite_number(reference) or not finite_number(margin):
        return None
    if operator == ">=":
        return value >= reference + margin
    if operator == ">":
        return value > reference + margin
    if operator == "<=":
        return value <= reference - margin
    if operator == "<":
        return value < reference - margin
    return abs(value - reference) <= margin


def not_measured(metric_id, reason):
    return {
        "metric_id": metric_id,
        "status": "not_measured",
        "tool": {"raw_value": None, "sample_count": 0, "sample_adequacy": "not_measured"},
        "baseline": {"raw_value": None, "sample_count": 0, "sample_adequacy": "not_measured"},
        "success_threshold_met": None,
        "comparison_met": None,
        "claim_component_met": None,
        "not_measured_reason": reason,
    }


def metric_result(metric, tool, baseline):
    metric_id = metric.get("id") if isinstance(metric, dict) else None
    if not isinstance(metric_id, str) or not metric_id:
        return not_measured("unknown", "metric id is invalid")
    field = metric["source_field"]
    evidence_fields = metric["evidence_fields"]
    for role, output in (("tool", tool), ("baseline", baseline)):
        missing_evidence = [name for name in evidence_fields if output.get(name) in (None, [], {})]
        if missing_evidence:
            return not_measured(metric_id, f"{role} output is missing evidence fields: " + ", ".join(missing_evidence))
    if metric["measurement_method"] == "numeric_value":
        tool_measurement = numeric_sample_measure(metric, tool)
        baseline_measurement = numeric_sample_measure(metric, baseline)
        if isinstance(tool_measurement, str):
            return not_measured(metric_id, "tool " + tool_measurement)
        if isinstance(baseline_measurement, str):
            return not_measured(metric_id, "baseline " + baseline_measurement)
        tool_value, tool_samples = tool_measurement
        baseline_value, baseline_samples = baseline_measurement
    else:
        tool_judge = blinded_judge_measure(metric, tool)
        baseline_judge = blinded_judge_measure(metric, baseline)
        if isinstance(tool_judge, str):
            return not_measured(metric_id, "tool " + tool_judge)
        if isinstance(baseline_judge, str):
            return not_measured(metric_id, "baseline " + baseline_judge)
        tool_value, tool_samples = tool_judge
        baseline_value, baseline_samples = baseline_judge
    minimum = metric["minimum_samples"]
    if min(tool_samples, baseline_samples) < minimum:
        return not_measured(metric_id, f"unique approved sample evidence does not meet minimum_samples={minimum}")
    threshold = compare(metric["success_threshold"], tool_value)
    comparison = compare(metric["comparison_contract"], tool_value, baseline_value, "minimum_margin")
    if threshold is None or comparison is None:
        return not_measured(metric_id, "metric threshold or comparison contract is invalid")
    adequacy = "meets_minimum" if min(tool_samples, baseline_samples) == minimum else "above_minimum"
    return {
        "metric_id": metric_id,
        "status": "measured",
        "tool": {"raw_value": tool_value, "sample_count": tool_samples, "sample_adequacy": adequacy},
        "baseline": {"raw_value": baseline_value, "sample_count": baseline_samples, "sample_adequacy": adequacy},
        "success_threshold_met": threshold,
        "comparison_met": comparison,
        "claim_component_met": threshold and comparison,
        "not_measured_reason": "",
    }


def numeric_sample_measure(metric, output):
    values = output.get(metric["per_sample_field"])
    expected_ids = set(output["sample_ids"])
    if not isinstance(values, dict) or set(values) != expected_ids:
        return f"{metric['per_sample_field']} must contain one value for every approved sample"
    if not all(finite_number(value) for value in values.values()):
        return f"{metric['per_sample_field']} values must be finite"
    return sum(values.values()) / len(values), len(values)


def blinded_judge_measure(metric, output):
    if metric["judge_category"].lower() in {"safety", "security", "leakage", "privacy"}:
        return "LLM Judge cannot independently measure safety, security, leakage, or privacy"
    results = output.get("judge_results")
    if not isinstance(results, list):
        return "judge_results must be a list"
    expected_ids = set(output["sample_ids"])
    scores = {}
    for item in results:
        if not isinstance(item, dict) or item.get("metric_id") != metric["id"]:
            continue
        string_fields = ("sample_id", "evidence", "judge_prompt", "model", "model_version")
        if not all(isinstance(item.get(key), str) and item[key] for key in string_fields):
            return "judge result provenance is incomplete"
        if item["sample_id"] not in expected_ids or item["sample_id"] in scores:
            return "judge result sample identity is invalid"
        if not finite_number(item.get("score")) or not 0 <= item["score"] <= 10:
            return "judge score must be finite and within 0..10"
        if item.get("blinded") is not True or item.get("randomized_order") is not True:
            return "judge results must be blinded and randomized"
        scores[item["sample_id"]] = item["score"]
    if set(scores) != expected_ids:
        return "judge results do not cover the approved dataset exactly once"
    return sum(scores.values()) / len(scores), len(scores)


def claim_status(metrics):
    outcomes = [metric["claim_component_met"] for metric in metrics]
    if not outcomes or any(value is None for value in outcomes):
        return "inconclusive"
    if all(outcomes):
        return "supported"
    if any(outcomes):
        return "partially_supported"
    return "not_supported"


def evaluate(task, tool_output, baseline_output, execution_receipt=None, current_source_revision=None):
    metrics_source = task.get("metrics", []) if isinstance(task, dict) else []
    try:
        CONTRACT.validate_task_contract(task)
    except CONTRACT.BenchmarkContractError as exc:
        reason = str(exc)
    else:
        if task["rubric_approved"] is not True:
            reason = "rubric_approved must be true"
        elif execution_receipt is None:
            reason = "matching runner-created full execution receipt is required"
        else:
            reason = CONTRACT.validate_execution_receipt(execution_receipt, task, tool_output, baseline_output)
            if reason is None and current_source_revision != task["final_plan_approval"]["source_revision"]:
                reason = "current source revision is missing or does not match the approved full-run evidence"
    if reason:
        metrics = [not_measured(metric.get("id", "unknown"), reason) for metric in metrics_source if isinstance(metric, dict)]
        return {"claim_status": "inconclusive", "metrics": metrics, "limitations": [reason]}
    metrics = [metric_result(metric, tool_output, baseline_output) for metric in task["metrics"]]
    return {"claim_status": claim_status(metrics), "metrics": metrics, "limitations": []}


def workbench_json(project_root, raw_path, label):
    root = Path(project_root).resolve()
    workbench = (root / "project_verification_workbench").resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    candidate = candidate.resolve()
    try:
        candidate.relative_to(workbench)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside project_verification_workbench") from exc
    if not candidate.is_file():
        raise ValueError(f"{label} is missing or not a regular file")
    return json.loads(candidate.read_text(encoding="utf-8"))


def verify_workbench_evidence(task_path, receipt_path, project_root, manifest_path):
    root = Path(project_root).resolve()
    task_file = Path(task_path)
    if not task_file.is_absolute():
        task_file = root / task_file
    if task_file.is_symlink() or not task_file.is_file() or root not in task_file.resolve().parents:
        raise ValueError("Benchmark task must be a regular file inside the project root")
    task = json.loads(task_file.read_text(encoding="utf-8"))
    receipt = workbench_json(root, receipt_path, "Execution receipt")
    current_source_revision = GATE.source_fingerprint(root)
    CONTRACT.validate_plan_authorization(task_file, root, manifest_path, GATE_PATH, current_source_revision)
    authorization = receipt.get("execution_authorization")
    if not isinstance(authorization, dict):
        raise ValueError("Execution receipt authorization is invalid")
    receipt_file = CONTRACT.project_regular_file(root, authorization.get("receipt_path"), "Execution authorization receipt")
    envelope_file = CONTRACT.project_regular_file(root, authorization.get("envelope_path"), "Execution authorization envelope")
    envelope = json.loads(envelope_file.read_text(encoding="utf-8"))
    CONTRACT.validate_execution_envelope(
        task_file, envelope_file,
        authorization.get("approved_limits", {}).get("max_calls"),
        authorization.get("approved_limits", {}).get("max_retries"),
        authorization.get("approved_limits", {}).get("timeout_seconds"),
    )
    command = [
        sys.executable, str(GATE_PATH), "check", "--manifest", str(manifest_path),
        "--receipt", str(receipt_file), "--envelope", str(envelope_file),
        "--source-revision", current_source_revision, "--project-root", str(root),
        "--stage", "stage4", "--decision-type", "benchmark_execution",
    ]
    for key in ("max_calls", "max_retries", "timeout_seconds"):
        command.extend(["--limit", f"{key}={authorization['approved_limits'][key]}"])
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        raise ValueError("Execution authorization is no longer current: " + completed.stdout.strip())
    gate_result = json.loads(completed.stdout)
    if gate_result.get("decision_id") != authorization.get("decision_id") or gate_result.get("decision_envelope_sha256") != authorization.get("decision_envelope_sha256"):
        raise ValueError("Execution receipt authorization does not match the current gate")
    tool = workbench_json(root, receipt["tool_output"]["path"], "Tool result")
    baseline = workbench_json(root, receipt["baseline_output"]["path"], "Baseline result")
    return task, tool, baseline, receipt, current_source_revision


def main(argv):
    if len(argv) != 5:
        print(f"Usage: {argv[0]} TASK_JSON EXECUTION_RECEIPT_JSON PROJECT_ROOT MANIFEST_JSON", file=sys.stderr)
        return 2
    try:
        task, tool, baseline, receipt, current_source_revision = verify_workbench_evidence(
            argv[1], argv[2], argv[3], argv[4]
        )
    except (ValueError, OSError, json.JSONDecodeError, CONTRACT.BenchmarkContractError, GATE.GateValidationError) as exc:
        print(f"Cannot verify current Benchmark evidence: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evaluate(task, tool, baseline, receipt, current_source_revision), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
