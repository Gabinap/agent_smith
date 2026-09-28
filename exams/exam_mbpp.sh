#!/bin/bash
# MBPP Examination Script
# Usage: ./exam_mbpp.sh --student-path PATH --moulinette-path PATH --env-file PATH
# Pass criteria: 4 out of 5 random tasks

set -e

# --- Argument parsing ---
STUDENT_PATH=""
MOULINETTE_PATH=""
ENV_FILE=""
MODEL=""
BACKEND=""

usage() {
    echo "Usage: $0 --student-path PATH --moulinette-path PATH --env-file PATH [--model-name MODEL] [--provider-url URL]"
    echo ""
    echo "Required arguments:"
    echo "  --student-path PATH       Path to student code directory"
    echo "  --moulinette-path PATH    Path to moulinette directory"
    echo "  --env-file PATH           Path to .env file with API keys"
    echo ""
    echo "Optional arguments:"
    echo "  --model-name MODEL        Model name (forwarded to agent)"
    echo "  --provider-url URL        LLM provider API URL (forwarded to agent)"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --student-path)
            STUDENT_PATH="$2"
            shift 2
            ;;
        --moulinette-path)
            MOULINETTE_PATH="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --model-name)
            MODEL="$2"
            shift 2
            ;;
        --provider-url)
            BACKEND="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown argument: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [ -z "$STUDENT_PATH" ] || [ -z "$MOULINETTE_PATH" ] || [ -z "$ENV_FILE" ]; then
    echo "Error: All three arguments are required."
    usage
fi

if [ ! -d "$STUDENT_PATH" ]; then
    echo "Error: Student path is not a directory: $STUDENT_PATH"
    exit 1
fi

if [ ! -d "$MOULINETTE_PATH" ]; then
    echo "Error: Moulinette path is not a directory: $MOULINETTE_PATH"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found: $ENV_FILE"
    exit 1
fi

# Resolve to absolute paths
STUDENT_PATH="$(cd "$STUDENT_PATH" && pwd)"
MOULINETTE_PATH="$(cd "$MOULINETTE_PATH" && pwd)"
ENV_FILE="$(cd "$(dirname "$ENV_FILE")" && pwd)/$(basename "$ENV_FILE")"

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATETIME=$(date +"%Y-%m-%d_%H-%M-%S")
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
EVAL_DIR="$PROJECT_DIR/evaluations/mbpp/$DATETIME"
PASSED=0
TOTAL=5
PASS_THRESHOLD=4

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}==============================================${NC}"
echo -e "${YELLOW}MBPP EXAMINATION${NC}"
echo -e "${YELLOW}==============================================${NC}"
echo "Student path: $STUDENT_PATH"
echo "Moulinette path: $MOULINETTE_PATH"
echo "Env file: $ENV_FILE"
echo "Eval directory: $EVAL_DIR"
echo "Tasks: $TOTAL"
echo "Pass threshold: $PASS_THRESHOLD"
[ -n "$MODEL" ] && echo "Model: $MODEL"
[ -n "$BACKEND" ] && echo "Backend: $BACKEND"
echo -e "${YELLOW}==============================================${NC}"

mkdir -p "$EVAL_DIR"

# Load environment variables from .env file
set -a
source "$ENV_FILE"
set +a

# Build optional model arguments to forward to agent
MODEL_ARGS=""
[ -n "$MODEL" ] && MODEL_ARGS="$MODEL_ARGS --model-name $MODEL"
[ -n "$BACKEND" ] && MODEL_ARGS="$MODEL_ARGS --provider-url $BACKEND"

