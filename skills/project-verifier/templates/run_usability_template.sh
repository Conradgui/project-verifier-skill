#!/bin/bash
# USABILITY TEST RUNNER TEMPLATE
# Runs isolated E2E/live tests for P0 execution paths.

set -u

TEST_DIR="${TEST_DIR:-tests/usability}"
REPORTS_DIR="${REPORTS_DIR:-tests/usability/reports}"
REQUIRED_ENV_FILE="${USABILITY_REQUIRED_ENV_FILE:-$TEST_DIR/required_env.txt}"
mkdir -p "$REPORTS_DIR"

echo "=============================================="
echo "Starting Usability Tests..."
echo "=============================================="

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

missing_env=0
for env_name in $(collect_required_env); do
    if [ -z "${!env_name:-}" ]; then
        echo "❌ [Error] Required environment variable is not set: $env_name"
        missing_env=$((missing_env + 1))
    fi
done

if [ "$missing_env" -gt 0 ]; then
    echo "Declare only truly required variables in USABILITY_REQUIRED_ENV or $REQUIRED_ENV_FILE."
    exit 1
fi

if [ ! -d "$TEST_DIR" ]; then
    echo "ℹ️  No usability test directory found at $TEST_DIR."
    exit 0
fi

SCRIPTS=$(find "$TEST_DIR" -type f \( -name "usability_P0_*.py" -o -name "usability_P0_*.ts" -o -name "usability_P0_*.sh" \) | sort)

if [ -z "$SCRIPTS" ]; then
    echo "ℹ️  No usability scripts matching 'usability_P0_*' found in $TEST_DIR."
    exit 0
fi

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
                deno run --allow-all "$script"
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

for script in $SCRIPTS; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    script_name=$(basename "$script")
    log_file="$REPORTS_DIR/${script_name%.*}.log"

    echo -n "Running $script_name... "
    start_time=$(date +%s)

    if run_script "$script" > "$log_file" 2>&1; then
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        echo "✅ Passed (Took ${elapsed}s)"
        PASSED_COUNT=$((PASSED_COUNT + 1))
    else
        echo "❌ Failed! (See details in $log_file)"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

echo "=============================================="
echo "Usability Tests Completed"
echo "Passed: $PASSED_COUNT / $TOTAL_COUNT"
echo "Failed: $FAILED_COUNT / $TOTAL_COUNT"
echo "=============================================="

if [ "$FAILED_COUNT" -gt 0 ]; then
    exit 1
fi
exit 0
