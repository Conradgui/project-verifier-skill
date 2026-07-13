#!/bin/bash
# Stage 3 runner for authorized, project-adapted security task bridges.

set -u

RUNNER_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BUNDLED_GATE_VALIDATOR="$RUNNER_DIR/../scripts/validate_gate.py"
TASK_DIR="${SECURITY_TASK_DIR:-security/tasks}"
REPORTS_DIR="${SECURITY_REPORTS_DIR:-project_verification_workbench/security-reports}"
RESULTS_JSON="${SECURITY_RESULTS_JSON:-project_verification_workbench/stage3_security_results.json}"
MANIFEST_FILE="${SECURITY_MANIFEST_FILE:-project_verification_workbench/verification_manifest.json}"
AUTHORIZATION_FILE="${SECURITY_AUTHORIZATION_FILE:-}"
ENVELOPE_FILE="${SECURITY_ENVELOPE_FILE:-}"
PROFILE_FILE="${SECURITY_PROFILE_FILE:-project_verification_workbench/project_profile.json}"
SOURCE_REVISION="${SECURITY_SOURCE_REVISION:-}"
GATE_VALIDATOR="${PROJECT_VERIFIER_GATE_VALIDATOR:-$BUNDLED_GATE_VALIDATOR}"
PROJECT_ROOT="${PROJECT_VERIFIER_PROJECT_ROOT:-.}"
MODE="${1:-}"
CAPABILITIES='offline_read_only tool_download vulnerability_database_update network passive_dynamic_scan active_scan'
TRUSTED_CUSTOM_BRIDGE_EXECUTION='trusted_custom_bridge_execution'

usage() {
    echo "Usage: $0 preflight|run"
    echo "  preflight  Validate the Profile, task metadata, tools, targets, paths, limits, and permissions without running a security task."
    echo "  run        Dispatch only explicitly authorized trusted custom bridges under the current stage3/security_execution authorization."
}

if [ -z "$MODE" ]; then
    usage
    exit 0
fi

case "$MODE" in
    preflight|run) ;;
    *) usage; exit 2 ;;
esac

normalize_project_directory() {
    python3 - "$PROJECT_ROOT" "$1" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
raw = sys.argv[2]
candidate = Path(raw)
if not candidate.is_absolute():
    candidate = root / candidate
if candidate.is_symlink():
    raise SystemExit(f"[Error] Project directory must not be a symlink: {raw}")
candidate = candidate.resolve()
try:
    candidate.relative_to(root)
except ValueError:
    raise SystemExit(f"[Error] Project directory must stay inside the project root: {raw}")
if not candidate.is_dir():
    raise SystemExit(f"[Error] Project directory is missing: {raw}")
print(candidate)
PY
}

normalize_workbench_output_path() {
    python3 - "$PROJECT_ROOT" "$1" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
workbench = root / "project_verification_workbench"
if workbench.is_symlink():
    raise SystemExit("[Error] The project workbench must not be a symlink.")
workbench = workbench.resolve()
raw = sys.argv[2]
candidate = Path(raw)
if not candidate.is_absolute():
    candidate = root / candidate
if candidate.is_symlink():
    raise SystemExit(f"[Error] Output path must not be a symlink: {raw}")
candidate = candidate.resolve()
try:
    candidate.relative_to(workbench)
except ValueError:
    raise SystemExit(f"[Error] Output path must stay inside project_verification_workbench: {raw}")
print(candidate)
PY
}

ensure_source_bound_task_directory() {
    python3 - "$PROJECT_ROOT" "$TASK_DIR" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
task_dir = Path(sys.argv[2]).resolve()
workbench = (root / "project_verification_workbench").resolve()
relative = task_dir.relative_to(root)
if relative.parts and relative.parts[0] == ".git":
    raise SystemExit("[Error] Security task directory must be source-bound and outside Git metadata.")
try:
    task_dir.relative_to(workbench)
except ValueError:
    print(task_dir)
else:
    raise SystemExit("[Error] Security task directory must be source-bound and outside project_verification_workbench.")
PY
}

resolve_external_temp_directory() {
    python3 - "$PROJECT_ROOT" "${TMPDIR:-/tmp}" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
temporary = Path(sys.argv[2]).resolve()
if not temporary.is_dir():
    raise SystemExit("[Error] Temporary directory is missing or not a directory.")
try:
    temporary.relative_to(root)
except ValueError:
    print(temporary)
else:
    raise SystemExit("[Error] Temporary directory must stay outside the target project.")
PY
}

