#!/bin/bash
#
# Batch evaluation script for Frontier-CS
# Replicates CI logic, can run locally
#
# Usage:
#   ./scripts/run_eval.sh --track research    # Auto-clones internal + results repos
#   ./scripts/run_eval.sh --track algorithmic --workers 10
#   ./scripts/run_eval.sh --check-overlap
#   ./scripts/run_eval.sh --track research --internal-dir /custom/path  # Use existing clone
#

set -e

# Defaults
TRACK=""
INTERNAL_DIR=""
PARALLELISM=10
SKYPILOT=false
RESULTS_REPO=""
CHECK_OVERLAP=false
DRY_RUN=false
AUTO_CLONE=true  # Auto-clone repos if not provided
PUSH_MODE="interactive"  # interactive (default), yes, no

# Script directory (public repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC_DIR="$(dirname "$SCRIPT_DIR")"

# Default clone locations (sibling directories)
DEFAULT_INTERNAL_DIR="$(dirname "$PUBLIC_DIR")/Frontier-CS-internal"
DEFAULT_RESULTS_REPO="$(dirname "$PUBLIC_DIR")/Frontier-CS-Result"

# Repo URLs
INTERNAL_REPO_URL="https://github.com/FrontierCS/Frontier-CS-internal.git"
RESULTS_REPO_URL="https://github.com/FrontierCS/Frontier-CS-Result.git"

# Clone or update a repo
ensure_repo() {
    local url="$1"
    local dir="$2"
    local name="$3"

    if [[ -d "$dir/.git" ]]; then
        echo "Updating $name: $dir"
        git -C "$dir" pull --ff-only 2>&1 || echo "  (pull failed, using existing)"
    else
        echo "Cloning $name to $dir"
        git clone --depth 1 "$url" "$dir"
    fi
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Auto-clones internal and results repos if not provided.
Default locations: ../Frontier-CS-internal and ../Frontier-CS-Result

Options:
    --track TYPE          Track to evaluate: research or algorithmic (required)
                          research: uses SkyPilot (GPU required)
                          algorithmic: uses Docker
    --internal-dir DIR    Path to internal repo (default: auto-clone)
    --results-repo DIR    Path to results repo for incremental state (default: auto-clone)
    -j N                  Parallelism: clusters for research, workers for algorithmic (default: 10)
    --push                Auto-push results to remote (for CI)
    --no-push             Skip pushing results (for local testing)
    --check-overlap       Only check internal ⊇ public
    --dry-run             Print commands without executing
    -h, --help            Show this help

Examples:
    # Run research (SkyPilot, 10 clusters)
    ./scripts/run_eval.sh --track research

    # Run algorithmic (Docker, 10 workers)
    ./scripts/run_eval.sh --track algorithmic

    # Custom parallelism
    ./scripts/run_eval.sh --track research -j 20

    # Check internal ⊇ public
    ./scripts/run_eval.sh --check-overlap
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
        --internal-dir)
            INTERNAL_DIR="$2"
            shift 2
            ;;
        -j)
            PARALLELISM="$2"
            shift 2
            ;;
        --results-repo)
            RESULTS_REPO="$2"
            shift 2
            ;;
        --check-overlap)
            CHECK_OVERLAP=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --push)
            PUSH_MODE="yes"
            shift
            ;;
        --no-push)
            PUSH_MODE="no"
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

