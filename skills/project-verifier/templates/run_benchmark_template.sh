#!/bin/bash
# AUTHORIZED BENCHMARK ORCHESTRATOR TEMPLATE

set -u

MODE="${1:-}"
TASK_ID="${2:-}"
TASK_DIR="${BENCHMARK_TASK_DIR:-benchmarks/tasks}"
EXECUTOR="${BENCHMARK_EXECUTOR:-benchmarks/benchmark_executor.sh}"
MANIFEST_FILE="${BENCHMARK_MANIFEST_FILE:-project_verification_workbench/verification_manifest.json}"
AUTHORIZATION_FILE="${BENCHMARK_AUTHORIZATION_FILE:-}"
PLAN_FILE="${BENCHMARK_PLAN_FILE:-project_verification_workbench/phase5_benchmark_plan.md}"
SOURCE_REVISION="${BENCHMARK_SOURCE_REVISION:-}"
GATE_VALIDATOR="${PROJECT_VERIFIER_GATE_VALIDATOR:-project_verification_workbench/tools/validate_gate.py}"
PROJECT_ROOT="${PROJECT_VERIFIER_PROJECT_ROOT:-.}"

usage() {
    echo "Usage: $0 preflight | pilot <task_id> | full"
}

case "$MODE" in
    preflight|full)
        ;;
    pilot)
        if [ -z "$TASK_ID" ]; then
            usage
            exit 2
        fi
        ;;
    *)
        usage
        exit 2
        ;;
esac

preflight() {
    failed=0
    if ! command -v python3 >/dev/null 2>&1; then
        echo "❌ [Error] Python 3 is required for schema and authorization validation."
        failed=1
    fi
    if [ ! -d "$TASK_DIR" ]; then
        echo "❌ [Error] Benchmark task directory is missing: $TASK_DIR"
        failed=1
    fi
    if [ ! -x "$EXECUTOR" ]; then
        echo "❌ [Error] Benchmark executor is missing or not executable: $EXECUTOR"
        failed=1
    fi
    if [ "$failed" -ne 0 ]; then
        echo "Preflight failed. No benchmark task was executed."
        return 1
    fi
    if ! python3 - "$TASK_DIR" <<'PY'
import json
import pathlib
import sys

task_files = sorted(pathlib.Path(sys.argv[1]).glob("task_BM_*.json"))
if not task_files:
    raise SystemExit("No task_BM_*.json files found")
for path in task_files:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload.get("task_id") or not isinstance(payload.get("metrics"), list):
        raise SystemExit(f"Invalid benchmark task schema: {path}")
print(f"Validated {len(task_files)} benchmark task definition(s).")
PY
    then
        echo "Preflight failed. No benchmark task was executed."
        return 1
    fi
    echo "Preflight passed. No model, API, tool, or baseline task was executed."
    return 0
}

preflight || exit 1
if [ "$MODE" = "preflight" ]; then
    exit 0
fi

for required_name in AUTHORIZATION_FILE SOURCE_REVISION BENCHMARK_MAX_CALLS BENCHMARK_MAX_RETRIES BENCHMARK_TIMEOUT_SECONDS; do
    required_value="${!required_name:-}"
    if [ -z "$required_value" ]; then
        echo "❌ [Error] Missing benchmark authorization input: $required_name"
        exit 1
    fi
done

for required_path in "$MANIFEST_FILE" "$AUTHORIZATION_FILE" "$PLAN_FILE" "$GATE_VALIDATOR"; do
    if [ ! -f "$required_path" ]; then
        echo "❌ [Error] Benchmark authorization file is missing: $required_path"
        exit 1
    fi
done

GATE_RESULT=$(python3 "$GATE_VALIDATOR" check \
    --manifest "$MANIFEST_FILE" \
    --receipt "$AUTHORIZATION_FILE" \
    --proposal "$PLAN_FILE" \
    --source-revision "$SOURCE_REVISION" \
    --project-root "$PROJECT_ROOT" \
    --phase phase5 \
    --decision-type benchmark_execution \
    --limit "max_calls=$BENCHMARK_MAX_CALLS" \
    --limit "max_retries=$BENCHMARK_MAX_RETRIES" \
    --limit "timeout_seconds=$BENCHMARK_TIMEOUT_SECONDS") || {
        echo "❌ [Error] Benchmark authorization validation failed."
        exit 1
    }

echo "Authorization validated: $GATE_RESULT"
python3 - "$BENCHMARK_TIMEOUT_SECONDS" "$EXECUTOR" "$MODE" "$TASK_ID" <<'PY'
import subprocess
import sys

timeout = int(sys.argv[1])
command = [sys.argv[2], sys.argv[3]]
if sys.argv[4]:
    command.append(sys.argv[4])
try:
    completed = subprocess.run(command, timeout=timeout, check=False)
except subprocess.TimeoutExpired:
    print(f"Benchmark execution timed out after {timeout} seconds.")
    raise SystemExit(124)
raise SystemExit(completed.returncode)
PY