ensure_skill_validator() {
    python3 - "$PROJECT_ROOT" "$GATE_VALIDATOR" "$BUNDLED_GATE_VALIDATOR" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
validator = Path(sys.argv[2])
bundled = Path(sys.argv[3]).resolve()
if validator.is_symlink() or not validator.is_file() or validator.resolve() != bundled:
    raise SystemExit("[Error] Gate validator must be the bundled Skill validator.")
try:
    bundled.relative_to(root)
except ValueError:
    print(bundled)
else:
    raise SystemExit("[Error] Bundled Skill validator must stay outside the target project.")
PY
}

nonnegative_limit() {
    case "$1" in
        ""|*[!0-9]*) return 1 ;;
        *) return 0 ;;
    esac
}

check_execution_bounds() {
    failed=0
    for name in SECURITY_MAX_TASKS SECURITY_MAX_COMMANDS_PER_TASK SECURITY_TIMEOUT_SECONDS; do
        value="${!name:-}"
        if ! nonnegative_limit "$value"; then
            echo "[Error] Invalid execution bound: $name must be a non-negative integer."
            failed=1
        fi
    done
    if [ "$failed" -ne 0 ]; then return 1; fi
    if [ "$SECURITY_MAX_TASKS" -lt 1 ] || [ "$SECURITY_MAX_COMMANDS_PER_TASK" -lt 1 ] || [ "$SECURITY_TIMEOUT_SECONDS" -lt 1 ]; then
        echo "[Error] SECURITY_MAX_TASKS, SECURITY_MAX_COMMANDS_PER_TASK, and SECURITY_TIMEOUT_SECONDS must each be at least 1."
        return 1
    fi
    return 0
}

check_profile_handoff() {
    for path in "$MANIFEST_FILE" "$PROFILE_FILE" "$GATE_VALIDATOR"; do
        if [ ! -f "$path" ]; then
            echo "[Error] Profile handoff file is missing: $path"
            return 1
        fi
    done
    python3 "$GATE_VALIDATOR" profile --manifest "$MANIFEST_FILE" --profile "$PROFILE_FILE" --project-root "$PROJECT_ROOT" || {
        echo "[Error] Profile handoff validation failed."
        return 1
    }
    echo "Profile handoff passed."
}

TASK_DIR=$(normalize_project_directory "$TASK_DIR") || exit 1
ensure_source_bound_task_directory >/dev/null || exit 1
REPORTS_DIR=$(normalize_workbench_output_path "$REPORTS_DIR") || exit 1
RESULTS_JSON=$(normalize_workbench_output_path "$RESULTS_JSON") || exit 1
EXTERNAL_TEMP_DIR=$(resolve_external_temp_directory) || exit 1
ensure_skill_validator >/dev/null || exit 1

