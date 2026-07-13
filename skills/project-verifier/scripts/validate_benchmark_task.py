#!/usr/bin/env python3
"""Validate and bind Benchmark task, approval, and execution evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


SHA256 = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
OPERATORS = {">=", "<=", ">", "<", "=="}
PROVENANCE = {"real", "existing_test", "user_confirmed", "synthetic_candidate"}
EXECUTION_MODES = {"plan_only", "pilot", "full"}
JUDGE_ALLOWED_CATEGORIES = {"quality", "helpfulness", "relevance", "style", "instruction_following"}
LIMIT_KEYS = {"max_calls", "max_retries", "timeout_seconds"}
TASK_FIELDS = {
    "schema_version",
    "task_id",
    "feature_id",
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
}


class BenchmarkContractError(ValueError):
    """Raised when a Benchmark artifact cannot support a trustworthy claim."""


def canonical_object_hash(payload):
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise BenchmarkContractError("artifact is not canonical JSON") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def proposal_sha256(task):
    if not isinstance(task, dict):
        raise BenchmarkContractError("task must be an object")
    proposal = json.loads(json.dumps(task))
    proposal.pop("final_plan_approval", None)
    return canonical_object_hash(proposal)


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def nonnegative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def require_exact_fields(payload, expected, label):
    if not isinstance(payload, dict):
        raise BenchmarkContractError(f"{label} must be an object")
    actual = set(payload)
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise BenchmarkContractError(f"{label} fields are invalid ({'; '.join(details)})")


def require_identifier(value, label):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise BenchmarkContractError(f"{label} is invalid")


def require_string_list(value, label, allow_empty=False):
    if not isinstance(value, list) or (not allow_empty and not value):
        raise BenchmarkContractError(f"{label} must be a non-empty list")
    if not all(isinstance(item, str) and item for item in value):
        raise BenchmarkContractError(f"{label} must contain non-empty strings")
    if len(set(value)) != len(value):
        raise BenchmarkContractError(f"{label} must not contain duplicates")


def require_sha256(value, label):
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise BenchmarkContractError(f"{label} must be a SHA-256 value")


def safe_workbench_reference(value, label):
    if not isinstance(value, str) or not value:
        raise BenchmarkContractError(f"{label} is invalid")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or path.parts[:2] != ("project_verification_workbench", "authorizations"):
        raise BenchmarkContractError(f"{label} must stay under project_verification_workbench/authorizations")
    return path.as_posix()


def validate_metric(metric, dataset_sample_count, execution_minimum):
    require_exact_fields(
        metric,
        {"id", "label", "measurement_method", "source_field", "per_sample_field", "judge_category", "success_threshold", "comparison_contract", "minimum_samples", "evidence_fields"},
        "Metric",
    )
    require_identifier(metric["id"], "Metric id")
    if not isinstance(metric["label"], str) or not metric["label"]:
        raise BenchmarkContractError("Metric label is invalid")
    if metric["measurement_method"] not in {"numeric_value", "llm_judge_score"}:
        raise BenchmarkContractError("Metric measurement_method is unsupported by the template")
    if not isinstance(metric["source_field"], str) or not metric["source_field"]:
        raise BenchmarkContractError("Metric source_field is invalid")
    if not isinstance(metric["per_sample_field"], str) or not metric["per_sample_field"]:
        raise BenchmarkContractError("Metric per_sample_field is invalid")
    if not isinstance(metric["judge_category"], str) or not metric["judge_category"]:
        raise BenchmarkContractError("Metric judge_category is invalid")
    require_exact_fields(metric["success_threshold"], {"operator", "value"}, "Metric success_threshold")
    if metric["success_threshold"]["operator"] not in OPERATORS or not finite_number(metric["success_threshold"]["value"]):
        raise BenchmarkContractError("Metric success_threshold is invalid")
    require_exact_fields(metric["comparison_contract"], {"operator", "minimum_margin"}, "Metric comparison_contract")
    if metric["comparison_contract"]["operator"] not in OPERATORS or not finite_number(metric["comparison_contract"]["minimum_margin"]):
        raise BenchmarkContractError("Metric comparison_contract is invalid")
    if metric["comparison_contract"]["minimum_margin"] < 0:
        raise BenchmarkContractError("Metric comparison_contract minimum_margin must be non-negative")
    if not positive_int(metric["minimum_samples"]):
        raise BenchmarkContractError("Metric minimum_samples must be a positive integer")
    if metric["minimum_samples"] > dataset_sample_count or metric["minimum_samples"] > execution_minimum:
        raise BenchmarkContractError("Metric minimum_samples exceeds approved unique dataset capacity")
    require_string_list(metric["evidence_fields"], "Metric evidence_fields")


def validate_task_contract(task):
    require_exact_fields(task, TASK_FIELDS, "Benchmark task")
    if task["schema_version"] != "3.0":
        raise BenchmarkContractError("Benchmark task schema_version must be 3.0")
    require_identifier(task["task_id"], "Benchmark task_id")
    require_identifier(task["feature_id"], "Benchmark feature_id")
    require_exact_fields(task["characteristic_source"], {"evidence_refs", "candidate_characteristic"}, "Characteristic source")
    require_string_list(task["characteristic_source"]["evidence_refs"], "Characteristic evidence_refs")
    if not isinstance(task["characteristic_source"]["candidate_characteristic"], str) or not task["characteristic_source"]["candidate_characteristic"]:
        raise BenchmarkContractError("Candidate characteristic is invalid")
    for field in ("user_selected_direction", "comparison_claim", "decision_use"):
        if not isinstance(task[field], str) or not task[field]:
            raise BenchmarkContractError(f"Benchmark {field} is invalid")
    require_string_list(task["user_path_ids"], "Benchmark user_path_ids")

    require_exact_fields(task["backend"], {"name", "version", "fallback_reason"}, "Backend")
    for field in ("name", "version"):
        if not isinstance(task["backend"][field], str) or not task["backend"][field]:
            raise BenchmarkContractError(f"Backend {field} is invalid")
    if task["backend"]["fallback_reason"] is not None and not isinstance(task["backend"]["fallback_reason"], str):
        raise BenchmarkContractError("Backend fallback_reason is invalid")
    require_exact_fields(task["baseline"], {"type", "identity", "equivalence_deviations"}, "Baseline")
    for field in ("type", "identity"):
        if not isinstance(task["baseline"][field], str) or not task["baseline"][field]:
            raise BenchmarkContractError(f"Baseline {field} is invalid")
    require_string_list(task["baseline"]["equivalence_deviations"], "Baseline equivalence_deviations", allow_empty=True)

    require_exact_fields(task["dataset"], {"dataset_id", "sha256", "samples"}, "Dataset")
    require_identifier(task["dataset"]["dataset_id"], "Dataset id")
    require_sha256(task["dataset"]["sha256"], "Dataset sha256")
    samples = task["dataset"]["samples"]
    if not isinstance(samples, list) or not samples:
        raise BenchmarkContractError("Dataset samples are required")
    sample_ids = []
    for sample in samples:
        require_exact_fields(sample, {"id", "provenance", "evidence_refs"}, "Dataset sample")
        require_identifier(sample["id"], "Dataset sample id")
        if sample["provenance"] not in PROVENANCE:
            raise BenchmarkContractError("Dataset sample provenance is invalid")
        require_string_list(sample["evidence_refs"], "Dataset sample evidence_refs")
        sample_ids.append(sample["id"])
    if len(set(sample_ids)) != len(sample_ids):
        raise BenchmarkContractError("Dataset sample ids must be unique")

    require_exact_fields(
        task["final_plan_approval"],
        {"decision_id", "proposal_sha256", "source_revision", "receipt_path", "envelope_path"},
        "Final plan approval",
    )
    approval = task["final_plan_approval"]
    require_identifier(approval["decision_id"], "Final plan approval decision_id")
    require_sha256(approval["proposal_sha256"], "Final plan approval proposal_sha256")
    if approval["proposal_sha256"] != proposal_sha256(task):
        raise BenchmarkContractError("Final plan approval proposal_sha256 does not match the task")
    if not isinstance(approval["source_revision"], str) or not approval["source_revision"]:
        raise BenchmarkContractError("Final plan approval source_revision is invalid")
    safe_workbench_reference(approval["receipt_path"], "Final plan approval receipt_path")
    safe_workbench_reference(approval["envelope_path"], "Final plan approval envelope_path")

    if not isinstance(task["rubric_approved"], bool):
        raise BenchmarkContractError("rubric_approved must be boolean")
    require_exact_fields(task["execution"], {"mode", "minimum_samples", "max_calls", "max_retries", "timeout_seconds"}, "Execution")
    execution = task["execution"]
    if execution["mode"] not in EXECUTION_MODES:
        raise BenchmarkContractError("Execution mode is invalid")
    if not positive_int(execution["minimum_samples"]):
        raise BenchmarkContractError("Execution minimum_samples must be a positive integer")
    if execution["minimum_samples"] > len(samples):
        raise BenchmarkContractError("Execution minimum_samples exceeds unique dataset samples")
    for key in LIMIT_KEYS:
        if not nonnegative_int(execution[key]):
            raise BenchmarkContractError(f"Execution {key} must be a non-negative integer")
    if execution["mode"] == "plan_only":
        if any(execution[key] != 0 for key in LIMIT_KEYS):
            raise BenchmarkContractError("plan_only execution must not reserve runtime limits")
    elif execution["max_calls"] < 1 or execution["timeout_seconds"] < 1:
        raise BenchmarkContractError("pilot/full execution requires positive max_calls and timeout_seconds")

    metrics = task["metrics"]
    if not isinstance(metrics, list) or not metrics:
        raise BenchmarkContractError("Benchmark metrics are required")
    metric_ids = []
    for metric in metrics:
        validate_metric(metric, len(samples), execution["minimum_samples"])
        if metric["measurement_method"] == "llm_judge_score" and metric["judge_category"] not in JUDGE_ALLOWED_CATEGORIES:
            raise BenchmarkContractError("LLM Judge category is not allowed as a standalone Benchmark metric")
        metric_ids.append(metric["id"])
    if len(set(metric_ids)) != len(metric_ids):
        raise BenchmarkContractError("Metric ids must be unique")
    return task


def load_json(path, label):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkContractError(f"{label} cannot be read as JSON") from exc


def project_regular_file(project_root, relative_path, label):
    root = Path(project_root).resolve()
    normalized = safe_workbench_reference(relative_path, label)
    candidate = root
    for part in PurePosixPath(normalized).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise BenchmarkContractError(f"{label} must not be a symlink")
    if not candidate.is_file():
        raise BenchmarkContractError(f"{label} is missing or not a regular file")
    return candidate


def validate_envelope_binding(envelope, task, decision_type):
    if not isinstance(envelope, dict):
        raise BenchmarkContractError("Decision envelope must be an object")
    if envelope.get("stage") != "stage4" or envelope.get("decision_type") != decision_type:
        raise BenchmarkContractError("Decision envelope does not match the Stage 4 operation")
    scope = envelope.get("scope")
    interpretation = envelope.get("interpretation")
    if not isinstance(scope, dict) or not isinstance(interpretation, dict):
        raise BenchmarkContractError("Decision envelope binding is incomplete")
    targets = scope.get("targets")
    if not isinstance(targets, list):
        raise BenchmarkContractError("Decision envelope targets are invalid")
    required_targets = {f"benchmark_task:{task['task_id']}", f"proposal_sha256:{proposal_sha256(task)}"}
    if not required_targets <= set(targets):
        raise BenchmarkContractError("Decision envelope does not bind this Benchmark proposal")
    if set(scope.get("path_ids", [])) != set(task["user_path_ids"]):
        raise BenchmarkContractError("Decision envelope path_ids do not match the Benchmark task")
    expected_interpretation = {
        "claim": task["comparison_claim"],
        "baseline": task["baseline"]["identity"],
        "dataset_id": task["dataset"]["dataset_id"],
        "metric_ids": [metric["id"] for metric in task["metrics"]],
    }
    if interpretation != expected_interpretation:
        raise BenchmarkContractError("Decision envelope interpretation does not match the Benchmark task")


def limit_arguments(execution):
    return [f"{key}={execution[key]}" for key in sorted(LIMIT_KEYS)]


def validate_plan_authorization(task_path, project_root, manifest_path, gate_validator, source_revision):
    task = validate_task_contract(load_json(task_path, "Benchmark task"))
    approval = task["final_plan_approval"]
    receipt_path = project_regular_file(project_root, approval["receipt_path"], "Final plan approval receipt")
    envelope_path = project_regular_file(project_root, approval["envelope_path"], "Final plan approval envelope")
    envelope = load_json(envelope_path, "Final plan approval envelope")
    validate_envelope_binding(envelope, task, "benchmark_plan")
    command = [
        sys.executable,
        str(gate_validator),
        "check",
        "--manifest", str(manifest_path),
        "--receipt", str(receipt_path),
        "--envelope", str(envelope_path),
        "--source-revision", source_revision,
        "--project-root", str(project_root),
        "--stage", "stage4",
        "--decision-type", "benchmark_plan",
    ]
    for value in limit_arguments(task["execution"]):
        command.extend(["--limit", value])
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        raise BenchmarkContractError("Final plan approval failed: " + completed.stdout.strip())
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BenchmarkContractError("Final plan approval validator returned invalid JSON") from exc
    if result.get("decision_id") != approval["decision_id"] or result.get("approved_source_revision") != approval["source_revision"]:
        raise BenchmarkContractError("Final plan approval receipt does not match the Benchmark task")
    return {"task_id": task["task_id"], "plan_approval": result, "proposal_sha256": proposal_sha256(task)}


def validate_execution_envelope(task_path, envelope_path, max_calls, max_retries, timeout_seconds):
    task = validate_task_contract(load_json(task_path, "Benchmark task"))
    if task["execution"]["mode"] == "plan_only":
        raise BenchmarkContractError("plan_only task cannot execute")
    if task["rubric_approved"] is not True:
        raise BenchmarkContractError("rubric_approved must be true before pilot or full execution")
    requested = {"max_calls": max_calls, "max_retries": max_retries, "timeout_seconds": timeout_seconds}
    for key, value in requested.items():
        if not nonnegative_int(value) or value > task["execution"][key]:
            raise BenchmarkContractError(f"Execution {key} is outside the approved task limit")
    if requested["max_calls"] < 1 or requested["timeout_seconds"] < 1:
        raise BenchmarkContractError("Execution limits cannot be zero")
    envelope = load_json(envelope_path, "Execution authorization envelope")
    validate_envelope_binding(envelope, task, "benchmark_execution")
    return {"task_id": task["task_id"], "requested_limits": requested}


def validate_runner_output(output, task, role):
    if not isinstance(output, dict):
        raise BenchmarkContractError(f"{role} output must be an object")
    if output.get("task_id") != task["task_id"] or output.get("runner_type") != role:
        raise BenchmarkContractError(f"{role} output identity is invalid")
    if output.get("status") != "completed" or output.get("execution_mode") != "full" or output.get("exit_code") != 0:
        raise BenchmarkContractError(f"{role} output is not a completed full successful run")
    sample_ids = output.get("sample_ids")
    require_string_list(sample_ids, f"{role} output sample_ids")
    expected_ids = {sample["id"] for sample in task["dataset"]["samples"]}
    if set(sample_ids) != expected_ids:
        raise BenchmarkContractError(f"{role} output sample_ids do not match the approved dataset")
    evidence = output.get("sample_evidence")
    if not isinstance(evidence, dict) or set(evidence) != expected_ids:
        raise BenchmarkContractError(f"{role} output sample_evidence does not cover the approved dataset")
    for sample_id, references in evidence.items():
        require_string_list(references, f"{role} output sample_evidence[{sample_id}]")


def validate_execution_receipt(receipt, task, tool_output, baseline_output):
    try:
        validate_task_contract(task)
        require_exact_fields(
            receipt,
            {
                "schema_version", "receipt_type", "receipt_id", "task_id", "proposal_sha256", "dataset_sha256",
                "execution_mode", "wrapper_exit_code", "duration_seconds", "tool_output", "baseline_output",
                "backend", "baseline", "log_path", "plan_approval", "execution_authorization", "telemetry",
            },
            "Execution receipt",
        )
        if receipt["schema_version"] != "1.0" or receipt["receipt_type"] != "stage4_benchmark_execution":
            raise BenchmarkContractError("Execution receipt type is invalid")
        require_identifier(receipt["receipt_id"], "Execution receipt_id")
        if receipt["task_id"] != task["task_id"] or receipt["proposal_sha256"] != proposal_sha256(task):
            raise BenchmarkContractError("Execution receipt task identity is invalid")
        if receipt["dataset_sha256"] != task["dataset"]["sha256"]:
            raise BenchmarkContractError("Execution receipt dataset identity is invalid")
        if receipt["execution_mode"] != "full" or receipt["wrapper_exit_code"] != 0:
            raise BenchmarkContractError("Execution receipt is not a successful full run")
        if not finite_number(receipt["duration_seconds"]) or receipt["duration_seconds"] < 0:
            raise BenchmarkContractError("Execution receipt duration is invalid")
        if not isinstance(receipt["log_path"], str) or not receipt["log_path"].startswith("project_verification_workbench/"):
            raise BenchmarkContractError("Execution receipt log_path is invalid")
        if receipt["backend"] != task["backend"] or receipt["baseline"] != task["baseline"]:
            raise BenchmarkContractError("Execution receipt backend or Baseline identity is invalid")
        require_exact_fields(receipt["plan_approval"], {"decision_id", "proposal_sha256", "source_revision"}, "Execution receipt plan_approval")
        if receipt["plan_approval"] != {
            "decision_id": task["final_plan_approval"]["decision_id"],
            "proposal_sha256": task["final_plan_approval"]["proposal_sha256"],
            "source_revision": task["final_plan_approval"]["source_revision"],
        }:
            raise BenchmarkContractError("Execution receipt plan approval is invalid")
        require_exact_fields(
            receipt["execution_authorization"],
            {"decision_id", "decision_envelope_sha256", "source_revision", "approved_limits", "receipt_path", "envelope_path"},
            "Execution receipt execution_authorization",
        )
        authorization = receipt["execution_authorization"]
        require_identifier(authorization["decision_id"], "Execution authorization decision_id")
        require_sha256(authorization["decision_envelope_sha256"], "Execution authorization envelope hash")
        if authorization["source_revision"] != task["final_plan_approval"]["source_revision"]:
            raise BenchmarkContractError("Execution authorization source revision is stale")
        safe_workbench_reference(authorization["receipt_path"], "Execution authorization receipt_path")
        safe_workbench_reference(authorization["envelope_path"], "Execution authorization envelope_path")
        if not isinstance(authorization["approved_limits"], dict) or set(authorization["approved_limits"]) != LIMIT_KEYS:
            raise BenchmarkContractError("Execution authorization limits are invalid")
        for key, value in authorization["approved_limits"].items():
            if not nonnegative_int(value) or value > task["execution"][key]:
                raise BenchmarkContractError("Execution authorization exceeds approved task limits")
        require_exact_fields(receipt["telemetry"], {"status", "actual_calls", "actual_retries", "side_effects"}, "Execution receipt telemetry")
        telemetry = receipt["telemetry"]
        if telemetry["status"] != "valid":
            raise BenchmarkContractError("Execution receipt telemetry is missing or invalid")
        for key, limit in (("actual_calls", "max_calls"), ("actual_retries", "max_retries")):
            if not nonnegative_int(telemetry[key]) or telemetry[key] > authorization["approved_limits"][limit]:
                raise BenchmarkContractError("Execution receipt telemetry exceeds approved limits")
        if not isinstance(telemetry["side_effects"], list):
            raise BenchmarkContractError("Execution receipt side_effects are invalid")
        validate_runner_output(tool_output, task, "tool")
        validate_runner_output(baseline_output, task, "baseline")
        for role, output in (("tool", tool_output), ("baseline", baseline_output)):
            artifact = receipt[f"{role}_output"]
            require_exact_fields(artifact, {"runner_type", "path", "sha256"}, f"Execution receipt {role}_output")
            if artifact["runner_type"] != role or not isinstance(artifact["path"], str) or not artifact["path"]:
                raise BenchmarkContractError(f"Execution receipt {role}_output identity is invalid")
            require_sha256(artifact["sha256"], f"Execution receipt {role}_output hash")
            if artifact["sha256"] != canonical_object_hash(output):
                raise BenchmarkContractError(f"Execution receipt {role}_output hash does not match the supplied output")
    except BenchmarkContractError as exc:
        return str(exc)
    return None


def workbench_output_path(project_root, raw_path):
    root = Path(project_root).resolve()
    workbench = root / "project_verification_workbench"
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        raise BenchmarkContractError("Execution receipt output must not be a symlink")
    candidate = candidate.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise BenchmarkContractError("Execution receipt output must stay inside the project root") from exc
    if relative.parts[:1] != ("project_verification_workbench",):
        raise BenchmarkContractError("Execution receipt output must stay inside project_verification_workbench")
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise BenchmarkContractError("Execution receipt output must not use symlinks")
    if candidate.exists() or candidate.is_symlink():
        raise BenchmarkContractError("Runner-owned execution receipt already exists")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate, relative.as_posix(), workbench


def existing_workbench_path(project_root, raw_path, label):
    root = Path(project_root).resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        raise BenchmarkContractError(f"{label} must not be a symlink")
    candidate = candidate.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise BenchmarkContractError(f"{label} must stay inside the project root") from exc
    if relative.parts[:1] != ("project_verification_workbench",) or candidate.is_symlink() or not candidate.is_file():
        raise BenchmarkContractError(f"{label} must be a regular file in project_verification_workbench")
    return relative.as_posix()


def read_result_artifact(project_root, raw_path, role):
    root = Path(project_root).resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        return None, {"runner_type": role, "path": "unsafe", "sha256": ""}
    candidate = candidate.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise BenchmarkContractError(f"{role} result must stay inside the project root") from exc
    if relative.parts[:1] != ("project_verification_workbench",) or candidate.is_symlink() or not candidate.is_file():
        return None, {"runner_type": role, "path": relative.as_posix(), "sha256": ""}
    payload = load_json(candidate, f"{role} result")
    return payload, {"runner_type": role, "path": relative.as_posix(), "sha256": canonical_object_hash(payload)}


def telemetry_payload(project_root, raw_path):
    root = Path(project_root).resolve()
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    if not path.is_file() or path.is_symlink():
        return {"status": "missing", "actual_calls": None, "actual_retries": None, "side_effects": None}
    try:
        payload = load_json(path, "Benchmark telemetry")
        require_exact_fields(payload, {"actual_calls", "actual_retries", "side_effects"}, "Benchmark telemetry")
        if not nonnegative_int(payload["actual_calls"]) or not nonnegative_int(payload["actual_retries"]) or not isinstance(payload["side_effects"], list):
            raise BenchmarkContractError("Benchmark telemetry is invalid")
    except BenchmarkContractError:
        return {"status": "invalid", "actual_calls": None, "actual_retries": None, "side_effects": None}
    return {"status": "valid", **payload}


def write_execution_receipt(args):
    task = validate_task_contract(load_json(args.task, "Benchmark task"))
    if args.mode not in {"pilot", "full"} or task["execution"]["mode"] == "plan_only":
        raise BenchmarkContractError("Benchmark task is not approved for runtime execution")
    authorization = json.loads(args.execution_authorization)
    require_exact_fields(
        authorization,
        {"approved", "decision_id", "decision_envelope_sha256", "approved_source_revision", "current_source_revision", "approved_limits", "source_policy"},
        "Execution authorization result",
    )
    if authorization["approved"] is not True:
        raise BenchmarkContractError("Execution authorization was not approved")
    authorization_receipt_path = existing_workbench_path(
        args.project_root, args.authorization_receipt, "Execution authorization receipt"
    )
    authorization_envelope_path = existing_workbench_path(
        args.project_root, args.authorization_envelope, "Execution authorization envelope"
    )
    safe_workbench_reference(authorization_receipt_path, "Execution authorization receipt_path")
    safe_workbench_reference(authorization_envelope_path, "Execution authorization envelope_path")
    output_path, receipt_relative_path, _ = workbench_output_path(args.project_root, args.output)
    log_relative_path = existing_workbench_path(args.project_root, args.log_path, "Execution log")
    tool_output, tool_artifact = read_result_artifact(args.project_root, args.tool_output, "tool")
    baseline_output, baseline_artifact = read_result_artifact(args.project_root, args.baseline_output, "baseline")
    telemetry = telemetry_payload(args.project_root, args.telemetry)
    receipt = {
        "schema_version": "1.0",
        "receipt_type": "stage4_benchmark_execution",
        "receipt_id": "receipt-" + os.urandom(12).hex(),
        "task_id": task["task_id"],
        "proposal_sha256": proposal_sha256(task),
        "dataset_sha256": task["dataset"]["sha256"],
        "execution_mode": args.mode,
        "wrapper_exit_code": args.exit_code,
        "duration_seconds": args.duration_seconds,
        "tool_output": tool_artifact,
        "baseline_output": baseline_artifact,
        "backend": task["backend"],
        "baseline": task["baseline"],
        "log_path": log_relative_path,
        "plan_approval": {
            "decision_id": task["final_plan_approval"]["decision_id"],
            "proposal_sha256": task["final_plan_approval"]["proposal_sha256"],
            "source_revision": task["final_plan_approval"]["source_revision"],
        },
        "execution_authorization": {
            "decision_id": authorization["decision_id"],
            "decision_envelope_sha256": authorization["decision_envelope_sha256"],
            "source_revision": authorization["current_source_revision"],
            "approved_limits": authorization["approved_limits"],
            "receipt_path": authorization_receipt_path,
            "envelope_path": authorization_envelope_path,
        },
        "telemetry": telemetry,
    }
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return {"receipt_path": receipt_relative_path, "receipt": receipt, "tool_output_present": tool_output is not None, "baseline_output_present": baseline_output is not None}


def build_parser():
    parser = argparse.ArgumentParser(description="Validate Project Verifier Benchmark contracts")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate one task JSON without execution")
    validate.add_argument("--task", required=True)
    plan = commands.add_parser("validate-plan", help="Validate the approved final Benchmark plan")
    plan.add_argument("--task", required=True)
    plan.add_argument("--project-root", required=True)
    plan.add_argument("--manifest", required=True)
    plan.add_argument("--gate-validator", required=True)
    plan.add_argument("--source-revision", required=True)
    execution = commands.add_parser("validate-execution-envelope", help="Bind execution authorization to a task")
    execution.add_argument("--task", required=True)
    execution.add_argument("--envelope", required=True)
    execution.add_argument("--max-calls", type=int, required=True)
    execution.add_argument("--max-retries", type=int, required=True)
    execution.add_argument("--timeout-seconds", type=int, required=True)
    receipt = commands.add_parser("write-receipt", help="Write a runner-owned execution receipt")
    receipt.add_argument("--task", required=True)
    receipt.add_argument("--project-root", required=True)
    receipt.add_argument("--mode", choices=("pilot", "full"), required=True)
    receipt.add_argument("--exit-code", type=int, required=True)
    receipt.add_argument("--duration-seconds", type=float, required=True)
    receipt.add_argument("--tool-output", required=True)
    receipt.add_argument("--baseline-output", required=True)
    receipt.add_argument("--telemetry", required=True)
    receipt.add_argument("--log-path", required=True)
    receipt.add_argument("--execution-authorization", required=True)
    receipt.add_argument("--authorization-receipt", required=True)
    receipt.add_argument("--authorization-envelope", required=True)
    receipt.add_argument("--output", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            task = validate_task_contract(load_json(args.task, "Benchmark task"))
            result = {"task_id": task["task_id"], "proposal_sha256": proposal_sha256(task)}
        elif args.command == "validate-plan":
            result = validate_plan_authorization(args.task, args.project_root, args.manifest, args.gate_validator, args.source_revision)
        elif args.command == "validate-execution-envelope":
            result = validate_execution_envelope(args.task, args.envelope, args.max_calls, args.max_retries, args.timeout_seconds)
        elif args.command == "write-receipt":
            result = write_execution_receipt(args)
        else:
            raise BenchmarkContractError("Unsupported command")
    except (BenchmarkContractError, OSError, json.JSONDecodeError) as exc:
        print(f"Benchmark contract validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
