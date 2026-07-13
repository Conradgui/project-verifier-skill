#!/bin/bash
# Stage 2 runner for explicitly authorized Smoke/live E2E fixture paths.

set -u

RUNNER_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TEST_DIR="${QUALITY_TEST_DIR:-tests/quality-e2e}"
REPORTS_DIR="${QUALITY_REPORTS_DIR:-project_verification_workbench/quality-e2e-reports}"
REQUIRED_ENV_FILE="${QUALITY_REQUIRED_ENV_FILE:-$TEST_DIR/required_env.txt}"
REQUIRED_FILES_FILE="${QUALITY_REQUIRED_FILES_FILE:-$TEST_DIR/required_files.txt}"
REQUIRED_COMMANDS_FILE="${QUALITY_REQUIRED_COMMANDS_FILE:-$TEST_DIR/required_commands.txt}"
RESULTS_JSON="${QUALITY_RESULTS_JSON:-project_verification_workbench/stage2_quality_results.json}"
MANIFEST_FILE="${QUALITY_MANIFEST_FILE:-project_verification_workbench/verification_manifest.json}"
AUTHORIZATION_FILE="${QUALITY_AUTHORIZATION_FILE:-}"
ENVELOPE_FILE="${QUALITY_ENVELOPE_FILE:-}"
PROFILE_FILE="${QUALITY_PROFILE_FILE:-project_verification_workbench/project_profile.json}"
SOURCE_REVISION="${QUALITY_SOURCE_REVISION:-}"
GATE_VALIDATOR="${PROJECT_VERIFIER_GATE_VALIDATOR:-$RUNNER_DIR/../scripts/validate_gate.py}"
PROJECT_ROOT="${PROJECT_VERIFIER_PROJECT_ROOT:-.}"
MODE="${1:-}"

usage() {
    echo "Usage: $0 preflight|run"
    echo "  preflight  Validate names, files, commands, runtimes, bounds, and the confirmed Profile without executing paths."
    echo "  run        Execute approved Smoke/live E2E scripts after Profile and decision-envelope validation."
}

if [ -z "$MODE" ]; then
    usage
    exit 0
fi

case "$MODE" in
    preflight|run)
        ;;
    *)
        usage
        exit 2
        ;;
esac

collect_requirements() {
    inline_values="$1"
    requirements_file="$2"
    values="$inline_values"
    if [ -f "$requirements_file" ]; then
        file_values=$(awk 'NF && $1 !~ /^#/' "$requirements_file")
        values="$values $file_values"
    fi
    printf '%s\n' "$values" | tr ',\n' '  '
}

collect_required_env() {
    collect_requirements "${QUALITY_REQUIRED_ENV:-}" "$REQUIRED_ENV_FILE"
}

check_required_env() {
    missing_env=0
    for env_name in $(collect_required_env); do
        case "$env_name" in
            ""|[0-9]*|*[!A-Za-z0-9_]*)
                echo "[Error] Invalid environment variable name: $env_name"
                missing_env=$((missing_env + 1))
                continue
                ;;
        esac
        if [ -z "${!env_name:-}" ]; then
            echo "[Error] Required environment variable is not set: $env_name"
            missing_env=$((missing_env + 1))
        fi
    done
    if [ "$missing_env" -gt 0 ]; then
        echo "Declare only required names in QUALITY_REQUIRED_ENV or $REQUIRED_ENV_FILE."
        return 1
    fi
    return 0
}

check_required_files() {
    missing=0
    for required_file in $(collect_requirements "${QUALITY_REQUIRED_FILES:-}" "$REQUIRED_FILES_FILE"); do
        if [ ! -e "$required_file" ]; then
            echo "[Error] Required file is missing: $required_file"
            missing=$((missing + 1))
        fi
    done
    [ "$missing" -eq 0 ]
}

check_required_commands() {
    missing=0
    for required_command in $(collect_requirements "${QUALITY_REQUIRED_COMMANDS:-}" "$REQUIRED_COMMANDS_FILE"); do
        if ! command -v "$required_command" >/dev/null 2>&1; then
            echo "[Error] Required command is unavailable: $required_command"
            missing=$((missing + 1))
        fi
    done
    [ "$missing" -eq 0 ]
}

normalize_project_directory() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[Error] Python 3 is required to validate project paths."
        return 1
    fi
    python3 - "$PROJECT_ROOT" "$1" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
