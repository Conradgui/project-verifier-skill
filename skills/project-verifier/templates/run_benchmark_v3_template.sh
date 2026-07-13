#!/bin/bash
# Stage 4 runner: no-call preflight plus receipt-bound, authorized execution.

set -u

RUNNER_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
GATE_VALIDATOR="$RUNNER_DIR/../scripts/validate_gate_v3.py"
TASK_VALIDATOR="$RUNNER_DIR/../scripts/validate_benchmark_task_v3.py"
MODE="${1:-}"
TASK_ID="${2:-}"
TASK_DIR="${BENCHMARK_TASK_DIR:-benchmarks/tasks}"
EXECUTOR="${BENCHMARK_EXECUTOR:-benchmarks/benchmark_executor.sh}"
PROJECT_ROOT="${PROJECT_VERIFIER_PROJECT_ROOT:-.}"
MANIFEST_FILE="${BENCHMARK_MANIFEST_FILE:-project_verification_workbench/verification_manifest_v3.json}"
PROFILE_FILE="${BENCHMARK_PROFILE_FILE:-project_verification_workbench/project_profile.json}"
AUTHORIZATION_FILE="${BENCHMARK_AUTHORIZATION_FILE:-}"
ENVELOPE_FILE="${BENCHMARK_ENVELOPE_FILE:-}"
SOURCE_REVISION="${BENCHMARK_SOURCE_REVISION:-}"

usage() {
    echo "Usage: $0 preflight | pilot TASK_ID | full TASK_ID"
    echo "  preflight      Validate final plan approvals and task contracts without a model, API, tool, Baseline, or executor call."
    echo "  pilot TASK_ID  Run one authorized harness task; pilot evidence remains inconclusive."
    echo "  full TASK_ID   Run one explicitly authorized Benchmark task and write a runner-owned receipt."
}

if [ -z "$MODE" ]; then
    usage
    exit 0
fi

case "$MODE" in
    preflight)
        [ -z "$TASK_ID" ] || { usage; exit 2; }
        ;;
    pilot|full)
        [ -n "$TASK_ID" ] || { usage; exit 2; }
        case "$TASK_ID" in *[!A-Za-z0-9_.-]*|"") echo "[Error] TASK_ID is invalid."; exit 2 ;; esac
        ;;
    *) usage; exit 2 ;;
esac

root_path() {
    python3 - "$PROJECT_ROOT" "$1" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
raw = Path(sys.argv[2])
candidate = raw if raw.is_absolute() else root / raw
if candidate.is_symlink():
    raise SystemExit(f"[Error] Project path must not be a symlink: {raw}")
candidate = candidate.resolve()
try:
    candidate.relative_to(root)
except ValueError:
    raise SystemExit(f"[Error] Project path must stay inside the project root: {raw}")
print(candidate)
PY
}

workbench_output_path() {
    python3 - "$PROJECT_ROOT" "$1" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
workbench = root / "project_verification_workbench"
raw = Path(sys.argv[2])
if ".." in raw.parts:
    raise SystemExit("[Error] Runner output must not contain '..'.")
candidate = raw if raw.is_absolute() else root / raw
if candidate.is_symlink():
    raise SystemExit(f"[Error] Runner output must not be a symlink: {raw}")
candidate = candidate.resolve()
try:
    relative = candidate.relative_to(root)
except ValueError:
    raise SystemExit("[Error] Runner output must stay inside the project root.")
if relative.parts[:1] != ("project_verification_workbench",):
    raise SystemExit("[Error] Runner output must stay inside project_verification_workbench.")
current = root
for part in relative.parts:
    current = current / part
    if current.exists() and current.is_symlink():
        raise SystemExit(f"[Error] Runner output must not use symlinks: {relative}")
if candidate.exists() or candidate.is_symlink():
    raise SystemExit(f"[Error] Runner-owned output already exists: {relative}")
candidate.parent.mkdir(parents=True, exist_ok=True)
print(candidate)
PY
}

PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd -P) || exit 1
TASK_DIR=$(root_path "$TASK_DIR") || exit 1
EXECUTOR=$(root_path "$EXECUTOR") || exit 1
MANIFEST_FILE=$(root_path "$MANIFEST_FILE") || exit 1
PROFILE_FILE=$(root_path "$PROFILE_FILE") || exit 1

