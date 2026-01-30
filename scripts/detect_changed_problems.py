#!/usr/bin/env python3
"""
Detect changed problems from git diff, handling nested variants.

Usage:
    python scripts/detect_changed_problems.py --track research
    python scripts/detect_changed_problems.py --track algorithmic
    python scripts/detect_changed_problems.py --track research --base-ref origin/main
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_changed_files(base_ref: str = "origin/main") -> list[str]:
    """Get list of changed files from git diff."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Try without three-dot syntax (for direct commits)
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "HEAD"],
            capture_output=True,
            text=True,
        )
    return [f for f in result.stdout.strip().split("\n") if f]


def detect_changed_problems(track: str, base_ref: str = "origin/main") -> list[str]:
    """
    Detect changed problems from git diff.

    For research track, handles nested variants:
    - research/problems/llm_sql/large/evaluator.py -> llm_sql/large
    - research/problems/flash_attn/evaluator.py -> flash_attn

    For algorithmic track, uses flat structure:
    - algorithmic/problems/101/config.yaml -> 101

    A valid problem directory must contain:
    - Research: evaluator.py
    - Algorithmic: config.yaml
    """
    changed_files = get_changed_files(base_ref)
    prefix = f"{track}/problems/"
    problems = set()

    for file_path in changed_files:
        if not file_path.startswith(prefix):
            continue

        # Extract relative path within problems/
        rel_path = file_path[len(prefix) :]
        parts = rel_path.split("/")

        if not parts or not parts[0]:
            continue

        # Find the actual problem directory (one with evaluator.py or config.yaml)
        # Start from deepest and work up, or from shallowest and work down
        for i in range(1, len(parts) + 1):
            candidate = "/".join(parts[:i])
            problem_dir = Path(prefix + candidate)

            if track == "algorithmic":
                is_problem = (problem_dir / "config.yaml").exists()
            else:
                # Research problems must have evaluator.py
                is_problem = (problem_dir / "evaluator.py").exists()

            if is_problem:
                problems.add(candidate)
                break

    return sorted(problems)


def main():
    parser = argparse.ArgumentParser(
        description="Detect changed problems from git diff"
    )
    parser.add_argument(
        "--track",
        required=True,
        choices=["algorithmic", "research"],
        help="Track to detect changes for",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="Base ref for git diff (default: origin/main)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose output to stderr",
    )

    args = parser.parse_args()

    problems = detect_changed_problems(args.track, args.base_ref)

    if args.verbose:
        print(f"Found {len(problems)} changed problems:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)

    # Output space-separated list for CI
    print(" ".join(problems))

    return 0


if __name__ == "__main__":
    sys.exit(main())
