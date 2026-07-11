#!/usr/bin/env python3
"""Validate V3 decision-envelope authorization with standard-library Python."""

import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path


PHASE_STATUSES = {"pending", "in_progress", "completed", "blocked", "skipped", "not_applicable", "failed"}
RESULT_OUTCOMES = {"not_run", "pass", "fail", "partial", "inconclusive"}
EXECUTION_SCOPES = {"none", "plan_only", "pilot", "full"}
CLAIM_ELIGIBILITY = {"none", "pilot", "full"}
GATE_STATES = {"not_required", "pending", "approved", "blocked"}
STAGES = {"stage1", "stage2", "stage3", "stage4"}
RECEIPT_FIELDS = {
    "decision_id",
    "stage",
    "decision_type",
    "decision_envelope_sha256",
    "source_revision",
    "user_choice",
    "approved_limits",
    "approved_at",
    "invalidated_at",
}
ENVELOPE_FIELDS = {
    "schema_version",
    "stage",
    "decision_type",
    "source_policy",
    "scope",
    "interpretation",
    "limits",
}
MANIFEST_FIELDS = {
    "schema_version",
    "source_revision",
    "user_intent",
    "permissions",
    "stages",
    "source_history",
    "project_profile",
    "decisions",
}
SOURCE_HISTORY_FIELDS = {
    "base_revision",
    "current_revision",
    "affected_artifacts_stale",
    "recorded_at",
}
COMMIT_REVISION = re.compile(r"^git:([0-9a-f]{40})$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class GateValidationError(ValueError):
    pass


def canonical_object_hash(payload):
    """Return the SHA-256 of canonical JSON, independent of formatting."""
    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GateValidationError(f"Decision envelope is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def requested_limit_is_within(approved, requested):
    """Allow numeric maxima to decrease; all other material values are exact."""
    if isinstance(approved, bool) or isinstance(requested, bool):
        return approved is requested
    if isinstance(approved, (int, float)) and isinstance(requested, (int, float)):
        return requested <= approved
    return requested == approved


def load_object(path, label):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise GateValidationError(f"Cannot read {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise GateValidationError(f"{label} must be a JSON object")
    return payload


def require_exact_fields(payload, expected, label):
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise GateValidationError(f"{label} fields must be exactly the approved set ({'; '.join(details)})")


def require_string_list(value, label):
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise GateValidationError(f"{label} must be a list of non-empty strings")


def normalize_relative_path(value):
    if not isinstance(value, str):
        raise GateValidationError("Changed path must be a string")
    normalized = posixpath.normpath(value.replace("\\", "/"))
    if normalized in ("", ".") or normalized.startswith("../") or normalized.startswith("/"):
        raise GateValidationError(f"Changed path is not a safe project-relative path: {value}")
    return normalized


def validate_decision_envelope(envelope):
    """Validate the complete material authorization surface before hashing it."""
    if not isinstance(envelope, dict):
        raise GateValidationError("Decision envelope must be a JSON object")
    require_exact_fields(envelope, ENVELOPE_FIELDS, "Decision envelope")
    if envelope["schema_version"] != "1.0":
        raise GateValidationError("Decision envelope schema_version must be 1.0")
    if envelope["stage"] not in STAGES:
        raise GateValidationError("Decision envelope stage is invalid")
    if not isinstance(envelope["decision_type"], str) or not envelope["decision_type"]:
        raise GateValidationError("Decision envelope decision_type is invalid")

    source_policy = envelope["source_policy"]
    require_exact_fields(source_policy, {"mode", "base_revision", "allowed_fix_paths"}, "Source policy")
    if source_policy["mode"] not in {"exact", "approved_fix_scope"}:
        raise GateValidationError("Source policy mode is invalid")
    if not isinstance(source_policy["base_revision"], str) or not source_policy["base_revision"]:
        raise GateValidationError("Source policy base_revision is invalid")
    require_string_list(source_policy["allowed_fix_paths"], "Source policy allowed_fix_paths")
    normalized_allowed = [normalize_relative_path(path) for path in source_policy["allowed_fix_paths"]]
    if len(set(normalized_allowed)) != len(normalized_allowed):
        raise GateValidationError("Source policy allowed_fix_paths must not contain duplicates")
    if source_policy["mode"] == "exact" and normalized_allowed:
        raise GateValidationError("Exact source policy must not define allowed_fix_paths")

    scope = envelope["scope"]
    require_exact_fields(
        scope,
        {
            "path_ids",
            "targets",
            "write_scope",
            "network",
            "credential_names",
            "sensitive_data",
            "side_effects",
        },
        "Decision envelope scope",
    )
    for field in ("path_ids", "targets", "credential_names", "side_effects"):
        require_string_list(scope[field], f"Decision envelope scope {field}")
    require_string_list(scope["write_scope"], "Decision envelope scope write_scope")
    for path in scope["write_scope"]:
        normalize_relative_path(path)
    if not isinstance(scope["network"], bool) or not isinstance(scope["sensitive_data"], bool):
        raise GateValidationError("Decision envelope scope booleans are invalid")

    interpretation = envelope["interpretation"]
    require_exact_fields(
        interpretation, {"claim", "baseline", "dataset_id", "metric_ids"}, "Decision envelope interpretation"
    )
    for field in ("claim", "baseline", "dataset_id"):
        if interpretation[field] is not None and not isinstance(interpretation[field], str):
            raise GateValidationError(f"Decision envelope interpretation {field} is invalid")
    require_string_list(interpretation["metric_ids"], "Decision envelope interpretation metric_ids")
    if not isinstance(envelope["limits"], dict):
        raise GateValidationError("Decision envelope limits must be an object")


def validate_receipt(receipt, label="Authorization receipt"):
    if not isinstance(receipt, dict):
        raise GateValidationError(f"{label} must be an object")
    require_exact_fields(receipt, RECEIPT_FIELDS, label)
    if not isinstance(receipt["decision_id"], str) or not receipt["decision_id"]:
        raise GateValidationError(f"{label} decision_id is invalid")
    if receipt["stage"] not in STAGES:
        raise GateValidationError(f"{label} stage is invalid")
    if not isinstance(receipt["decision_type"], str) or not receipt["decision_type"]:
        raise GateValidationError(f"{label} decision_type is invalid")
    if not isinstance(receipt["decision_envelope_sha256"], str) or not SHA256.fullmatch(receipt["decision_envelope_sha256"]):
        raise GateValidationError(f"{label} decision_envelope_sha256 is invalid")
    if not isinstance(receipt["source_revision"], str) or not receipt["source_revision"]:
        raise GateValidationError(f"{label} source_revision is invalid")
    if not isinstance(receipt["user_choice"], str):
        raise GateValidationError(f"{label} user_choice is invalid")
    if not isinstance(receipt["approved_limits"], dict):
        raise GateValidationError(f"{label} approved_limits must be an object")
    if not isinstance(receipt["approved_at"], str) or not receipt["approved_at"]:
        raise GateValidationError(f"{label} approved_at is invalid")
    if receipt["invalidated_at"] is not None and not isinstance(receipt["invalidated_at"], str):
        raise GateValidationError(f"{label} invalidated_at is invalid")


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise GateValidationError("Manifest must be a JSON object")
    require_exact_fields(manifest, MANIFEST_FIELDS, "Manifest")
    if manifest["schema_version"] != "3.0":
        raise GateValidationError("Manifest schema_version must be 3.0")
    source = manifest["source_revision"]
    require_exact_fields(source, {"revision", "dirty", "captured_at"}, "Manifest source_revision")
    if not isinstance(source["revision"], str) or not source["revision"]:
        raise GateValidationError("Manifest source_revision revision is invalid")
    if not isinstance(source["dirty"], bool) or not isinstance(source["captured_at"], str) or not source["captured_at"]:
        raise GateValidationError("Manifest source_revision is incomplete")
    if source["dirty"] != source["revision"].startswith("dirty:"):
        raise GateValidationError("Manifest source_revision dirty flag does not match its fingerprint")

    intent = manifest["user_intent"]
    require_exact_fields(
        intent,
        {"goal", "target_users", "in_scope", "out_of_scope", "success_criteria", "risk_tolerance"},
        "Manifest user_intent",
    )
    if not isinstance(intent["goal"], str) or not isinstance(intent["risk_tolerance"], str):
        raise GateValidationError("Manifest user_intent has invalid types")
    for field in ("target_users", "in_scope", "out_of_scope", "success_criteria"):
        require_string_list(intent[field], f"Manifest user_intent {field}")

    permissions = manifest["permissions"]
    require_exact_fields(
        permissions,
        {"write_scope", "production_code_changes", "dependency_install", "live_calls", "public_claims"},
        "Manifest permissions",
    )
    require_string_list(permissions["write_scope"], "Manifest permissions write_scope")
    for path in permissions["write_scope"]:
        normalize_relative_path(path)
    if not all(isinstance(permissions[field], bool) for field in ("production_code_changes", "dependency_install", "live_calls", "public_claims")):
        raise GateValidationError("Manifest permissions have invalid types")

    stages = manifest["stages"]
    if not isinstance(stages, dict) or set(stages) != STAGES:
        raise GateValidationError("Manifest stages must contain exactly stage1 through stage4")
    for stage, state in stages.items():
        if not isinstance(state, dict):
            raise GateValidationError(f"Manifest state for {stage} must be an object")
        checks = (
            ("phase_status", PHASE_STATUSES),
            ("result_outcome", RESULT_OUTCOMES),
            ("execution_scope", EXECUTION_SCOPES),
            ("claim_eligibility", CLAIM_ELIGIBILITY),
            ("gate_state", GATE_STATES),
        )
        for field, allowed in checks:
            if state.get(field) not in allowed:
                raise GateValidationError(f"Manifest {stage}.{field} is invalid")
        for field in ("artifacts", "blockers", "recovery_conditions"):
            if not isinstance(state.get(field), list):
                raise GateValidationError(f"Manifest {stage}.{field} must be a list")

    if not isinstance(manifest["source_history"], list):
        raise GateValidationError("Manifest source_history must be a list")
    for item in manifest["source_history"]:
        if not isinstance(item, dict):
            raise GateValidationError("Manifest source_history entries must be objects")
        require_exact_fields(item, SOURCE_HISTORY_FIELDS, "Manifest source_history entry")
        if not isinstance(item["base_revision"], str) or not item["base_revision"]:
            raise GateValidationError("Manifest source_history base_revision is invalid")
        if not isinstance(item["current_revision"], str) or not item["current_revision"]:
            raise GateValidationError("Manifest source_history current_revision is invalid")
        if not isinstance(item["affected_artifacts_stale"], bool):
            raise GateValidationError("Manifest source_history affected_artifacts_stale is invalid")
        if not isinstance(item["recorded_at"], str) or not item["recorded_at"]:
            raise GateValidationError("Manifest source_history recorded_at is invalid")
    profile = manifest["project_profile"]
    require_exact_fields(profile, {"path", "status", "approved_fields_sha256"}, "Manifest project_profile")
    if not isinstance(profile["path"], str) or not profile["path"]:
        raise GateValidationError("Manifest project_profile path is invalid")
    if not isinstance(profile["status"], str) or not profile["status"]:
        raise GateValidationError("Manifest project_profile status is invalid")
    approved_hash = profile["approved_fields_sha256"]
    if approved_hash is not None and (not isinstance(approved_hash, str) or not SHA256.fullmatch(approved_hash)):
        raise GateValidationError("Manifest project_profile approved_fields_sha256 is invalid")
    if not isinstance(manifest["decisions"], list):
        raise GateValidationError("Manifest decisions must be a list")


def parse_limit(value):
    key, separator, raw = value.partition("=")
    if not separator or not key or not raw:
        raise GateValidationError(f"Invalid --limit value: {value}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return key, parsed


def source_fingerprint(root):
    """Return a Git identity without outputting tracked or untracked file contents."""
    root = Path(root).resolve()
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.strip()
        tracked_diff = subprocess.run(
            [
                "git", "-C", str(root), "diff", "--binary", "HEAD", "--", ".",
                ":(exclude)project_verification_workbench/**",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout
        untracked = subprocess.run(
            [
                "git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z", "--", ".",
                ":(exclude)project_verification_workbench/**",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GateValidationError(f"Cannot fingerprint source repository: {exc}") from exc
    if not tracked_diff and not untracked:
        return f"git:{head}"

    digest = hashlib.sha256(tracked_diff)
    for raw_path in untracked.split(b"\0"):
        if not raw_path:
            continue
        path_text = raw_path.decode("utf-8", errors="surrogateescape")
        file_path = root / path_text
        digest.update(raw_path + b"\0")
        try:
            if file_path.is_symlink():
                digest.update(os.readlink(file_path).encode("utf-8", errors="surrogateescape"))
            elif file_path.is_file():
                digest.update(file_path.read_bytes())
            else:
                digest.update(b"non-file")
        except OSError:
            digest.update(b"missing")
    return f"dirty:{head}:{digest.hexdigest()}"


def run_git(project_root, arguments, failure):
    result = subprocess.run(
        ["git", "-C", str(project_root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GateValidationError(failure)
    return result.stdout


def validate_source_policy(envelope, receipt, manifest, current_revision, project_root):
    source_policy = envelope["source_policy"]
    base_revision = source_policy["base_revision"]
    if receipt["source_revision"] != base_revision:
        raise GateValidationError("Authorization receipt source_revision does not match the decision envelope base")
    if source_policy["mode"] == "exact":
        if base_revision != current_revision:
            raise GateValidationError("Exact source policy requires the current fingerprint to equal the approved base")
        return

    match = COMMIT_REVISION.fullmatch(base_revision)
    if not match:
        raise GateValidationError("Approved-fix source policy requires a clean Git commit base")
    if project_root is None:
        raise GateValidationError("Approved-fix source policy requires --project-root for Git verification")
    base_commit = match.group(1)
    run_git(project_root, ["rev-parse", "--verify", f"{base_commit}^{{commit}}"], "Approved-fix base commit is unavailable")
    ancestor = subprocess.run(
        ["git", "-C", str(project_root), "merge-base", "--is-ancestor", base_commit, "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise GateValidationError("Approved-fix base commit is not an ancestor of HEAD")

    changed = run_git(
        project_root,
        ["diff", "--name-only", "-z", base_commit, "--", "."],
        "Cannot enumerate committed, staged, and unstaged changes from the approved base",
    ).split("\0")
    untracked = run_git(
        project_root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
        "Cannot enumerate untracked changes from the approved base",
    ).split("\0")
    allowed = [normalize_relative_path(path) for path in source_policy["allowed_fix_paths"]]
    all_paths = sorted({normalize_relative_path(path) for path in changed + untracked if path})
    outside = [
        path
        for path in all_paths
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in allowed)
    ]
    if outside:
        raise GateValidationError("Changed paths are outside approved fix scope: " + ", ".join(outside))
    if current_revision != base_revision:
        history = [
            item
            for item in manifest["source_history"]
            if item["base_revision"] == base_revision
            and item["current_revision"] == current_revision
            and item["affected_artifacts_stale"] is True
        ]
        if len(history) != 1:
            raise GateValidationError(
                "Manifest source_history must record the approved base, current fingerprint, and stale affected artifacts"
            )


def validate_check(args):
    manifest = load_object(args.manifest, "manifest")
    receipt = load_object(args.receipt, "authorization receipt")
    envelope = load_object(args.envelope, "decision envelope")
    validate_manifest(manifest)
    validate_receipt(receipt)
    validate_decision_envelope(envelope)

    if receipt["stage"] != args.stage or receipt["decision_type"] != args.decision_type:
        raise GateValidationError("Authorization stage or decision type does not match this operation")
    if envelope["stage"] != args.stage or envelope["decision_type"] != args.decision_type:
        raise GateValidationError("Decision envelope stage or decision type does not match this operation")
    if receipt["user_choice"] != "approved":
        raise GateValidationError("Authorization user choice is not approved")
    if receipt["invalidated_at"] is not None:
        raise GateValidationError("Authorization has been invalidated")
    if receipt["decision_envelope_sha256"] != canonical_object_hash(envelope):
        raise GateValidationError("Authorization decision envelope hash does not match the current envelope")
    if receipt["approved_limits"] != envelope["limits"]:
        raise GateValidationError("Authorization approved_limits do not match the decision envelope limits")

    current_revision = args.source_revision
    if not isinstance(current_revision, str) or not current_revision:
        raise GateValidationError("Current source revision is invalid")
    if args.project_root:
        computed_revision = source_fingerprint(args.project_root)
        if computed_revision != current_revision:
            raise GateValidationError("Current source revision does not match the project fingerprint")
    if manifest["source_revision"]["revision"] != current_revision:
        raise GateValidationError("Manifest source revision does not match the current source revision")

    matches = [
        item
        for item in manifest["decisions"]
        if isinstance(item, dict) and item.get("decision_id") == receipt["decision_id"]
    ]
    if len(matches) != 1:
        raise GateValidationError("Authorization decision_id is not uniquely recorded in the manifest")
    manifest_decision = matches[0]
    validate_receipt(manifest_decision, "Manifest authorization receipt")
    if manifest_decision != receipt:
        raise GateValidationError("Authorization receipt differs from the manifest decision")

    stage_state = manifest["stages"].get(args.stage)
    if stage_state.get("gate_state") != "approved":
        raise GateValidationError(f"Manifest gate_state for {args.stage} is not approved")
    requested_limits = {}
    for raw_limit in args.limit:
        key, requested = parse_limit(raw_limit)
        if key in requested_limits:
            raise GateValidationError(f"Authorization limit {key} was specified more than once")
        requested_limits[key] = requested
    for key, requested in requested_limits.items():
        if key not in receipt["approved_limits"]:
            raise GateValidationError(f"Authorization limit {key} is not approved")
        if not requested_limit_is_within(receipt["approved_limits"][key], requested):
            raise GateValidationError(f"Authorization limit {key} exceeds the approved maximum")

    validate_source_policy(envelope, receipt, manifest, current_revision, args.project_root)
    return {
        "approved": True,
        "decision_id": receipt["decision_id"],
        "decision_envelope_sha256": receipt["decision_envelope_sha256"],
        "approved_source_revision": receipt["source_revision"],
        "current_source_revision": current_revision,
        "approved_limits": receipt["approved_limits"],
        "source_policy": envelope["source_policy"]["mode"],
    }


def validate_paths(args):
    manifest = load_object(args.manifest, "manifest")
    validate_manifest(manifest)
    allowed = [normalize_relative_path(value) for value in manifest["permissions"]["write_scope"]]
    changed = [normalize_relative_path(value) for value in args.changed_file]
    outside = [
        path
        for path in changed
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in allowed)
    ]
    if outside:
        raise GateValidationError("Changed files are outside the approved write scope: " + ", ".join(outside))
    return {"approved": True, "changed_files": changed, "write_scope": allowed}


def build_parser():
    parser = argparse.ArgumentParser(description="Validate V3 project-verifier decision envelopes")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Validate one V3 authorization receipt")
    check.add_argument("--manifest", required=True)
    check.add_argument("--receipt", required=True)
    check.add_argument("--envelope", required=True)
    check.add_argument("--source-revision", required=True)
    check.add_argument("--project-root")
    check.add_argument("--stage", required=True)
    check.add_argument("--decision-type", required=True)
    check.add_argument("--limit", action="append", default=[])
    paths = subparsers.add_parser("paths", help="Validate changed files against V3 manifest write scope")
    paths.add_argument("--manifest", required=True)
    paths.add_argument("--changed-file", action="append", required=True)
    fingerprint = subparsers.add_parser("fingerprint", help="Print a secret-safe Git source fingerprint")
    fingerprint.add_argument("--root", default=".")
    return parser


def main():
    args = build_parser().parse_args()
    try:
        if args.command == "check":
            result = validate_check(args)
        elif args.command == "paths":
            result = validate_paths(args)
        elif args.command == "fingerprint":
            print(source_fingerprint(args.root))
            return
        else:
            raise GateValidationError(f"Unsupported command: {args.command}")
    except (GateValidationError, OSError) as exc:
        print(f"Gate validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
