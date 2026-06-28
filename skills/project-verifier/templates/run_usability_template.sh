#!/bin/bash
# USABILITY TEST RUNNER TEMPLATE
# Runs isolated E2E/live tests for P0 execution paths.

set -u

TEST_DIR="${TEST_DIR:-tests/usability}"
REPORTS_DIR="${REPORTS_DIR:-tests/usability/reports}"
REQUIRED_ENV_FILE="${USABILITY_REQUIRED_ENV_FILE:-$TEST_DIR/required_env.txt}"
REQUIRED_FILES_FILE="${USABILITY_REQUIRED_FILES_FILE:-$TEST_DIR/required_files.txt}"
REQUIRED_COMMANDS_FILE="${USABILITY_REQUIRED_COMMANDS_FILE:-$TEST_DIR/required_commands.txt}"
RESULTS_JSON="${USABILITY_RESULTS_JSON:-project_verification_workbench/phase4_usability_results.json}"
MODE="${1:-}"

usage() {
    echo "Usage: $0 preflight|run"
    echo "  preflight  Check environment names, files, and runtimes without executing live tests."
    echo "  run        Execute approved usability scripts after preflight."
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

collect_required_env() {
    required=""
    if [ -n "${USABILITY_REQUIRED_ENV:-}" ]; then
        required="$USABILITY_REQUIRED_ENV"
    fi
    if [ -f "$REQUIRED_ENV_FILE" ]; then
        file_values=$(awk 'NF && $1 !~ /^#/' "$REQUIRED_ENV_FILE")
        required="$required $file_values"
    fi
    printf '%s\n' "$required" | tr ',\n' '  '
}

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

check_required_env() {
    missing_env=0
    for env_name in $(collect_required_env); do
        case "$env_name" in
            ""|[0-9]*|*[!A-Za-z0-9_]*)
                echo "❌ [Error] Invalid environment variable name: $env_name"
                missing_env=$((missing_env + 1))
                continue
                ;;
        esac
        if [ -z "${!env_name:-}" ]; then
            echo "❌ [Error] Required environment variable is not set: $env_name"
            missing_env=$((missing_env + 1))
        fi
    done
    if [ "$missing_env" -gt 0 ]; then
        echo "Declare only truly required variable names in USABILITY_REQUIRED_ENV or $REQUIRED_ENV_FILE."
        return 1
    fi
    return 0
}

nonnegative_int() {
    value="$1"
    case "$value" in
        ""|*[!0-9]*)
            echo 0
            ;;
        *)
            echo "$value"
            ;;
    esac
}

json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

check_required_files() {
    missing=0
    for required_file in $(collect_requirements "${USABILITY_REQUIRED_FILES:-}" "$REQUIRED_FILES_FILE"); do
        if [ ! -e "$required_file" ]; then
            echo "❌ [Error] Required file is missing: $required_file"
            missing=$((missing + 1))
        fi
    done
    [ "$missing" -eq 0 ]
}

check_required_commands() {
    missing=0
    for required_command in $(collect_requirements "${USABILITY_REQUIRED_COMMANDS:-}" "$REQUIRED_COMMANDS_FILE"); do
        if ! command -v "$required_command" >/dev/null 2>&1; then
            echo "❌ [Error] Required command is unavailable: $required_command"
            missing=$((missing + 1))
        fi
    done
    [ "$missing" -eq 0 ]
}

check_execution_bounds() {
    invalid=0
    for bound_name in USABILITY_MAX_PATHS USABILITY_MAX_CALLS_PER_PATH USABILITY_MAX_RETRIES USABILITY_TIMEOUT_SECONDS; do
        bound_value="${!bound_name:-}"
        if [ -n "$bound_value" ]; then
            case "$bound_value" in
                *[!0-9]*)
                    echo "❌ [Error] Invalid execution bound: $bound_name must be a non-negative integer."
                    invalid=1
                    ;;
            esac
        fi
    done
    if [ "$invalid" -ne 0 ]; then
        return 1
    fi
    if [ -n "${USABILITY_MAX_PATHS:-}" ] && [ "${USABILITY_MAX_PATHS}" -lt 1 ]; then
        echo "❌ [Error] Invalid execution bound: USABILITY_MAX_PATHS must be at least 1."
        return 1
    fi
    if [ -n "${USABILITY_TIMEOUT_SECONDS:-}" ] && [ "${USABILITY_TIMEOUT_SECONDS}" -lt 1 ]; then
        echo "❌ [Error] Invalid execution bound: USABILITY_TIMEOUT_SECONDS must be at least 1."
        return 1
    fi
    if [ -n "${USABILITY_MAX_PATHS:-}" ] && [ "${#SCRIPTS[@]}" -gt "${USABILITY_MAX_PATHS}" ]; then
        echo "❌ [Error] Found ${#SCRIPTS[@]} scripts, exceeding approved max_paths=${USABILITY_MAX_PATHS}."
        return 1
    fi
    return 0
}

if [ ! -d "$TEST_DIR" ]; then
    echo "❌ [Error] No usability test directory found at $TEST_DIR."
    exit 1
fi

