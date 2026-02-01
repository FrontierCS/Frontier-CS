#!/bin/bash
#
# Public-only evaluation script for Frontier-CS
# Evaluates only the public repo without checking private repo or pushing results
#
# Usage:
#   ./scripts/run_eval_public.sh --track research
#   ./scripts/run_eval_public.sh --track algorithmic --workers 10
#   ./scripts/run_eval_public.sh --track algorithmic --results-dir ./my_results
#

set -e

# Defaults
TRACK=""
SOLUTIONS_DIR=""
PARALLELISM=10
SKYPILOT=false
RESULTS_DIR=""
DRY_RUN=false
FORCE=false  # Force re-evaluation of all pairs (--no-resume)
MODEL=""      # Filter by model name
PROBLEM=""    # Filter by problem name

# Script directory (public repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Evaluates only the public repo (no private repo checking, no result pushing).

Options:
    --track TYPE          Track to evaluate: research or algorithmic (required)
                          research: uses SkyPilot (GPU required)
                          algorithmic: uses Docker
    --solutions-dir DIR   Path to solutions directory (default: ./<track>/solutions)
    --results-dir DIR     Path to save results (default: ./results/<track>/batch)
    --model MODEL         Filter solutions by model name (e.g., gpt4, claude)
    --problem PROBLEM     Filter solutions by problem name (e.g., flash_attn)
    -j N                  Parallelism: clusters for research, workers for algorithmic (default: 10)
    --force               Force re-evaluation of all pairs (ignore cache)
    --dry-run             Print commands without executing
    -h, --help            Show this help

Examples:
    # Run research track (SkyPilot, 10 clusters)
    ./scripts/run_eval_public.sh --track research

    # Run algorithmic track (Docker, 10 workers)
    ./scripts/run_eval_public.sh --track algorithmic

    # Test a specific model across all problems
    ./scripts/run_eval_public.sh --track research --model gpt4

    # Test all models on a specific problem
    ./scripts/run_eval_public.sh --track research --problem flash_attn

    # Test a specific model on a specific problem
    ./scripts/run_eval_public.sh --track research --model gpt4 --problem flash_attn

    # Custom solutions directory
    ./scripts/run_eval_public.sh --track algorithmic --solutions-dir ./my_solutions
EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --track)
            TRACK="$2"
            shift 2
            ;;
        --solutions-dir)
            SOLUTIONS_DIR="$2"
            shift 2
            ;;
        --results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --problem)
            PROBLEM="$2"
            shift 2
            ;;
        -j)
            PARALLELISM="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Cleanup SkyPilot clusters
cleanup_skypilot() {
    if ! $SKYPILOT; then
        return
    fi

    echo ""
    echo "Cleaning up SkyPilot clusters..."
    CLUSTERS_LIST=$(uv run sky status --refresh 2>/dev/null | grep -E '^eval-' | awk '{print $1}' || true)
    if [[ -n "$CLUSTERS_LIST" ]]; then
        echo "$CLUSTERS_LIST" | while read cluster; do
            echo "  Terminating: $cluster"
            uv run sky down "$cluster" -y &
        done
        wait
        echo "Cleanup complete"
    else
        echo "No eval clusters to clean up"
    fi
}

# Trap for any exit (Ctrl+C, errors, normal exit)
CLEANUP_DONE=false
cleanup_on_exit() {
    if $CLEANUP_DONE; then
        return
    fi
    CLEANUP_DONE=true

    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo ""
        echo "Exiting with code $exit_code, running cleanup..."
    fi
    cleanup_skypilot
}
trap cleanup_on_exit EXIT

# Main

if [[ -z "$TRACK" ]]; then
    echo "ERROR: --track is required"
    usage
fi

if [[ "$TRACK" != "research" ]] && [[ "$TRACK" != "algorithmic" ]]; then
    echo "ERROR: --track must be 'research' or 'algorithmic'"
    exit 1
fi

# Research track uses SkyPilot by default
if [[ "$TRACK" == "research" ]]; then
    SKYPILOT=true
fi

# Build command - CLI now handles default paths based on track
CMD="uv run frontier-eval batch --track $TRACK"

if [[ -n "$SOLUTIONS_DIR" ]]; then
    CMD="$CMD --solutions-dir $SOLUTIONS_DIR"
fi

if [[ -n "$RESULTS_DIR" ]]; then
    CMD="$CMD --results-dir $RESULTS_DIR"
fi

if $SKYPILOT; then
    CMD="$CMD --skypilot --workers $PARALLELISM --clusters $PARALLELISM"
else
    CMD="$CMD --workers $PARALLELISM"
fi

if $FORCE; then
    CMD="$CMD --no-resume"
fi

if [[ -n "$MODEL" ]]; then
    CMD="$CMD --model $MODEL"
fi

if [[ -n "$PROBLEM" ]]; then
    CMD="$CMD --problem $PROBLEM"
fi

echo ""
echo "=========================================="
echo "Public Repo Evaluation"
echo "=========================================="
echo "Track:              $TRACK"
if [[ -n "$SOLUTIONS_DIR" ]]; then
    echo "Solutions dir:      $SOLUTIONS_DIR"
else
    echo "Solutions dir:      (default: ./$TRACK/solutions)"
fi
if [[ -n "$RESULTS_DIR" ]]; then
    echo "Results dir:        $RESULTS_DIR"
else
    echo "Results dir:        (default: ./results/$TRACK)"
fi
if [[ -n "$MODEL" ]]; then
    echo "Model filter:       $MODEL"
fi
if [[ -n "$PROBLEM" ]]; then
    echo "Problem filter:     $PROBLEM"
fi
echo "Parallelism:        $PARALLELISM"
if $SKYPILOT; then
    echo "Execution:          SkyPilot (GPU)"
else
    echo "Execution:          Docker (local)"
fi
echo "=========================================="
echo ""
echo "Command: $CMD"
echo ""

if $DRY_RUN; then
    echo "(dry run, not executing)"
    exit 0
fi

# Run evaluation from public repo
cd "$PUBLIC_DIR"
$CMD

echo ""
echo "=========================================="
echo "Evaluation complete!"
echo "Results saved to: $RESULTS_DIR"
echo "=========================================="