TASK_SCRIPTS=()
while IFS= read -r task; do
    TASK_SCRIPTS[${#TASK_SCRIPTS[@]}]="$task"
done < <(find "$TASK_DIR" -type f \( -name 'security_P0_*.sh' -o -name 'security_P0_*.py' \) | sort)

if [ "${#TASK_SCRIPTS[@]}" -eq 0 ]; then
    echo "[Error] No security tasks matching 'security_P0_*' found in $TASK_DIR."
    exit 1
fi

validate_task_metadata() {
    TASK_METADATA_FILE=$(mktemp "$EXTERNAL_TEMP_DIR/project-verifier-security-metadata.XXXXXX") || {
        echo "[Error] Unable to create temporary security metadata."
        return 1
    }
    python3 - "$PROJECT_ROOT" "$TASK_DIR" "$REPORTS_DIR" "$RESULTS_JSON" "$SECURITY_MAX_TASKS" "$CAPABILITIES" "${TASK_SCRIPTS[@]}" > "$TASK_METADATA_FILE" <<'PY'
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
task_dir = Path(sys.argv[2]).resolve()
reports_dir = Path(sys.argv[3]).resolve()
results_path = Path(sys.argv[4]).resolve()
max_tasks = int(sys.argv[5])
capabilities = set(sys.argv[6].split())
scripts = [Path(value) for value in sys.argv[7:]]
workbench = (root / "project_verification_workbench").resolve()
tool_name = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]*$")
required = {"task_id", "tool", "target", "capability", "network", "active", "side_effects", "raw_output_path"}
seen_ids = set()
seen_raw_paths = set()
failed = False

def inside_workbench(path, label):
    try:
        path.relative_to(workbench)
    except ValueError:
        raise ValueError(f"{label} must stay inside project_verification_workbench")

def is_ignored(path):
    relative = path.relative_to(root)
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--", str(relative)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise ValueError("cannot determine whether the security task is ignored by Git")

def is_git_metadata(path):
    return ".git" in path.relative_to(root).parts

try:
    inside_workbench(reports_dir, "Reports path")
    inside_workbench(results_path, "Results path")
except ValueError as exc:
    print(f"[Error] {exc}")
    raise SystemExit(1)
if len(scripts) > max_tasks:
    print(f"[Error] Found {len(scripts)} tasks, exceeding approved max_tasks={max_tasks}.")
    raise SystemExit(1)

for script in scripts:
    descriptor_path = script.with_suffix(".task.json")
    if script.is_symlink() or not script.is_file():
        print(f"[Error] Security task must be a regular file: {script}")
        failed = True
        continue
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        print(f"[Error] Security task metadata is missing or unsafe: {descriptor_path}")
        failed = True
        continue
    if is_git_metadata(script) or is_git_metadata(descriptor_path):
        print(f"[Error] Security task or metadata is inside Git metadata and not source-bound: {script}")
        failed = True
        continue
    if is_ignored(script) or is_ignored(descriptor_path):
        print(f"[Error] Security task or metadata is Git-ignored and not source-bound: {script}")
        failed = True
        continue
    try:
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        if not isinstance(descriptor, dict) or set(descriptor) != required:
            raise ValueError("metadata fields must be exactly task_id, tool, target, capability, network, active, side_effects, raw_output_path")
        task_id = descriptor["task_id"]
        expected_id = script.stem.removeprefix("security_")
        if not isinstance(task_id, str) or not task_id or task_id != expected_id or task_id in seen_ids:
            raise ValueError("task_id must match its script name and be unique")
        seen_ids.add(task_id)
        tool = descriptor["tool"]
        if not isinstance(tool, dict) or set(tool) != {"name", "version", "fallback"}:
            raise ValueError("tool must contain name, version, and fallback")
        if not all(isinstance(tool[key], str) and tool[key] for key in tool):
            raise ValueError("tool metadata values must be non-empty strings")
        if not tool_name.fullmatch(tool["name"]):
            raise ValueError("tool name is invalid")
        if not isinstance(descriptor["target"], str) or not descriptor["target"]:
            raise ValueError("target must be a non-empty string")
        if descriptor["capability"] not in capabilities:
            raise ValueError("capability is not recognized")
        if not isinstance(descriptor["network"], bool) or not isinstance(descriptor["active"], bool):
            raise ValueError("network and active must be booleans")
        if descriptor["active"] != (descriptor["capability"] == "active_scan"):
            raise ValueError("active must match the active_scan capability")
        if not isinstance(descriptor["side_effects"], list) or not all(isinstance(value, str) for value in descriptor["side_effects"]):
            raise ValueError("side_effects must be a list of strings")
        raw_path = Path(descriptor["raw_output_path"])
        if raw_path.is_absolute():
            raise ValueError("raw_output_path must be project-relative")
        raw_path = (root / raw_path).resolve()
        inside_workbench(raw_path, "raw_output_path")
        if raw_path.exists():
            raise ValueError("raw_output_path must not exist before dispatch")
        reserved_paths = {
            results_path,
            reports_dir / ".security_results.jsonl",
            reports_dir / f"{task_id}.log",
        }
        if raw_path in reserved_paths:
            raise ValueError("raw_output_path collides with a runner result or log path")
        if any(path.exists() or path.is_symlink() for path in reserved_paths):
            raise ValueError("runner result and log paths must be new for this execution")
        if raw_path in seen_raw_paths:
            raise ValueError("raw_output_path is duplicate across security tasks")
        seen_raw_paths.add(raw_path)
        if descriptor["active"] and not descriptor["target"].startswith(("local-", "local://", "isolated-", "isolated://")):
            raise ValueError("active scans require a local or isolated target")
        available = shutil.which(tool["name"]) is not None
        if not available:
            print(f"[Tool unavailable] {tool['name']}; fallback: {tool['fallback']}; coverage reduced.")
            failed = True
        print("\t".join((task_id, str(script.resolve()), tool["name"], tool["version"], descriptor["target"], descriptor["capability"], str(descriptor["network"]).lower(), str(descriptor["active"]).lower(), json.dumps(descriptor["side_effects"], separators=(",", ":")), str(raw_path))))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[Error] Invalid security task metadata for {script}: {exc}")
        failed = True

raise SystemExit(1 if failed else 0)
PY
    result=$?
    if [ "$result" -ne 0 ]; then
        cat "$TASK_METADATA_FILE"
        rm -f "$TASK_METADATA_FILE"
        return 1
    fi
    return 0
}

perform_preflight() {
    failed=0
    check_execution_bounds || failed=1
    validate_task_metadata || failed=1
    check_profile_handoff || failed=1
    if [ "$failed" -ne 0 ]; then
        rm -f "$TASK_METADATA_FILE"
        echo "Preflight failed. No security task was executed."
        return 1
    fi
    echo "Preflight passed for ${#TASK_SCRIPTS[@]} security task(s). No security task was executed."
    return 0
}

authorized_task_set_and_capabilities() {
    python3 - "$ENVELOPE_FILE" "$CAPABILITIES" "$TRUSTED_CUSTOM_BRIDGE_EXECUTION" "$TASK_METADATA_FILE" <<'PY'
import json
import sys
from pathlib import Path

envelope = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
allowed_names = set(sys.argv[2].split())
trusted_bridge_marker = sys.argv[3]
lines = Path(sys.argv[4]).read_text(encoding="utf-8").splitlines()
scope = envelope.get("scope", {})
limits = envelope.get("limits", {})
matrix = limits.get("capabilities")
if not isinstance(matrix, dict) or set(matrix) != allowed_names or not all(isinstance(value, bool) for value in matrix.values()):
    raise SystemExit("[Error] Security authorization capabilities must be a complete boolean matrix.")
if scope.get("network") is not matrix["network"]:
    raise SystemExit("[Error] Security authorization network scope does not match its capability.")
approved_ids = scope.get("path_ids")
approved_targets = scope.get("targets")
approved_side_effects = scope.get("side_effects")
if not isinstance(approved_ids, list) or not isinstance(approved_targets, list):
    raise SystemExit("[Error] Security authorization task paths or targets are invalid.")
if not all(isinstance(value, str) and value for value in approved_ids + approved_targets):
    raise SystemExit("[Error] Security authorization task paths or targets are invalid.")
if (
    not isinstance(approved_side_effects, list)
    or not all(isinstance(value, str) and value for value in approved_side_effects)
    or trusted_bridge_marker not in approved_side_effects
):
    raise SystemExit("[Error] Running a trusted custom bridge requires explicit trusted custom bridge authorization.")
if len(approved_ids) != len(approved_targets) or len(set(approved_ids)) != len(approved_ids):
    raise SystemExit("[Error] Security authorization task-target bindings are incomplete or duplicate.")
approved_bindings = set(zip(approved_ids, approved_targets))
if len(approved_bindings) != len(approved_ids):
    raise SystemExit("[Error] Security authorization task-target bindings are duplicate.")
actual_bindings = []
for line in lines:
    parts = line.split("\t")
    if len(parts) != 10:
        raise SystemExit("[Error] Security task metadata is malformed.")
    task_id, _, _, _, target, capability, network, active, side_effects, _ = parts
    actual_bindings.append((task_id, target))
    try:
        declared_side_effects = json.loads(side_effects)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[Error] Security task side effects are malformed: {exc}") from exc
    if not isinstance(declared_side_effects, list) or not all(isinstance(value, str) and value for value in declared_side_effects):
        raise SystemExit("[Error] Security task side effects are malformed.")
    if not set(declared_side_effects).issubset(set(approved_side_effects)):
        raise SystemExit("[Error] Security task declares a side effect that is not authorized.")
    required = {capability}
    required.update(set(declared_side_effects).intersection(allowed_names))
    if network == "true" and capability != "network":
        required.add("network")
    if active == "true" and capability != "active_scan":
        required.add("active_scan")
    for name in sorted(required):
        if not matrix.get(name, False):
            raise SystemExit(f"[Error] Security capability is not separately authorized: {name}")
if set(actual_bindings) != approved_bindings or len(actual_bindings) != len(approved_bindings):
    raise SystemExit("[Error] Authorized task-target bindings do not exactly match discovered security tasks.")
print(json.dumps(matrix, sort_keys=True, separators=(",", ":")))
PY
}

authorized_write_scope() {
    python3 - "$MANIFEST_FILE" "$ENVELOPE_FILE" "$PROJECT_ROOT" "$REPORTS_DIR" "$RESULTS_JSON" "$TASK_METADATA_FILE" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
envelope = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
root = Path(sys.argv[3]).resolve()
reports_dir = Path(sys.argv[4]).resolve()
results_path = Path(sys.argv[5]).resolve()
lines = Path(sys.argv[6]).read_text(encoding="utf-8").splitlines()

def normalized_scopes(value, label):
    if not isinstance(value, list) or not value:
        raise SystemExit(f"[Error] {label} must be a non-empty list.")
    scopes = []
    for raw in value:
        if not isinstance(raw, str) or not raw:
            raise SystemExit(f"[Error] {label} contains an invalid path.")
        candidate = Path(raw)
        if candidate.is_absolute():
            raise SystemExit(f"[Error] {label} paths must be project-relative.")
        candidate = (root / candidate).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            raise SystemExit(f"[Error] {label} paths must stay inside the project root.")
        scopes.append(candidate)
    return scopes

manifest_scopes = normalized_scopes(manifest.get("permissions", {}).get("write_scope"), "Manifest write scope")
envelope_scopes = normalized_scopes(envelope.get("scope", {}).get("write_scope"), "Authorization write scope")

outputs = [reports_dir, results_path]
for line in lines:
    parts = line.split("\t")
    if len(parts) != 10:
        raise SystemExit("[Error] Security task metadata is malformed.")
    outputs.append(Path(parts[9]).resolve())

def covered(path, scopes):
    for scope in scopes:
        try:
            path.relative_to(scope)
            return True
        except ValueError:
            pass
    return False

for output in outputs:
    if not covered(output, manifest_scopes) or not covered(output, envelope_scopes):
        raise SystemExit("[Error] Security runner output is outside the authorized write scope.")
PY
}

check_execution_authorization() {
    for name in AUTHORIZATION_FILE ENVELOPE_FILE SOURCE_REVISION; do
        if [ -z "${!name:-}" ]; then
            echo "[Error] Missing execution authorization input: $name"
            return 1
        fi
    done
    for path in "$MANIFEST_FILE" "$AUTHORIZATION_FILE" "$ENVELOPE_FILE" "$PROFILE_FILE" "$GATE_VALIDATOR"; do
        if [ ! -f "$path" ]; then
            echo "[Error] Execution authorization file is missing: $path"
            return 1
        fi
    done
    SECURITY_CAPABILITIES_JSON=$(authorized_task_set_and_capabilities) || return 1
    authorized_write_scope || return 1
    GATE_RESULT_JSON=$(python3 "$GATE_VALIDATOR" check \
        --manifest "$MANIFEST_FILE" \
        --receipt "$AUTHORIZATION_FILE" \
        --envelope "$ENVELOPE_FILE" \
        --source-revision "$SOURCE_REVISION" \
        --project-root "$PROJECT_ROOT" \
        --stage stage3 \
        --decision-type security_execution \
        --limit "max_tasks=$SECURITY_MAX_TASKS" \
        --limit "max_commands_per_task=$SECURITY_MAX_COMMANDS_PER_TASK" \
        --limit "timeout_seconds=$SECURITY_TIMEOUT_SECONDS" \
        --limit "capabilities=$SECURITY_CAPABILITIES_JSON") || {
            echo "[Error] Execution authorization validation failed."
            return 1
        }
    return 0
}

if [ "$MODE" = "preflight" ]; then
    perform_preflight
    result=$?
    rm -f "${TASK_METADATA_FILE:-}"
    exit "$result"
fi

perform_preflight || exit 1
check_execution_authorization || {
    rm -f "$TASK_METADATA_FILE"
    exit 1
}
mkdir -p "$REPORTS_DIR" "$(dirname "$RESULTS_JSON")"
TASK_RESULTS_FILE="$REPORTS_DIR/.security_results.jsonl"
python3 - "$TASK_RESULTS_FILE" <<'PY' || exit 1
import sys
from pathlib import Path

with Path(sys.argv[1]).open("x", encoding="utf-8"):
    pass
PY

run_task() {
    runtime="$1"
    task_script="$2"
    log_path="$3"
    timeout_seconds="$4"
    python3 - "$timeout_seconds" "$log_path" "$PROJECT_ROOT" "$runtime" "$task_script" <<'PY'
import subprocess
import sys

timeout, log_path, project_root, runtime, task_script = sys.argv[1:]
with open(log_path, "x", encoding="utf-8") as log:
    try:
        completed = subprocess.run(
            [runtime, task_script],
            cwd=project_root,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=int(timeout),
            check=False,
        )
    except subprocess.TimeoutExpired:
        log.write(f"Execution timed out after {timeout} seconds.\n")
        raise SystemExit(124)
raise SystemExit(completed.returncode)
PY
}

while IFS=$'\t' read -r task_id task_script tool_name tool_version target capability network active side_effects raw_output_path; do
    log_path="$REPORTS_DIR/${task_id}.log"
    start_time=$(date +%s)
    case "$task_script" in
        *.sh) command_identity="sh"; run_task "$command_identity" "$task_script" "$log_path" "$SECURITY_TIMEOUT_SECONDS" ;;
        *.py) command_identity="python3"; run_task "$command_identity" "$task_script" "$log_path" "$SECURITY_TIMEOUT_SECONDS" ;;
        *) command_identity="unsupported"; false ;;
    esac
    exit_code=$?
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    raw_output_status="missing"
    raw_output_sha256=""
    if [ -f "$raw_output_path" ] && [ ! -L "$raw_output_path" ]; then
        raw_output_sha256=$(python3 - "$raw_output_path" <<'PY'
import hashlib
import sys
from pathlib import Path

print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)
        if [ -n "$raw_output_sha256" ]; then raw_output_status="present"; fi
    fi
    printf '%s\n' "$(python3 - "$task_id" "$command_identity" "$task_script" "$tool_name" "$tool_version" "$exit_code" "$duration" "$raw_output_path" "$raw_output_status" "$raw_output_sha256" "$target" "$network" "$active" "$side_effects" "$GATE_RESULT_JSON" <<'PY'