raw_path = sys.argv[2]
if "\n" in raw_path or "\r" in raw_path:
    raise SystemExit("[Error] Project path must not contain a newline.")
candidate = Path(raw_path)
if not candidate.is_absolute():
    candidate = root / candidate
if candidate.is_symlink():
    raise SystemExit(f"[Error] Project path must not be a symlink: {raw_path}")
candidate = candidate.resolve()
try:
    candidate.relative_to(root)
except ValueError:
    raise SystemExit(f"[Error] Project path must stay inside the project root: {raw_path}")
if not candidate.is_dir():
    raise SystemExit(f"[Error] Project directory is missing: {raw_path}")
print(candidate)
PY
}

normalize_workbench_output_path() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[Error] Python 3 is required to validate workbench output paths."
        return 1
    fi
    python3 - "$PROJECT_ROOT" "$1" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
workbench = root / "project_verification_workbench"
if workbench.is_symlink():
    raise SystemExit("[Error] The project workbench must not be a symlink.")
workbench = workbench.resolve()
raw_path = sys.argv[2]
if "\n" in raw_path or "\r" in raw_path:
    raise SystemExit("[Error] Output path must not contain a newline.")
candidate = Path(raw_path)
if not candidate.is_absolute():
    candidate = root / candidate
if candidate.is_symlink():
    raise SystemExit(f"[Error] Output path must not be a symlink: {raw_path}")
candidate = candidate.resolve()
try:
    candidate.relative_to(workbench)
except ValueError:
    raise SystemExit(f"[Error] Output path must stay inside project_verification_workbench: {raw_path}")
print(candidate)
PY
}

check_output_paths() {
    REPORTS_DIR=$(normalize_workbench_output_path "$REPORTS_DIR") || return 1
    RESULTS_JSON=$(normalize_workbench_output_path "$RESULTS_JSON") || return 1
}

nonnegative_int() {
    value="$1"
    case "$value" in
        ""|*[!0-9]*) echo 0 ;;
        *) echo "$value" ;;
    esac
}

json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

check_execution_bounds() {
    invalid=0
    for bound_name in QUALITY_MAX_PATHS QUALITY_MAX_CALLS_PER_PATH QUALITY_MAX_RETRIES QUALITY_TIMEOUT_SECONDS; do
        bound_value="${!bound_name:-}"
        if [ -z "$bound_value" ] || [[ "$bound_value" == *[!0-9]* ]]; then
            echo "[Error] Invalid execution bound: $bound_name must be a non-negative integer."
            invalid=1
        fi
    done
    if [ "$invalid" -ne 0 ]; then
        return 1
    fi
    if [ "$QUALITY_MAX_PATHS" -lt 1 ]; then
        echo "[Error] Invalid execution bound: QUALITY_MAX_PATHS must be at least 1."
        return 1
    fi
    if [ "$QUALITY_TIMEOUT_SECONDS" -lt 1 ]; then
        echo "[Error] Invalid execution bound: QUALITY_TIMEOUT_SECONDS must be at least 1."
        return 1
    fi
    if [ "${#SCRIPTS[@]}" -gt "$QUALITY_MAX_PATHS" ]; then
        echo "[Error] Found ${#SCRIPTS[@]} scripts, exceeding approved max_paths=$QUALITY_MAX_PATHS."
        return 1
    fi
    return 0
}

check_profile_handoff() {
    for required_path in "$MANIFEST_FILE" "$PROFILE_FILE" "$GATE_VALIDATOR"; do
        if [ ! -f "$required_path" ]; then
            echo "[Error] Profile handoff file is missing: $required_path"
            return 1
        fi
    done
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[Error] Python 3 is required to validate the Profile handoff."
        return 1
    fi
    python3 "$GATE_VALIDATOR" profile \
        --manifest "$MANIFEST_FILE" \
        --profile "$PROFILE_FILE" \
        --project-root "$PROJECT_ROOT" || {
            echo "[Error] Profile handoff validation failed."
            return 1
        }
    echo "Profile handoff passed."
    return 0
}