SCRIPTS=()
while IFS= read -r script; do
    SCRIPTS[${#SCRIPTS[@]}]="$script"
done < <(find "$TEST_DIR" -type f \( -name "usability_P0_*.py" -o -name "usability_P0_*.ts" -o -name "usability_P0_*.sh" \) | sort)

if [ "${#SCRIPTS[@]}" -eq 0 ]; then
    echo "❌ [Error] No usability scripts matching 'usability_P0_*' found in $TEST_DIR."
    exit 1
fi

check_runtime() {
    script="$1"
    case "$script" in
        *.py)
            command -v python3 >/dev/null 2>&1 || {
                echo "Missing Python runtime for $script."
                return 127
            }
            ;;
        *.sh)
            command -v sh >/dev/null 2>&1 || {
                echo "Missing shell runtime for $script."
                return 127
            }
            ;;
        *.ts)
            if ! command -v tsx >/dev/null 2>&1 \
                && ! command -v ts-node >/dev/null 2>&1 \
                && ! command -v deno >/dev/null 2>&1; then
                echo "Missing TypeScript runtime for $script. Install/provide tsx, ts-node, or deno, or use .py/.sh."
                return 127
            fi
            ;;
        *)
            echo "Unsupported usability script type: $script"
            return 2
            ;;
    esac
    return 0
}

perform_preflight() {
    failed=0
    check_required_env || failed=1
    check_required_files || failed=1
    check_required_commands || failed=1
    check_execution_bounds || failed=1
    for script in "${SCRIPTS[@]}"; do
        check_runtime "$script" || failed=1
    done
    if [ "$failed" -ne 0 ]; then
        echo "Preflight failed. No usability scripts were executed."
        return 1
    fi
    echo "Preflight passed for ${#SCRIPTS[@]} usability script(s). No live scripts were executed."
    return 0
}

if [ "$MODE" = "preflight" ]; then
    perform_preflight
    exit $?
fi

perform_preflight || exit 1
mkdir -p "$REPORTS_DIR"
mkdir -p "$(dirname "$RESULTS_JSON")"
RESULTS_TMP="$REPORTS_DIR/.usability_results.jsonl"
: > "$RESULTS_TMP"

echo "=============================================="
echo "Starting Approved Usability Tests..."
echo "=============================================="

run_script() {
    script="$1"
    case "$script" in
        *.py)
            python3 "$script"
            ;;
        *.sh)
            sh "$script"
            ;;
        *.ts)
            if command -v tsx >/dev/null 2>&1; then
                tsx "$script"
            elif command -v ts-node >/dev/null 2>&1; then
                ts-node "$script"
            elif command -v deno >/dev/null 2>&1; then
                deno run "$script"
            else
                echo "Missing TypeScript runtime for $script. Install/provide tsx, ts-node, or deno, or use .py/.sh."
                return 127
            fi
            ;;
        *)
            echo "Unsupported usability script type: $script"
            return 2
            ;;
    esac
}

PASSED_COUNT=0
FAILED_COUNT=0
TOTAL_COUNT=0

for script in "${SCRIPTS[@]}"; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    script_name=$(basename "$script")
    log_file="$REPORTS_DIR/${script_name%.*}.log"

    echo -n "Running $script_name... "
    start_time=$(date +%s)

    run_script "$script" > "$log_file" 2>&1
    exit_code=$?
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))
    if [ "$exit_code" -eq 0 ]; then
        failure_stage="null"
        errors="[]"
        echo "✅ Passed (Took ${elapsed}s)"
        PASSED_COUNT=$((PASSED_COUNT + 1))
    else
        failure_stage='"script_execution"'
        errors="[]"
        echo "❌ Failed! (See details in $log_file)"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
    path_id="${script_name%.*}"
    path_id="${path_id#usability_}"
    escaped_path_id=$(json_escape "$path_id")
    escaped_log_file=$(json_escape "$log_file")
    if [ "$exit_code" -ne 0 ]; then
        errors="[\"See log: $escaped_log_file\"]"
    fi
    printf '{"path_id":"%s","path_name":"%s","exit_code":%s,"duration_seconds":%s,"log_path":"%s","failure_stage":%s,"errors":%s}\n' \
        "$escaped_path_id" "$escaped_path_id" "$exit_code" "$elapsed" "$escaped_log_file" "$failure_stage" "$errors" >> "$RESULTS_TMP"
done

if [ "$FAILED_COUNT" -gt 0 ]; then
    RESULT_STATUS="failed"
else
    RESULT_STATUS="completed"
fi

required_env_json=""
for env_name in $(collect_required_env); do
    if [ -n "$required_env_json" ]; then
        required_env_json="$required_env_json,"
    fi
    required_env_json="$required_env_json\"$env_name\""
done

max_calls_per_path=$(nonnegative_int "${USABILITY_MAX_CALLS_PER_PATH:-0}")
max_retries=$(nonnegative_int "${USABILITY_MAX_RETRIES:-0}")
timeout_seconds=$(nonnegative_int "${USABILITY_TIMEOUT_SECONDS:-0}")
max_paths=$(nonnegative_int "${USABILITY_MAX_PATHS:-$TOTAL_COUNT}")

{
    echo "{"
    echo '  "schema_version": "2.0",'
    echo "  \"status\": \"$RESULT_STATUS\","
    echo "  \"required_env\": [$required_env_json],"
    echo '  "missing_env": [],'
    echo '  "backend_dependencies": [],'
    echo '  "execution_authorization": true,'
    echo "  \"execution_bounds\": {\"max_paths\": $max_paths, \"max_calls_per_path\": $max_calls_per_path, \"max_retries\": $max_retries, \"timeout_seconds\": $timeout_seconds},"
    echo '  "paths": ['
    first=1
    while IFS= read -r result_line; do
        if [ "$first" -eq 0 ]; then
            echo ','
        fi
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

echo "=============================================="
echo "Usability Tests Completed"
echo "Passed: $PASSED_COUNT / $TOTAL_COUNT"
echo "Failed: $FAILED_COUNT / $TOTAL_COUNT"
echo "Results: $RESULTS_JSON"
echo "=============================================="

if [ "$FAILED_COUNT" -gt 0 ]; then
    exit 1
fi
exit 0
