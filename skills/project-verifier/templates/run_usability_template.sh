#!/bin/bash
# USABILITY TEST RUNNER TEMPLATE
# Runs isolated E2E live tests for P0 execution paths.

set -e

# Configurable paths
TEST_DIR="tests/usability"
REPORTS_DIR="tests/usability/reports"
mkdir -p "$REPORTS_DIR"

echo "=============================================="
echo "Starting Live API Usability Tests..."
echo "=============================================="

# 1. Environment Guard Check
MISSING_KEYS=0
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  [Warning] OPENAI_API_KEY is not set in environment."
    MISSING_KEYS=$((MISSING_KEYS+1))
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  [Warning] ANTHROPIC_API_KEY is not set in environment."
    MISSING_KEYS=$((MISSING_KEYS+1))
fi

if [ $MISSING_KEYS -eq 2 ]; then
    echo "❌  [Error] No API keys detected in environment variables."
    echo "    Please export OPENAI_API_KEY or ANTHROPIC_API_KEY before running."
    exit 1
fi

PASSED_COUNT=0
FAILED_COUNT=0
TOTAL_COUNT=0

# 2. Find and Run Usability Scripts
# Example script file naming matches: usability_P0_*.py
SCRIPTS=$(find "$TEST_DIR" -name "usability_P0_*.py" -o -name "usability_P0_*.ts" -o -name "usability_P0_*.sh")

if [ -z "$SCRIPTS" ]; then
    echo "ℹ️  No usability scripts matching 'usability_P0_*' found in $TEST_DIR."
    echo "   Ensure you have created the files in Phase 4."
    exit 0
fi

for script in $SCRIPTS; do
    TOTAL_COUNT=$((TOTAL_COUNT+1))
    script_name=$(basename "$script")
    log_file="$REPORTS_DIR/${script_name%.*}.log"
    
    echo -n "Running $script_name... "
    
    # Run script inside a subshell or separate process
    start_time=$(date +%s)
    
    # Run the test, capture output, and isolate execution
    if python3 "$script" > "$log_file" 2>&1; then
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        echo "✅ Passed (Took ${elapsed}s)"
        PASSED_COUNT=$((PASSED_COUNT+1))
    else
        echo "❌ Failed! (See details in $log_file)"
        FAILED_COUNT=$((FAILED_COUNT+1))
    fi
done

echo "=============================================="
echo "Live API Usability Tests Completed"
echo "Passed: $PASSED_COUNT / $TOTAL_COUNT"
echo "Failed: $FAILED_COUNT / $TOTAL_COUNT"
echo "=============================================="

if [ $FAILED_COUNT -gt 0 ]; then
    exit 1
fi
exit 0
