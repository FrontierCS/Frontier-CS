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
    -j N                  Parallelism: clusters for research, workers for algorithmic (default: 10)
    --force               Force re-evaluation of all pairs (ignore cache)
    --dry-run             Print commands without executing
    -h, --help            Show this help

Examples:
    # Run research track (SkyPilot, 10 clusters)
    ./scripts/run_eval_public.sh --track research

    # Run algorithmic track (Docker, 10 workers)
    ./scripts/run_eval_public.sh --track algorithmic

    # Custom parallelism
    ./scripts/run_eval_public.sh --track research -j 20

    # Custom solutions directory
    ./scripts/run_eval_public.sh --track algorithmic --solutions-dir ./my_solutions

    # Custom results directory
    ./scripts/run_eval_public.sh --track algorithmic --results-dir ./my_results
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

# Research track always uses SkyPilot
if [[ "$TRACK" == "research" ]]; then
    SKYPILOT=true
fi

# Set paths based on track
# Solutions and problems from public repo only
if [[ "$TRACK" == "algorithmic" ]]; then
    # Default solutions directory if not specified
    if [[ -z "$SOLUTIONS_DIR" ]]; then
        SOLUTIONS_DIR="$PUBLIC_DIR/algorithmic/solutions"
    fi
    PROBLEMS_DIR="$PUBLIC_DIR/algorithmic/problems"
    EXTRA_ARGS="--algorithmic"
    # Default results directory
    if [[ -z "$RESULTS_DIR" ]]; then
        RESULTS_DIR="$PUBLIC_DIR/results/algorithmic/batch"
    fi
else
    # Default solutions directory if not specified
    if [[ -z "$SOLUTIONS_DIR" ]]; then
        SOLUTIONS_DIR="$PUBLIC_DIR/research/solutions"
    fi
    PROBLEMS_DIR="$PUBLIC_DIR/research/problems"
    EXTRA_ARGS=""
    # Default results directory
    if [[ -z "$RESULTS_DIR" ]]; then
        RESULTS_DIR="$PUBLIC_DIR/results/research/batch"
    fi
fi

if [[ ! -d "$SOLUTIONS_DIR" ]]; then
    echo "ERROR: Solutions directory not found: $SOLUTIONS_DIR"
    exit 1
fi

if [[ ! -d "$PROBLEMS_DIR" ]]; then
    echo "ERROR: Problems directory not found: $PROBLEMS_DIR"
    exit 1
fi

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Build command
CMD="uv run frontier-eval batch"
CMD="$CMD --solutions-dir $SOLUTIONS_DIR"
CMD="$CMD --problems-dir $PROBLEMS_DIR"
CMD="$CMD --results-dir $RESULTS_DIR"
CMD="$CMD $EXTRA_ARGS"

if $SKYPILOT; then
    CMD="$CMD --skypilot --workers $PARALLELISM --clusters $PARALLELISM"
else
    CMD="$CMD --workers $PARALLELISM"
fi

if $FORCE; then
    CMD="$CMD --no-resume"
fi

echo ""
echo "=========================================="
echo "Public Repo Evaluation (Local)"
echo "=========================================="
echo "Track:              $TRACK"
echo "Solutions dir:      $SOLUTIONS_DIR"
echo "Problems dir:       $PROBLEMS_DIR"
echo "Results dir:        $RESULTS_DIR"
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
