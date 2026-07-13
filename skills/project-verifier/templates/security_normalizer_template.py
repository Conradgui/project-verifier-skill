#!/usr/bin/env python3
"""Normalize project bridge findings without treating scanner output as a security conclusion."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import subprocess
import sys
from pathlib import Path


SEVERITIES = {"unknown", "info", "low", "medium", "high", "critical"}
CONFIDENCES = {"unknown", "low", "medium", "high"}


def required_string(value, field):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def location_key(location):
    if not isinstance(location, dict):
        raise ValueError("source_location must be an object")
    allowed_fields = {"path", "line", "column", "end_line", "end_column"}
    if set(location) - allowed_fields:
        raise ValueError("source_location contains unsupported fields")
    normalized = {"path": required_string(location.get("path"), "source_location.path")}
    for field in ("line", "column", "end_line", "end_column"):
        value = location.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
            raise ValueError(f"source_location.{field} must be a positive integer when present")
        if value is not None:
            normalized[field] = value
    if "line" in normalized and "end_line" in normalized and normalized["end_line"] < normalized["line"]:
        raise ValueError("source_location.end_line must not precede source_location.line")
    return normalized


def stable_id(category, rule_id, source_location):
    del category, rule_id, source_location
    return "SEC-" + secrets.token_hex(16)


def opaque_reference(prefix, value):
    del value
    return prefix + "-" + secrets.token_hex(16)


def opaque_source_location(source_location):
    reference = {"source_ref": opaque_reference("SRC", source_location)}
    for field in ("line", "column", "end_line", "end_column"):
        if field in source_location:
            reference[field] = source_location[field]
    return reference


def normalize_finding(finding, tool):
    if not isinstance(finding, dict):
        raise ValueError("finding must be an object")
    category = required_string(finding.get("category"), "category")
    rule_id = required_string(finding.get("rule_id"), "rule_id")
    source_location = location_key(finding.get("source_location"))
    severity = finding.get("severity", "unknown")
    confidence = finding.get("confidence", "unknown")
    if severity not in SEVERITIES:
        raise ValueError("severity is invalid")
    if confidence not in CONFIDENCES:
        raise ValueError("confidence is invalid")
    raw_evidence = finding.get("evidence", {})
    if not isinstance(raw_evidence, (dict, list, str, int, float, bool, type(None))):
        raise ValueError("evidence must be JSON-compatible")
    finding_id = stable_id(category, rule_id, source_location)
    recommended_action = finding.get("recommended_action")
    verification_method = finding.get("verification_method")
    limitations = finding.get("limitations", [])
    if recommended_action is not None and not isinstance(recommended_action, str):
        raise ValueError("recommended_action must be a string or null")
    if verification_method is not None and not isinstance(verification_method, str):
        raise ValueError("verification_method must be a string or null")
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        raise ValueError("limitations must be a list of strings")
    affected_user_path = finding.get("affected_user_path")
    if affected_user_path is not None and not isinstance(affected_user_path, str):
        raise ValueError("affected_user_path must be a string or null")
    raw_preconditions = finding.get("exploit_preconditions", [])
    if not isinstance(raw_preconditions, list):
        raise ValueError("exploit_preconditions must be a list")
    return {
        "finding_id": finding_id,
        "category_ref": opaque_reference("CAT", category),
        "rule_ref": opaque_reference("RULE", rule_id),
        "severity": severity,
        "confidence": confidence,
        "triage_status": "needs_review",
        "source_location": opaque_source_location(source_location),
        "evidence_ref": opaque_reference("EVD", raw_evidence),
        "has_evidence": bool(raw_evidence),
        "exploit_preconditions_ref": opaque_reference("PRE", raw_preconditions),
        "tool_ref": opaque_reference("TOOL", tool),
        "has_recommended_action": recommended_action is not None,
        "has_verification_method": verification_method is not None,
        "tool_limitations_count": len(limitations),
    }


def normalize(payload, executed_scope=None):
    """Validate a bridge payload, preserve redacted raw evidence, and avoid inferred conclusions."""
    if not isinstance(payload, dict) or set(payload) != {"tool", "findings"}:
        raise ValueError("adapter payload must contain exactly tool and findings")
    tool = payload["tool"]
    if not isinstance(tool, dict) or set(tool) != {"name", "version"}:
        raise ValueError("tool must contain exactly name and version")
    normalized_tool = {"name": required_string(tool["name"], "tool.name"), "version": required_string(tool["version"], "tool.version")}
    if not isinstance(payload["findings"], list):
        raise ValueError("findings must be a list")

    findings = []
    seen = set()
    duplicates_removed = 0
    for raw in payload["findings"]:
        if not isinstance(raw, dict):
            raise ValueError("finding must be an object")
        dedup_identity = (
            required_string(raw.get("category"), "category"),
            required_string(raw.get("rule_id"), "rule_id"),
            json.dumps(location_key(raw.get("source_location")), sort_keys=True, separators=(",", ":")),
        )
        finding = normalize_finding(raw, normalized_tool)
        if dedup_identity in seen:
            duplicates_removed += 1
            continue
        seen.add(dedup_identity)
        findings.append(finding)

    if executed_scope is None:
        raise ValueError("executed_scope is required")
    scope = list(executed_scope)
    if not scope or not all(isinstance(item, str) and item for item in scope):
        raise ValueError("executed_scope must contain non-empty strings")
    limitations = [
        "Findings are adapter evidence and require project-context triage; exploitability is not inferred.",
        "Only exact category, rule identity, and source-location duplicates were collapsed.",
    ]
    if not findings:
        limitations.append("No issue was found in the completed authorized task scope.")
    return {
        "status": "findings_normalized" if findings else "no_issue_found_in_executed_scope",
        "tools": [{"tool_ref": opaque_reference("TOOL", normalized_tool)}],
        "findings": findings,
        "deduplication": {"duplicates_removed": duplicates_removed, "method": "exact_category_rule_location"},
        "limitations": limitations,
        "raw_evidence_ref": opaque_reference("RAW", payload),
    }


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_object_hash(payload):
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"authorization envelope cannot be canonicalized: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def current_source_revision(project_root):
    validator = Path(__file__).resolve().parent.parent / "scripts" / "validate_gate.py"
    if validator.is_symlink() or not validator.is_file():
        raise ValueError("bundled gate validator is unavailable")
    root = Path(project_root).resolve()
    try:
        validator.resolve().relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("bundled gate validator must stay outside the target project")
    completed = subprocess.run(
        ["python3", str(validator), "fingerprint", "--root", str(root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError("cannot fingerprint the current project source")
    return required_string(completed.stdout.strip(), "current source revision")


def workbench_path(project_root, raw_path, label, must_exist):
    root = Path(project_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("project root must be a regular directory")
    root = root.resolve()
    workbench = root / "project_verification_workbench"
    if workbench.is_symlink() or not workbench.is_dir():
        raise ValueError("project workbench must be a regular directory")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(workbench.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside project_verification_workbench") from exc
    if must_exist:
        if not resolved.is_file():
            raise ValueError(f"{label} must be an existing regular file")
    else:
        if candidate.exists() or candidate.is_symlink():
            raise ValueError(f"{label} must be a new non-symlink file")
        if candidate.parent.is_symlink() or not candidate.parent.is_dir():
            raise ValueError(f"{label} parent must be an existing regular directory")
    return resolved


def write_scopes(project_root, payload, field_path, label):
    value = payload
    for field in field_path:
        if not isinstance(value, dict):
            raise ValueError(f"{label} is malformed")
        value = value.get(field)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label} write scope is invalid")
    root = Path(project_root).resolve()
    normalized = []
    for raw_scope in value:
        candidate = Path(raw_scope)
        if candidate.is_absolute():
            raise ValueError(f"{label} write scope must be project-relative")
        resolved = (root / candidate).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"{label} write scope must stay inside the project") from exc
        normalized.append(resolved)
    return normalized


def covered_by_every_scope(path, scope_sets):
    for scopes in scope_sets:
        if not any(_is_within(path, scope) for scope in scopes):
            return False
    return True


def _is_within(path, scope):
    try:
        path.relative_to(scope)
        return True
    except ValueError:
        return False


def validate_normalization_authorization(project_root, manifest, envelope, authorization, source_revision, output_path):
    if not isinstance(manifest, dict) or not isinstance(envelope, dict) or not isinstance(authorization, dict):
        raise ValueError("current manifest, envelope, and execution authorization are required")
    if envelope.get("stage") != "stage3" or envelope.get("decision_type") != "security_execution":
        raise ValueError("authorization envelope is not a Stage 3 security decision")
    decision_id = required_string(authorization.get("decision_id"), "execution_authorization.decision_id")
    envelope_hash = canonical_object_hash(envelope)
    if required_string(authorization.get("decision_envelope_sha256"), "execution_authorization.decision_envelope_sha256") != envelope_hash:
        raise ValueError("execution authorization does not match the current envelope")
    if required_string(authorization.get("current_source_revision"), "execution_authorization.current_source_revision") != source_revision:
        raise ValueError("execution authorization source revision is no longer current")
    manifest_revision = manifest.get("source_revision", {}).get("revision")
    if required_string(manifest_revision, "manifest source revision") != source_revision:
        raise ValueError("manifest source revision is no longer current")
    decisions = manifest.get("decisions")
    matches = [item for item in decisions if isinstance(item, dict) and item.get("decision_id") == decision_id] if isinstance(decisions, list) else []
    if len(matches) != 1:
        raise ValueError("execution authorization is not uniquely recorded in the current manifest")
    receipt = matches[0]
    if receipt.get("user_choice") != "approved" or receipt.get("invalidated_at") is not None:
        raise ValueError("execution authorization is not currently approved")
    if required_string(receipt.get("source_revision"), "manifest authorization source_revision") != source_revision:
        raise ValueError("manifest authorization source revision is no longer current")
    if required_string(receipt.get("decision_envelope_sha256"), "manifest authorization decision_envelope_sha256") != envelope_hash:
        raise ValueError("manifest authorization does not match the current envelope")
    manifest_scopes = write_scopes(project_root, manifest, ("permissions", "write_scope"), "manifest")
    envelope_scopes = write_scopes(project_root, envelope, ("scope", "write_scope"), "authorization")
    if not covered_by_every_scope(output_path, (manifest_scopes, envelope_scopes)):
        raise ValueError("normalized output is outside the current authorized write scope")


def execution_scope_from_results(payload, requested_task_id, raw_input_path, source_revision):
    if not isinstance(payload, dict):
        raise ValueError("stage3 results must be an object")
    if payload.get("schema_version") != "3.0" or payload.get("phase_status") != "completed":
        raise ValueError("stage3 results are not a completed result")
    if payload.get("result_outcome") != "pass":
        raise ValueError("stage3 results are not complete enough for normalization")
    if required_string(payload.get("source_revision"), "stage3 results source_revision") != source_revision:
        raise ValueError("stage3 results source revision is no longer current")
    authorization = payload.get("execution_authorization")
    if not isinstance(authorization, dict):
        raise ValueError("stage3 results lack execution authorization")
    decision_id = required_string(authorization.get("decision_id"), "execution_authorization.decision_id")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("stage3 results lack executed tasks")
    requested_task_id = required_string(requested_task_id, "requested task_id")
    raw_input_path = Path(raw_input_path).resolve()
    matched = None
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("stage3 result task must be an object")
        task_id = required_string(task.get("task_id"), "stage3 result task_id")
        if required_string(task.get("decision_id"), "stage3 result decision_id") != decision_id:
            raise ValueError("stage3 task decision_id does not match execution authorization")
        if task.get("exit_code") != 0 or task.get("raw_output_status") != "present":
            raise ValueError("stage3 results include incomplete task evidence")
        raw_output_path = Path(required_string(task.get("raw_output_path"), "stage3 result raw_output_path")).resolve()
        if task_id == requested_task_id:
            if matched is not None:
                raise ValueError("stage3 results contain duplicate task IDs")
            raw_output_sha256 = required_string(task.get("raw_output_sha256"), "stage3 result raw_output_sha256")
            if not re.fullmatch(r"[0-9a-f]{64}", raw_output_sha256):
                raise ValueError("stage3 result raw_output_sha256 is invalid")
            matched = (task_id, raw_output_path, raw_output_sha256)
    task_ids = [required_string(task.get("task_id"), "stage3 result task_id") for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("stage3 results contain duplicate task IDs")
    if matched is None:
        raise ValueError("requested task ID is not present in completed stage3 results")
    task_id, raw_output_path, raw_output_sha256 = matched
    if raw_output_path != raw_input_path:
        raise ValueError("raw input path does not match the completed task result")
    if sha256_file(raw_input_path) != raw_output_sha256:
        raise ValueError("raw input SHA256 does not match the completed task result")
    return [task_id], decision_id, raw_output_path, raw_output_sha256


def main(argv):
    if len(argv) != 8:
        print(f"Usage: {argv[0]} INPUT_JSON OUTPUT_JSON STAGE3_RESULTS_JSON TASK_ID PROJECT_ROOT MANIFEST_JSON ENVELOPE_JSON", file=sys.stderr)
        return 2
    project_root = Path(argv[5]).resolve()
    input_path = workbench_path(project_root, argv[1], "raw input", must_exist=True)
    output_path = workbench_path(project_root, argv[2], "normalized output", must_exist=False)
    results_path = workbench_path(project_root, argv[3], "stage3 results", must_exist=True)
    manifest_path = workbench_path(project_root, argv[6], "manifest", must_exist=True)
    envelope_path = workbench_path(project_root, argv[7], "authorization envelope", must_exist=True)
    source_revision = current_source_revision(project_root)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    executed_scope, decision_id, raw_output_path, raw_output_sha256 = execution_scope_from_results(
        results, argv[4], input_path, source_revision
    )
    validate_normalization_authorization(
        project_root,
        json.loads(manifest_path.read_text(encoding="utf-8")),
        json.loads(envelope_path.read_text(encoding="utf-8")),
        results["execution_authorization"],
        source_revision,
        output_path,
    )
    normalized = normalize(payload, executed_scope=executed_scope)
    normalized["execution_evidence"] = {
        "decision_ref": opaque_reference("DEC", decision_id),
        "task_refs": [opaque_reference("TASK", task_id) for task_id in executed_scope],
        "raw_evidence_ref": opaque_reference("RAW", raw_output_sha256),
        "source_revision_ref": opaque_reference("SRCREV", source_revision),
    }
    with output_path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(normalized, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