check_execution_authorization() {
    for required_name in AUTHORIZATION_FILE ENVELOPE_FILE SOURCE_REVISION QUALITY_MAX_PATHS QUALITY_MAX_CALLS_PER_PATH QUALITY_MAX_RETRIES QUALITY_TIMEOUT_SECONDS; do
        required_value="${!required_name:-}"
        if [ -z "$required_value" ]; then
            echo "[Error] Missing execution authorization input: $required_name"
            return 1
        fi
    done
    for required_path in "$MANIFEST_FILE" "$AUTHORIZATION_FILE" "$ENVELOPE_FILE" "$PROFILE_FILE" "$GATE_VALIDATOR"; do
        if [ ! -f "$required_path" ]; then
            echo "[Error] Execution authorization file is missing: $required_path"
            return 1
        fi
    done
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[Error] Python 3 is required to validate the execution authorization."
        return 1
    fi
    GATE_RESULT_JSON=$(python3 "$GATE_VALIDATOR" check \
        --manifest "$MANIFEST_FILE" \
        --receipt "$AUTHORIZATION_FILE" \
        --envelope "$ENVELOPE_FILE" \
        --source-revision "$SOURCE_REVISION" \
        --project-root "$PROJECT_ROOT" \
        --stage stage2 \
        --decision-type live_e2e \
        --limit "max_paths=$QUALITY_MAX_PATHS" \
        --limit "max_calls_per_path=$QUALITY_MAX_CALLS_PER_PATH" \
        --limit "max_retries=$QUALITY_MAX_RETRIES" \
        --limit "timeout_seconds=$QUALITY_TIMEOUT_SECONDS") || {
            echo "[Error] Execution authorization validation failed."
            return 1
        }
    check_authorized_scripts || return 1
    return 0
}

check_authorized_scripts() {
    python3 - "$PROJECT_ROOT" "$TEST_DIR" "$ENVELOPE_FILE" "${SCRIPTS[@]}" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
test_dir = Path(sys.argv[2]).resolve()
envelope = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
allowed = envelope.get("scope", {}).get("path_ids")
if not isinstance(allowed, list) or not all(isinstance(item, str) and item for item in allowed):
    raise SystemExit("[Error] Authorization envelope path_ids are invalid.")

actual = []
for raw_path in sys.argv[4:]:
    path = Path(raw_path)
    if path.is_symlink():
        raise SystemExit(f"[Error] Quality script must not be a symlink: {raw_path}")
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
        resolved.relative_to(test_dir)
    except ValueError:
        raise SystemExit(f"[Error] Quality script is outside the approved project test directory: {raw_path}")
    script_id = resolved.stem.removeprefix("quality_")
    if not script_id or script_id in actual:
        raise SystemExit(f"[Error] Quality script path ID is invalid or duplicated: {raw_path}")
    actual.append(script_id)

if set(actual) != set(allowed) or len(actual) != len(allowed):
    raise SystemExit("[Error] Authorized path IDs do not exactly match discovered quality scripts.")
PY
}

check_runtime() {
    script="$1"
    case "$script" in
        *.py)
            command -v python3 >/dev/null 2>&1 || { echo "Missing Python runtime for $script."; return 127; }
            ;;
        *.sh)
            command -v sh >/dev/null 2>&1 || { echo "Missing shell runtime for $script."; return 127; }
            ;;
        *.ts)
            if ! command -v tsx >/dev/null 2>&1 && ! command -v ts-node >/dev/null 2>&1 && ! command -v deno >/dev/null 2>&1; then
                echo "Missing TypeScript runtime for $script. Provide tsx, ts-node, or deno, or use .py/.sh."
                return 127
            fi
            ;;
        *)
            echo "Unsupported quality script type: $script"
            return 2
            ;;
    esac
    return 0
}

TEST_DIR=$(normalize_project_directory "$TEST_DIR") || exit 1

if [ ! -d "$TEST_DIR" ]; then
    echo "[Error] No quality E2E test directory found at $TEST_DIR."
    exit 1
fi

