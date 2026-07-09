#!/usr/bin/env python3
"""Validate a high-risk project-verifier decision receipt without dependencies."""

import argparse
import hashlib
import json
import os
import posixpath
import subprocess
import sys
from pathlib import Path


PHASE_STATUSES = {"pending", "in_progress", "completed", "blocked", "skipped", "not_applicable", "failed"}
RESULT_OUTCOMES = {"not_run", "pass", "fail", "partial", "inconclusive"}
EXECUTION_SCOPES = {"none", "plan_only", "pilot", "full"}
CLAIM_ELIGIBILITY = {"none", "pilot", "full"}
REQUIRED_DECISION_FIELDS = {
    "decision_id",
    "phase",
    "decision_type",
    "proposal_sha256",
    "source_revision",
    "user_choice",
    "approved_limits",
    "approved_at",
    "invalidated_at",
}


class GateValidationError(ValueError):
    pass


def load_object(path, label):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise GateValidationError(f"Cannot read {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise GateValidationError(f"{label} must be a JSON object")
    return payload


def validate_manifest(manifest):
    if manifest.get("schema_version") != "2.0":
        raise GateValidationError("Manifest schema_version must be 2.0")
    source = manifest.get("source_revision")
    if not isinstance(source, dict) or not source.get("revision") or not source.get("captured_at"):
        raise GateValidationError("Manifest source_revision is incomplete")
    if source.get("dirty") is True and not str(source["revision"]).startswith("dirty:"):
        raise GateValidationError("A dirty source must use a deterministic dirty: fingerprint as its revision")
    intent = manifest.get("user_intent")
    required_intent = {"goal", "target_users", "in_scope", "out_of_scope", "success_criteria", "risk_tolerance"}
    if not isinstance(intent, dict) or not required_intent <= set(intent):
        raise GateValidationError("Manifest user_intent is incomplete")
    permissions = manifest.get("permissions")
    required_permissions = {"write_scope", "production_code_changes", "dependency_install", "live_calls", "public_claims"}
    if not isinstance(permissions, dict) or not required_permissions <= set(permissions):
        raise GateValidationError("Manifest permissions are incomplete")
    if not isinstance(permissions["write_scope"], list) or not all(
        isinstance(permissions[field], bool)
        for field in ("production_code_changes", "dependency_install", "live_calls", "public_claims")
    ):
        raise GateValidationError("Manifest permissions have invalid types")
    for phase, state in (manifest.get("phases") or {}).items():
        if not isinstance(state, dict):
            raise GateValidationError(f"Manifest state for {phase} must be an object")
        checks = (
            ("phase_status", PHASE_STATUSES),
            ("result_outcome", RESULT_OUTCOMES),
            ("execution_scope", EXECUTION_SCOPES),
            ("claim_eligibility", CLAIM_ELIGIBILITY),
        )
        for field, allowed in checks:
            if state.get(field) not in allowed:
                raise GateValidationError(f"Manifest {phase}.{field} is invalid")
    if not isinstance(manifest.get("decisions"), list):
        raise GateValidationError("Manifest decisions must be a list")


def proposal_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_limit(value):
    key, separator, raw = value.partition("=")
    if not separator or not key or not raw:
        raise GateValidationError(f"Invalid --limit value: {value}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return key, parsed


def validate_check(args):
    manifest = load_object(args.manifest, "manifest")
    receipt = load_object(args.receipt, "authorization receipt")
    validate_manifest(manifest)

    missing = sorted(REQUIRED_DECISION_FIELDS - set(receipt))
    if missing:
        raise GateValidationError("Authorization receipt is missing: " + ", ".join(missing))
    if receipt["phase"] != args.phase or receipt["decision_type"] != args.decision_type:
        raise GateValidationError("Authorization phase or decision type does not match this operation")
    if receipt["user_choice"] != "approved":
        raise GateValidationError("Authorization user choice is not approved")
    if receipt["invalidated_at"] is not None:
        raise GateValidationError("Authorization has been invalidated")
    if not receipt["approved_at"]:
        raise GateValidationError("Authorization has no approval timestamp")

    if args.project_root:
        current_revision = source_fingerprint(args.project_root)
        if current_revision != args.source_revision:
            raise GateValidationError(
                "Current source revision does not match the authorized source revision"
            )

    actual_hash = proposal_hash(args.proposal)
    if receipt["proposal_sha256"] != actual_hash:
        raise GateValidationError("Authorization proposal hash does not match the current proposal")

    manifest_revision = manifest["source_revision"]["revision"]
    if receipt["source_revision"] != args.source_revision or manifest_revision != args.source_revision:
        raise GateValidationError("Authorization source revision does not match the current source revision")

    matches = [
        item
        for item in manifest["decisions"]
        if isinstance(item, dict) and item.get("decision_id") == receipt["decision_id"]
    ]
    if len(matches) != 1:
        raise GateValidationError("Authorization decision_id is not uniquely recorded in the manifest")
    manifest_decision = matches[0]
    for field in REQUIRED_DECISION_FIELDS:
        if manifest_decision.get(field) != receipt.get(field):
            raise GateValidationError(f"Authorization field {field} differs from the manifest decision")

    limits = receipt.get("approved_limits")
    if not isinstance(limits, dict):
        raise GateValidationError("Authorization approved_limits must be an object")
    requested_limits = dict(parse_limit(value) for value in args.limit)
    for key, requested in requested_limits.items():
        if limits.get(key) != requested:
            raise GateValidationError(f"Authorization limit {key} does not match the requested execution")

    phase_state = (manifest.get("phases") or {}).get(args.phase)
    if not isinstance(phase_state, dict) or phase_state.get("gate_state") != "approved":
        raise GateValidationError(f"Manifest gate_state for {args.phase} is not approved")

    return {
        "approved": True,
        "decision_id": receipt["decision_id"],
        "proposal_sha256": actual_hash,
        "source_revision": args.source_revision,
        "approved_limits": limits,
    }


def normalize_relative_path(value):
    normalized = posixpath.normpath(value.replace("\\", "/"))
    if normalized in ("", ".") or normalized.startswith("../") or normalized.startswith("/"):
        raise GateValidationError(f"Changed path is not a safe project-relative path: {value}")
    return normalized


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


def source_fingerprint(root):
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


def build_parser():
    parser = argparse.ArgumentParser(description="Validate project-verifier gate receipts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Validate one high-risk authorization")
    check.add_argument("--manifest", required=True)
    check.add_argument("--receipt", required=True)
    check.add_argument("--proposal", required=True)
    check.add_argument("--source-revision", required=True)
    check.add_argument("--project-root")
    check.add_argument("--phase", required=True)
    check.add_argument("--decision-type", required=True)
    check.add_argument("--limit", action="append", default=[])
    paths = subparsers.add_parser("paths", help="Validate changed files against manifest write scope")
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