# Get problem IDs from a directory
get_problem_ids() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        return
    fi

    for item in "$dir"/*; do
        [[ -d "$item" ]] || continue
        name=$(basename "$item")
        [[ "$name" == .* ]] && continue

        # Direct problem (has config.yaml or statement.txt)
        if [[ -f "$item/config.yaml" ]] || [[ -f "$item/statement.txt" ]] || [[ -f "$item/evaluator.py" ]]; then
            echo "$name"
        else
            # Nested problems
            for subitem in "$item"/*; do
                [[ -d "$subitem" ]] || continue
                subname=$(basename "$subitem")
                if [[ -f "$subitem/config.yaml" ]] || [[ -f "$subitem/evaluator.py" ]]; then
                    echo "$name/$subname"
                fi
            done
        fi
    done
}

# Check that internal is a superset of public and report differences
check_superset() {
    local public_dir="$1"
    local internal_dir="$2"
    local has_error=false

    for track in algorithmic research; do
        if [[ "$track" == "algorithmic" ]]; then
            public_problems="$public_dir/algorithmic/problems"
            internal_problems="$internal_dir/algorithmic/problems"
        else
            public_problems="$public_dir/research/problems"
            internal_problems="$internal_dir/research/problems"
        fi

        echo ""
        echo "${track^^} track:"

        public_ids=$(get_problem_ids "$public_problems" | sort)
        internal_ids=$(get_problem_ids "$internal_problems" | sort)

        public_count=$(echo "$public_ids" | grep -c . || echo 0)
        internal_count=$(echo "$internal_ids" | grep -c . || echo 0)

        echo "  Public problems:   $public_count"
        echo "  Internal problems: $internal_count"

        # Check: all public problems should be in internal (public ⊆ internal)
        missing_in_internal=$(comm -23 <(echo "$public_ids") <(echo "$internal_ids"))

        # Internal-only problems (this is expected/OK)
        internal_only=$(comm -13 <(echo "$public_ids") <(echo "$internal_ids"))
        internal_only_count=$(echo "$internal_only" | grep -c . 2>/dev/null || true)
        [[ -z "$internal_only_count" ]] && internal_only_count=0

        if [[ -n "$missing_in_internal" ]]; then
            missing_count=$(echo "$missing_in_internal" | grep -c .)
            echo "  ERROR: $missing_count public problems missing in internal:"
            echo "$missing_in_internal" | sed 's/^/    - /'
            has_error=true
        else
            echo "  All public problems exist in internal"
        fi

        if [[ $internal_only_count -gt 0 ]]; then
            echo "  Internal-only problems: $internal_only_count (OK)"
        fi

        # Check differences in shared problems using folder hash
        diff_count=0
        total_shared=0

        for prob_id in $public_ids; do
            total_shared=$((total_shared + 1))
            pub_prob="$public_problems/$prob_id"
            int_prob="$internal_problems/$prob_id"

            [[ ! -d "$int_prob" ]] && continue

            # Hash folder contents (excluding __pycache__) - only compare file hashes, not paths
            pub_hash=$(find "$pub_prob" -type f -not -path '*__pycache__*' -print0 2>/dev/null | sort -z | xargs -0 md5sum 2>/dev/null | awk '{print $1}' | sort | md5sum | cut -d' ' -f1)
            int_hash=$(find "$int_prob" -type f -not -path '*__pycache__*' -print0 2>/dev/null | sort -z | xargs -0 md5sum 2>/dev/null | awk '{print $1}' | sort | md5sum | cut -d' ' -f1)

            if [[ "$pub_hash" != "$int_hash" ]]; then
                diff_count=$((diff_count + 1))
            fi
        done

        echo "  Problems with differences: $diff_count / $total_shared"
    done

    if $has_error; then
        echo ""
        echo "ERROR: Internal should be a superset of public."
        echo "       All public problems must exist in internal."
        return 1
    fi

    echo ""
    echo "Check passed: internal ⊇ public"
    return 0
}

# Commit and push results to remote
push_results() {
    local results_repo="$1"
    local track="$2"

    if [[ -z "$results_repo" ]] || [[ ! -d "$results_repo/.git" ]]; then
        return
    fi

    cd "$results_repo"

    # Only add track-relevant files
    if [[ "$track" == "algorithmic" ]]; then
        git add algorithmic/
    elif [[ "$track" == "research" ]]; then
        git add research/
    else
        git add .
    fi

    if ! git diff --staged --quiet; then
        git commit -m "chore: update $track evaluation results $(date +%Y-%m-%d)"
        git push
        echo "Pushed results to remote"
    else
        echo "No changes to push"
    fi
}

# Interactive push confirmation
confirm_push() {
    if [[ "$PUSH_MODE" == "yes" ]]; then
        return 0
    elif [[ "$PUSH_MODE" == "no" ]]; then
        return 1
    fi

    # Interactive mode
    read -p "Push results to remote? [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

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

# Trap for Ctrl+C and other signals (local runs)
cleanup_on_exit() {
    echo ""
    echo "Interrupted! Running cleanup..."
    cleanup_skypilot
    exit 1
}
trap cleanup_on_exit INT TERM

# Main

# Auto-clone internal repo if not provided
if [[ -z "$INTERNAL_DIR" ]] && $AUTO_CLONE; then
    INTERNAL_DIR="$DEFAULT_INTERNAL_DIR"
    ensure_repo "$INTERNAL_REPO_URL" "$INTERNAL_DIR" "internal repo"
fi

# Auto-clone results repo if not provided
if [[ -z "$RESULTS_REPO" ]] && $AUTO_CLONE; then
    RESULTS_REPO="$DEFAULT_RESULTS_REPO"

    # Check if results repo exists and has uncommitted changes
    if [[ -d "$RESULTS_REPO/.git" ]]; then
        # Filter changes by track if specified
        # algorithmic -> algorithmic/, research -> research/
        if [[ "$TRACK" == "algorithmic" ]]; then
            TRACK_FILTER="algorithmic/"
        elif [[ "$TRACK" == "research" ]]; then
            TRACK_FILTER="research/"
        else
            TRACK_FILTER=""  # No filter for --check-overlap or unspecified track
        fi

        # Check for track-relevant uncommitted changes
        if [[ -n "$TRACK_FILTER" ]]; then
            HAS_CHANGES=$(git -C "$RESULTS_REPO" status --porcelain 2>/dev/null | grep "^.. $TRACK_FILTER" || true)
        else
            HAS_CHANGES=$(git -C "$RESULTS_REPO" status --porcelain 2>/dev/null || true)
        fi

        if [[ -n "$HAS_CHANGES" ]]; then
            echo ""
            echo "⚠️  Results repo has uncommitted changes!"
            echo "    Path: $RESULTS_REPO"
            echo ""
            echo "$HAS_CHANGES" | head -20
            echo ""

            # Non-interactive: abort
            if [[ ! -t 0 ]]; then
                echo "ERROR: Uncommitted changes in results repo. Aborting."
                echo "       Commit or stash changes, then retry."
                exit 1
            fi

            # Interactive: let user choose
            echo "Options:"
            echo "  [C] Continue - skip pull, use local state"
            echo "  [A] Abort    - exit and resolve manually"
            read -p "Choice [C/A]: " -n 1 -r
            echo ""

            if [[ ! $REPLY =~ ^[Cc]$ ]]; then
                echo "Aborted"
                exit 1
            fi
            echo "Continuing with local state (skipping pull)"
        else
            ensure_repo "$RESULTS_REPO_URL" "$RESULTS_REPO" "results repo"
        fi
    else
        ensure_repo "$RESULTS_REPO_URL" "$RESULTS_REPO" "results repo"
    fi
fi

# Check overlap mode
if $CHECK_OVERLAP; then
    if [[ -z "$INTERNAL_DIR" ]] || [[ ! -d "$INTERNAL_DIR" ]]; then
        echo "ERROR: Internal repo not found"
        exit 1
    fi
    check_superset "$PUBLIC_DIR" "$INTERNAL_DIR"
    exit $?
fi

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

# Validate internal dir
if [[ -z "$INTERNAL_DIR" ]] || [[ ! -d "$INTERNAL_DIR" ]]; then
    echo "ERROR: Internal directory not found: $INTERNAL_DIR"
    echo "       Clone it manually or ensure you have access to FrontierCS/Frontier-CS-internal"
    exit 1
fi

# Check that internal is superset of public
echo ""
echo "Checking internal ⊇ public..."
if ! check_superset "$PUBLIC_DIR" "$INTERNAL_DIR"; then
    echo ""
    echo "WARNING: Continuing despite check failure..."
fi

echo ""
echo "Using internal data from: $INTERNAL_DIR"
echo "Running tools from: $PUBLIC_DIR"

# Set paths based on track
# Solutions always from public, problems from internal (more test cases)
# Results saved directly to results repo
if [[ "$TRACK" == "algorithmic" ]]; then
    SOLUTIONS_DIR="$PUBLIC_DIR/algorithmic/solutions"
    RESULTS_DIR="$RESULTS_REPO/algorithmic/batch"
    PROBLEMS_DIR="$INTERNAL_DIR/algorithmic/problems"
    EXTRA_ARGS="--algorithmic"
else
    SOLUTIONS_DIR="$PUBLIC_DIR/research/solutions"
    RESULTS_DIR="$RESULTS_REPO/research/batch"
    PROBLEMS_DIR="$INTERNAL_DIR/research/problems"
    EXTRA_ARGS=""
fi

if [[ ! -d "$SOLUTIONS_DIR" ]]; then
    echo "ERROR: Solutions directory not found: $SOLUTIONS_DIR"
    exit 1
fi

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Build command
CMD="uv run frontier-eval batch"
CMD="$CMD --solutions-dir $SOLUTIONS_DIR"
CMD="$CMD --results-dir $RESULTS_DIR"
CMD="$CMD $EXTRA_ARGS"

# For algorithmic track, use internal's problems (more test cases)
if [[ -n "$PROBLEMS_DIR" ]]; then
    CMD="$CMD --problems-dir $PROBLEMS_DIR"
fi

if $SKYPILOT; then
    CMD="$CMD --skypilot --workers $PARALLELISM --clusters $PARALLELISM"
else
    CMD="$CMD --workers $PARALLELISM"
fi

echo ""
echo "Command: $CMD"
echo "Working directory: $PUBLIC_DIR"
echo ""

if $DRY_RUN; then
    echo "(dry run, not executing)"
    exit 0
fi

# Run evaluation from public repo (uses public's tools, internal's data)
cd "$PUBLIC_DIR"
$CMD

# Push results if there are changes
echo ""
if [[ -d "$RESULTS_REPO/.git" ]]; then
    # Check for track-relevant changes
    if [[ "$TRACK" == "algorithmic" ]]; then
        CHANGES=$(git -C "$RESULTS_REPO" status --porcelain algorithmic/ 2>/dev/null | head -1)
    else
        CHANGES=$(git -C "$RESULTS_REPO" status --porcelain research/ 2>/dev/null | head -1)
    fi

    if [[ -n "$CHANGES" ]]; then
        if confirm_push; then
            push_results "$RESULTS_REPO" "$TRACK"
        fi
    else
        echo "No changes to push"
    fi
fi

# Cleanup SkyPilot clusters
cleanup_skypilot

echo ""
echo "Evaluation complete!"