SCRIPTS=()
while IFS= read -r script; do
    SCRIPTS[${#SCRIPTS[@]}]="$script"
done < <(find "$TEST_DIR" -type f \( -name "quality_P0_*.py" -o -name "quality_P0_*.ts" -o -name "quality_P0_*.sh" \) | sort)

if [ "${#SCRIPTS[@]}" -eq 0 ]; then
    echo "[Error] No quality scripts matching 'quality_P0_*' found in $TEST_DIR."
    exit 1
fi

perform_preflight() {
    failed=0
    check_required_env || failed=1
    check_required_files || failed=1
    check_required_commands || failed=1
    check_output_paths || failed=1
    check_execution_bounds || failed=1
    for script in "${SCRIPTS[@]}"; do
        check_runtime "$script" || failed=1
    done
    check_profile_handoff || failed=1
    if [ "$failed" -ne 0 ]; then
        echo "Preflight failed. No Smoke/live scripts were executed."
        return 1
    fi
    echo "Preflight passed for ${#SCRIPTS[@]} quality script(s). No Smoke/live scripts were executed."
    return 0
}

if [ "$MODE" = "preflight" ]; then
    perform_preflight
    exit $?
fi

perform_preflight || exit 1
check_execution_authorization || exit 1
mkdir -p "$REPORTS_DIR"
mkdir -p "$(dirname "$RESULTS_JSON")"
RESULTS_TMP="$REPORTS_DIR/.quality_results.jsonl"
: > "$RESULTS_TMP"

run_script() {
    script="$1"
    log_file="$2"
    timeout_seconds="$3"
    case "$script" in
        *.py) runtime="python3" ;;
        *.sh) runtime="sh" ;;
        *.ts)
            if command -v tsx >/dev/null 2>&1; then runtime="tsx"
            elif command -v ts-node >/dev/null 2>&1; then runtime="ts-node"
            elif command -v deno >/dev/null 2>&1; then runtime="deno"
            else echo "Missing TypeScript runtime for $script."; return 127
            fi
            ;;
        *) echo "Unsupported quality script type: $script"; return 2 ;;
    esac
    if [ "$runtime" = "deno" ]; then set -- deno run "$script"; else set -- "$runtime" "$script"; fi
    python3 - "$timeout_seconds" "$log_file" "$PROJECT_ROOT" "$@" <<'PY'
import subprocess
import sys

timeout = int(sys.argv[1])
log_path = sys.argv[2]
project_root = sys.argv[3]
command = sys.argv[4:]
with open(log_path, "w", encoding="utf-8") as log:
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log.write(f"Execution timed out after {timeout} seconds.\n")
        raise SystemExit(124)
raise SystemExit(completed.returncode)
PY
}

PASSED_COUNT=0
FAILED_COUNT=0
INCONCLUSIVE_COUNT=0
TOTAL_COUNT=0

for script in "${SCRIPTS[@]}"; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    script_name=$(basename "$script")
    log_file="$REPORTS_DIR/${script_name%.*}.log"
    telemetry_file="$REPORTS_DIR/${script_name%.*}.telemetry.json"
    rm -f "$telemetry_file"
    start_time=$(date +%s)
    run_script "$script" "$log_file" "$QUALITY_TIMEOUT_SECONDS"
    exit_code=$?
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))
    telemetry_status="missing"
    external_calls_actual="null"
    retries_actual="null"
    side_effects="[]"
    if [ -f "$telemetry_file" ]; then
        telemetry_values=$(python3 - "$telemetry_file" "$QUALITY_MAX_CALLS_PER_PATH" "$QUALITY_MAX_RETRIES" <<'PY'
import json
import sys

try:
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    calls = payload["external_calls_actual"]
    retries = payload["retries_actual"]
    side_effects = payload["side_effects"]
    if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0:
        raise ValueError("external_calls_actual must be a non-negative integer")
    if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
        raise ValueError("retries_actual must be a non-negative integer")
    if not isinstance(side_effects, list):
        raise ValueError("side_effects must be a list")
    if calls > int(sys.argv[2]) or retries > int(sys.argv[3]):
        raise ValueError("actual execution exceeded approved limits")
except Exception as exc:
    print(f"invalid\t{exc}")
    raise SystemExit(1)
print(f"valid\t{calls}\t{retries}\t{json.dumps(side_effects, separators=(',', ':'))}")
PY
        )
        if [ "$?" -eq 0 ]; then
            telemetry_status=$(printf '%s' "$telemetry_values" | cut -f1)
            external_calls_actual=$(printf '%s' "$telemetry_values" | cut -f2)
            retries_actual=$(printf '%s' "$telemetry_values" | cut -f3)
            side_effects=$(printf '%s' "$telemetry_values" | cut -f4-)
        else
            telemetry_status="invalid"
        fi
    fi
    if [ "$telemetry_status" != "valid" ]; then
        failure_stage='"telemetry_validation"'
        errors="[\"Missing or invalid telemetry: $(json_escape "$telemetry_file")\"]"
        INCONCLUSIVE_COUNT=$((INCONCLUSIVE_COUNT + 1))
    elif [ "$exit_code" -eq 0 ]; then
        failure_stage="null"
        errors="[]"
        PASSED_COUNT=$((PASSED_COUNT + 1))
    else
        failure_stage='"script_execution"'
        errors="[\"See log: $(json_escape "$log_file")\"]"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
    path_id="${script_name%.*}"
    path_id="${path_id#quality_}"
    printf '{"path_id":"%s","path_name":"%s","exit_code":%s,"duration_seconds":%s,"log_path":"%s","failure_stage":%s,"telemetry_status":"%s","telemetry_provenance":{"exit_code":"wrapper_observed","duration_seconds":"wrapper_observed","log_path":"wrapper_observed","external_calls_actual":"script_self_reported","retries_actual":"script_self_reported","side_effects":"script_self_reported"},"external_calls_actual":%s,"retries_actual":%s,"side_effects":%s,"errors":%s}\n' \
        "$(json_escape "$path_id")" "$(json_escape "$path_id")" "$exit_code" "$elapsed" "$(json_escape "$log_file")" "$failure_stage" "$telemetry_status" "$external_calls_actual" "$retries_actual" "$side_effects" "$errors" >> "$RESULTS_TMP"