for i in $(seq 1 $TOTAL); do
    echo ""
    echo -e "${YELLOW}--- Task $i/$TOTAL ---${NC}"

    # Dump random task
    echo "Dumping task..."
    TEMP_TASK=$(mktemp --suffix=.json)
    cd "$MOULINETTE_PATH"
    uv run moulinette_eval dump mbpp --output "$TEMP_TASK"

    TASK_ID=$(cat "$TEMP_TASK" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
    echo "Task ID: $TASK_ID"

    # Create task directory and copy task input
    TASK_DIR="$EVAL_DIR/$TASK_ID"
    mkdir -p "$TASK_DIR"
    cp "$TEMP_TASK" "$TASK_DIR/task.json"
    rm -f "$TEMP_TASK"

    TASK_FILE="$TASK_DIR/task.json"
    SOLUTION_FILE="$TASK_DIR/solution.json"

    # Run student solution with separate stdout/stderr capture
    echo "Running student solution..."
    cd "$STUDENT_PATH"
    AGENT_START=$(date +%s)
    uv run python -m agent_mbpp --task-file "$TASK_FILE" --output "$SOLUTION_FILE" $MODEL_ARGS \
        > "$TASK_DIR/stdout.log" 2> "$TASK_DIR/stderr.log" \
        && EXEC_SUCCESS=1 || EXEC_SUCCESS=0
    AGENT_END=$(date +%s)
    AGENT_DURATION=$((AGENT_END - AGENT_START))
    echo "Agent duration: ${AGENT_DURATION}s"

    # Check time limit (MBPP: 120s)
    MBPP_TIME_LIMIT=120
    if [ "$AGENT_DURATION" -gt "$MBPP_TIME_LIMIT" ]; then
        echo -e "${RED}FAILED: Agent exceeded time limit (${AGENT_DURATION}s > ${MBPP_TIME_LIMIT}s)${NC}"
        echo "TIME_LIMIT: EXCEEDED (${AGENT_DURATION}s > ${MBPP_TIME_LIMIT}s)" >> "$TASK_DIR/stdout.log"
        echo "RESULT: FAILED (time limit)" >> "$TASK_DIR/stdout.log"
    elif [ $EXEC_SUCCESS -eq 1 ]; then
        echo "TIME_LIMIT: OK (${AGENT_DURATION}s <= ${MBPP_TIME_LIMIT}s)" >> "$TASK_DIR/stdout.log"
        # Validate solution
        cd "$MOULINETTE_PATH"
        echo "Validating solution..."
        VALIDATE_OUTPUT=$(uv run moulinette_eval validate mbpp "$TASK_FILE" "$SOLUTION_FILE" 2>&1) && VALIDATE_SUCCESS=1 || VALIDATE_SUCCESS=0
        echo "$VALIDATE_OUTPUT" >> "$TASK_DIR/stdout.log"

        if [ $VALIDATE_SUCCESS -eq 1 ]; then
            echo -e "Result: ${GREEN}PASSED${NC}"
            echo "RESULT: PASSED" >> "$TASK_DIR/stdout.log"
            ((PASSED++)) || true
        else
            echo -e "Result: ${RED}FAILED (validation)${NC}"
            echo "RESULT: FAILED (validation)" >> "$TASK_DIR/stdout.log"
        fi
    else
        echo "TIME_LIMIT: OK (${AGENT_DURATION}s <= ${MBPP_TIME_LIMIT}s)" >> "$TASK_DIR/stdout.log"
        echo -e "Result: ${RED}FAILED (execution)${NC}"
        echo "RESULT: FAILED (execution)" >> "$TASK_DIR/stderr.log"
        # Show last few lines of error
        grep -E "(Error|Exception|Traceback)" "$TASK_DIR/stderr.log" | tail -3 | sed 's/^/  /' || true
    fi
done

echo ""
echo -e "${YELLOW}==============================================${NC}"
echo -e "${YELLOW}FINAL RESULT: $PASSED/$TOTAL${NC}"
echo -e "${YELLOW}==============================================${NC}"
echo "Results saved to: $EVAL_DIR"

echo ""
echo "To inspect results:"
echo "  cd moulinette && uv run moulinette_eval display ../\$SOLUTION_FILE"
echo ""

if [ $PASSED -ge $PASS_THRESHOLD ]; then
    echo -e "${GREEN}STATUS: PASS${NC}"
    exit 0
else
    echo -e "${RED}STATUS: FAIL${NC}"
    exit 1
fi