[ -d "$TASK_DIR" ] || { echo "[Error] Benchmark task directory is missing."; exit 1; }
[ -f "$EXECUTOR" ] && [ ! -L "$EXECUTOR" ] || { echo "[Error] Benchmark executor must be a regular project file."; exit 1; }
case "$EXECUTOR" in
    "$PROJECT_ROOT"/project_verification_workbench/*)
        echo "[Error] Benchmark executor must not live inside project_verification_workbench."
        exit 1
        ;;
esac
[ -f "$GATE_VALIDATOR" ] && [ -f "$TASK_VALIDATOR" ] || { echo "[Error] Project Verifier validators are unavailable."; exit 1; }

TASK_FILES=()
while IFS= read -r task_file; do
    TASK_FILES[${#TASK_FILES[@]}]="$task_file"
done < <(find "$TASK_DIR" -type f -name 'task_BM_*.json' -print | sort)
[ "${#TASK_FILES[@]}" -gt 0 ] || { echo "[Error] No task_BM_*.json files found."; exit 1; }

validate_task() {
    task_file="$1"
    python3 "$TASK_VALIDATOR" validate --task "$task_file" || return 1
    if [ -z "$SOURCE_REVISION" ]; then
        SOURCE_REVISION=$(python3 "$GATE_VALIDATOR" fingerprint --root "$PROJECT_ROOT") || {
            echo "[Error] Cannot calculate the current source revision."
            return 1
        }
    fi
    python3 "$TASK_VALIDATOR" validate-plan \
        --task "$task_file" \
        --project-root "$PROJECT_ROOT" \
        --manifest "$MANIFEST_FILE" \
        --gate-validator "$GATE_VALIDATOR" \
        --source-revision "$SOURCE_REVISION" || return 1
}

validate_profile() {
    python3 "$GATE_VALIDATOR" profile \
        --manifest "$MANIFEST_FILE" \
        --profile "$PROFILE_FILE" \
        --project-root "$PROJECT_ROOT" || {
            echo "[Error] Confirmed Stage 1 Profile is required."
            return 1
        }
}

if [ "$MODE" = "preflight" ]; then
    for task_file in "${TASK_FILES[@]}"; do
        validate_task "$task_file" || { echo "Preflight failed. No model, API, tool, Baseline, or executor was called."; exit 1; }
    done
    validate_profile || { echo "Preflight failed. No model, API, tool, Baseline, or executor was called."; exit 1; }
    echo "Preflight passed for ${#TASK_FILES[@]} Benchmark task(s). No model, API, tool, Baseline, or executor was called."
    exit 0
fi

TASK_FILE="$TASK_DIR/task_${TASK_ID}.json"
[ -f "$TASK_FILE" ] && [ ! -L "$TASK_FILE" ] || { echo "[Error] Benchmark task file is missing or unsafe: task_${TASK_ID}.json"; exit 1; }
validate_task "$TASK_FILE" || { echo "[Error] Benchmark task preflight failed. No executor was called."; exit 1; }
validate_profile || { echo "[Error] Benchmark task preflight failed. No executor was called."; exit 1; }

for required_name in AUTHORIZATION_FILE ENVELOPE_FILE BENCHMARK_MAX_CALLS BENCHMARK_MAX_RETRIES BENCHMARK_TIMEOUT_SECONDS BENCHMARK_TOOL_RESULT_FILE BENCHMARK_BASELINE_RESULT_FILE BENCHMARK_TELEMETRY_FILE BENCHMARK_RECEIPT_FILE BENCHMARK_LOG_FILE; do
    [ -n "${!required_name:-}" ] || { echo "[Error] Missing execution authorization input: $required_name"; exit 1; }
done

AUTHORIZATION_FILE=$(root_path "$AUTHORIZATION_FILE") || exit 1
ENVELOPE_FILE=$(root_path "$ENVELOPE_FILE") || exit 1
for numeric_name in BENCHMARK_MAX_CALLS BENCHMARK_MAX_RETRIES BENCHMARK_TIMEOUT_SECONDS; do
    case "${!numeric_name}" in ""|*[!0-9]*) echo "[Error] $numeric_name must be a non-negative integer."; exit 1 ;; esac
done
[ "$BENCHMARK_MAX_CALLS" -gt 0 ] && [ "$BENCHMARK_TIMEOUT_SECONDS" -gt 0 ] || { echo "[Error] max calls and timeout must be positive."; exit 1; }

GATE_RESULT=$(python3 "$GATE_VALIDATOR" check \
    --manifest "$MANIFEST_FILE" \
    --receipt "$AUTHORIZATION_FILE" \
    --envelope "$ENVELOPE_FILE" \
    --source-revision "$SOURCE_REVISION" \
    --project-root "$PROJECT_ROOT" \
    --stage stage4 \
    --decision-type benchmark_execution \
    --limit "max_calls=$BENCHMARK_MAX_CALLS" \
    --limit "max_retries=$BENCHMARK_MAX_RETRIES" \
    --limit "timeout_seconds=$BENCHMARK_TIMEOUT_SECONDS") || {
        echo "[Error] Benchmark execution authorization validation failed."; exit 1;
    }
python3 - "$ENVELOPE_FILE" <<'PY'
import json
import sys
from pathlib import Path

envelope = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
scope = envelope.get("scope") if isinstance(envelope, dict) else None
if not isinstance(scope, dict) or "trusted_project_executor_execution" not in scope.get("side_effects", []):
    raise SystemExit("[Error] The execution envelope must explicitly acknowledge trusted_project_executor_execution.")
if "project_verification_workbench" not in scope.get("write_scope", []):
    raise SystemExit("[Error] The execution envelope must authorize project_verification_workbench output writes.")
PY
if [ "$?" -ne 0 ]; then
    exit 1
fi
python3 "$TASK_VALIDATOR" validate-execution-envelope \
    --task "$TASK_FILE" \
    --envelope "$ENVELOPE_FILE" \
    --max-calls "$BENCHMARK_MAX_CALLS" \
    --max-retries "$BENCHMARK_MAX_RETRIES" \
    --timeout-seconds "$BENCHMARK_TIMEOUT_SECONDS" || {
        echo "[Error] Benchmark execution envelope does not match the approved task."; exit 1;
    }

BENCHMARK_TOOL_RESULT_FILE=$(workbench_output_path "$BENCHMARK_TOOL_RESULT_FILE") || exit 1
BENCHMARK_BASELINE_RESULT_FILE=$(workbench_output_path "$BENCHMARK_BASELINE_RESULT_FILE") || exit 1
BENCHMARK_TELEMETRY_FILE=$(workbench_output_path "$BENCHMARK_TELEMETRY_FILE") || exit 1
BENCHMARK_RECEIPT_FILE=$(workbench_output_path "$BENCHMARK_RECEIPT_FILE") || exit 1
BENCHMARK_LOG_FILE=$(workbench_output_path "$BENCHMARK_LOG_FILE") || exit 1
export BENCHMARK_TOOL_RESULT_FILE BENCHMARK_BASELINE_RESULT_FILE BENCHMARK_TELEMETRY_FILE BENCHMARK_RECEIPT_FILE BENCHMARK_LOG_FILE

START_TIME=$(python3 -c 'import time; print(time.monotonic())')
python3 - "$EXECUTOR" "$PROJECT_ROOT" "$MODE" "$TASK_ID" "$BENCHMARK_TIMEOUT_SECONDS" "$BENCHMARK_LOG_FILE" <<'PY'
import subprocess
import sys

executor, project_root, mode, task_id, timeout, log_path = sys.argv[1:]
with open(log_path, "w", encoding="utf-8") as log:
    try:
        completed = subprocess.run([executor, mode, task_id], cwd=project_root, stdout=log, stderr=subprocess.STDOUT, timeout=int(timeout), check=False)
    except subprocess.TimeoutExpired:
        log.write(f"Benchmark execution timed out after {timeout} seconds.\n")
        raise SystemExit(124)
raise SystemExit(completed.returncode)
PY
EXECUTOR_EXIT=$?
DURATION_SECONDS=$(python3 - "$START_TIME" <<'PY'
import sys
import time
print(round(max(0.0, time.monotonic() - float(sys.argv[1])), 6))
PY
)

python3 "$TASK_VALIDATOR" write-receipt \
    --task "$TASK_FILE" \
    --project-root "$PROJECT_ROOT" \
    --mode "$MODE" \
    --exit-code "$EXECUTOR_EXIT" \
    --duration-seconds "$DURATION_SECONDS" \
    --tool-output "$BENCHMARK_TOOL_RESULT_FILE" \
    --baseline-output "$BENCHMARK_BASELINE_RESULT_FILE" \
    --telemetry "$BENCHMARK_TELEMETRY_FILE" \
    --log-path "$BENCHMARK_LOG_FILE" \
    --execution-authorization "$GATE_RESULT" \
    --authorization-receipt "$AUTHORIZATION_FILE" \
    --authorization-envelope "$ENVELOPE_FILE" \
    --output "$BENCHMARK_RECEIPT_FILE" || {
        echo "[Error] Runner could not write its execution receipt."; exit 1;
    }

echo "Authorized Benchmark executor completed: mode=$MODE task=$TASK_ID receipt=$BENCHMARK_RECEIPT_FILE exit_code=$EXECUTOR_EXIT"
exit "$EXECUTOR_EXIT"