done

PHASE_STATUS="completed"
EXECUTION_SCOPE="full"
if [ "$INCONCLUSIVE_COUNT" -gt 0 ]; then
    RESULT_OUTCOME="inconclusive"
    CLAIM_ELIGIBILITY="none"
elif [ "$FAILED_COUNT" -eq 0 ]; then
    RESULT_OUTCOME="pass"
    CLAIM_ELIGIBILITY="full"
elif [ "$PASSED_COUNT" -eq 0 ]; then
    RESULT_OUTCOME="fail"
    CLAIM_ELIGIBILITY="full"
else
    RESULT_OUTCOME="partial"
    CLAIM_ELIGIBILITY="full"
fi

required_env_json=""
for env_name in $(collect_required_env); do
    [ -n "$required_env_json" ] && required_env_json="$required_env_json,"
    required_env_json="$required_env_json\"$env_name\""
done

{
    echo "{"
    echo '  "schema_version": "3.0",'
    echo "  \"status\": \"$PHASE_STATUS\","
    echo "  \"phase_status\": \"$PHASE_STATUS\","
    echo "  \"result_outcome\": \"$RESULT_OUTCOME\","
    echo "  \"execution_scope\": \"$EXECUTION_SCOPE\","
    echo "  \"claim_eligibility\": \"$CLAIM_ELIGIBILITY\","
    echo "  \"required_env\": [$required_env_json],"
    echo '  "missing_env": [],'
    echo '  "backend_dependencies": [],'
    echo "  \"execution_authorization\": $GATE_RESULT_JSON,"
    echo "  \"execution_bounds\": {\"max_paths\": $QUALITY_MAX_PATHS, \"max_calls_per_path\": $QUALITY_MAX_CALLS_PER_PATH, \"max_retries\": $QUALITY_MAX_RETRIES, \"timeout_seconds\": $QUALITY_TIMEOUT_SECONDS},"
    echo '  "telemetry_provenance": {"wrapper_observed": ["exit_code", "duration_seconds", "log_path"], "script_self_reported": ["external_calls_actual", "retries_actual", "side_effects"]},'
    echo '  "paths": ['
    first=1
    while IFS= read -r result_line; do
        [ "$first" -eq 0 ] && echo ','
        printf '    %s' "$result_line"
        first=0
    done < "$RESULTS_TMP"
    echo
    echo '  ],'
    echo '  "blockers": [],'
    echo '  "recovery_conditions": []'
    echo "}"
} > "$RESULTS_JSON"
rm -f "$RESULTS_TMP"

echo "Quality Smoke/live E2E completed: passed=$PASSED_COUNT failed=$FAILED_COUNT inconclusive=$INCONCLUSIVE_COUNT results=$RESULTS_JSON"

if [ "$FAILED_COUNT" -gt 0 ] || [ "$INCONCLUSIVE_COUNT" -gt 0 ]; then
    exit 1
fi
exit 0