import json
import sys

(
    task_id, command, script, tool, version, exit_code, duration, raw_path,
    raw_status, raw_sha256, target, network, active, side_effects, authorization,
) = sys.argv[1:]
print(json.dumps({
    "task_id": task_id,
    "command_identity": [command, script],
    "tool_and_version": {"name": tool, "declared_version": version},
    "exit_code": int(exit_code),
    "duration_seconds": int(duration),
    "raw_output_path": raw_path,
    "raw_output_status": raw_status,
    "raw_output_sha256": raw_sha256 or None,
    "target": target,
    "network": network == "true",
    "active": active == "true",
    "side_effects": json.loads(side_effects),
    "execution_isolation": "none_trusted_custom_bridge",
    "decision_id": json.loads(authorization)["decision_id"],
}, sort_keys=True))
PY
)" >> "$TASK_RESULTS_FILE"
done < "$TASK_METADATA_FILE"

python3 - "$TASK_RESULTS_FILE" "$RESULTS_JSON" "$GATE_RESULT_JSON" <<'PY'
import json
import sys
from pathlib import Path

tasks = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line]
failed = [task for task in tasks if task["exit_code"] != 0 or task["raw_output_status"] != "present"]
authorization = json.loads(sys.argv[3])
source_revision = authorization.get("current_source_revision")
if not isinstance(source_revision, str) or not source_revision:
    raise SystemExit("[Error] Gate result lacks the current source revision.")
payload = {
    "schema_version": "3.0",
    "status": "completed",
    "phase_status": "completed",
    "result_outcome": "pass" if not failed else "partial",
    "execution_scope": "full",
    "claim_eligibility": "none",
    "source_revision": source_revision,
    "execution_authorization": authorization,
    "tasks": tasks,
    "limitations": [
        "Results report only the executed scope; they do not certify security or infer exploitability.",
        "Raw outputs require normalization before findings are interpreted.",
        "Custom bridge scripts are trusted code. This runner validates declared authorization but does not sandbox or technically enforce bridge side effects.",
    ],
}
with Path(sys.argv[2]).open("x", encoding="utf-8") as output:
    output.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
raise SystemExit(1 if failed else 0)
PY
result=$?
rm -f "$TASK_RESULTS_FILE" "$TASK_METADATA_FILE"
if [ "$result" -ne 0 ]; then
    echo "Security execution completed with incomplete task evidence: results=$RESULTS_JSON"
    exit 1
fi
echo "Security execution completed in the authorized scope: results=$RESULTS_JSON"
