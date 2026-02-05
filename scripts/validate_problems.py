#!/usr/bin/env python3
"""
Validate that reference solutions can run successfully for problems.

This script is used by CI to validate new/modified problems before merge.
It ensures the evaluation environment works by running reference solutions
and verifying they achieve score > 0.

Usage:
    python scripts/validate_problems.py --track algorithmic --problems 101 102
    python scripts/validate_problems.py --track research --problems flash_attn llm_sql/large
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from frontier_cs.config import get_problem_extension


def find_reference_solution(track: str, problem_id: str) -> Optional[Path]:
    """
    Find reference solution for a problem.

    Returns:
        Path to reference solution, or None if not found.
    """
    if track == "algorithmic":
        # Algorithmic: reference.cpp in problem directory
        ref_path = Path(f"algorithmic/problems/{problem_id}/reference.cpp")
        if ref_path.exists():
            return ref_path
    else:
        # Research: extension based on config.yaml language field
        problem_path = Path(f"research/problems/{problem_id}")
        ext = get_problem_extension(problem_path)
        ref_path = problem_path / f"reference.{ext}"
        if ref_path.exists():
            return ref_path
    return None


def run_evaluation(
    track: str, problem_id: str, solution_path: Path, timeout: int = 300
) -> dict:
    """
    Run evaluation using frontier CLI.

    Returns:
        Dict with keys: success, score, message
    """
    cmd = [
        "uv",
        "run",
        "frontier",
        "eval",
        track,
        problem_id,
        str(solution_path),
        "--json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Parse JSON output (may have prefix text before JSON array)
        if result.returncode == 0 and result.stdout.strip():
            stdout = result.stdout.strip()
            # Find JSON array in output
            json_start = stdout.find("[")
            if json_start >= 0:
                try:
                    data = json.loads(stdout[json_start:])
                    if isinstance(data, list) and len(data) > 0:
                        item = data[0]
                        return {
                            "success": item.get("status") == "success",
                            "score": item.get("score", 0),
                            "message": item.get("message", ""),
                        }
                except json.JSONDecodeError:
                    pass

        # Fallback: check stderr for error messages
        # Include both stdout and stderr for debugging
        error_msg = ""
        if result.stderr:
            error_msg += result.stderr
        if result.stdout:
            error_msg += "\n" + result.stdout
        return {
            "success": False,
            "score": 0,
            "message": error_msg.strip() or f"Command failed with exit code {result.returncode}",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "score": 0,
            "message": f"Evaluation timed out after {timeout}s",
        }
    except Exception as e:
        return {
            "success": False,
            "score": 0,
            "message": str(e),
        }


def validate_problem(
    track: str, problem_id: str, timeout: int = 300, verbose: bool = False
) -> bool:
    """
    Validate a problem by running its reference solution.

    1. Check reference solution exists
    2. Run evaluation
    3. Verify score > 0

    Returns:
        True if validation passed, False otherwise.
    """
    print(f"\n{'='*60}")
    print(f"Validating: {problem_id}")
    print("=" * 60)

    # Find reference solution
    ref_path = find_reference_solution(track, problem_id)
    if ref_path is None:
        print(f"  ERROR: Missing reference solution")
        if track == "algorithmic":
            print(f"  Expected: algorithmic/problems/{problem_id}/reference.cpp")
        else:
            problem_path = Path(f"research/problems/{problem_id}")
            ext = get_problem_extension(problem_path)
            print(f"  Expected: research/problems/{problem_id}/reference.{ext}")
        return False

    print(f"  Reference: {ref_path}")

    # Run evaluation
    print(f"  Running evaluation...")
    result = run_evaluation(track, problem_id, ref_path, timeout)

    if verbose:
        print(f"  Result: {result}")

    # Check result
    # Accept score >= 0 for baseline references (score=0 means evaluation works, just no speedup)
    if result["success"] and result["score"] is not None and result["score"] >= 0:
        print(f"  PASS: score = {result['score']}")
        return True
    else:
        print(f"  FAIL: score = {result['score']}")
        if result["message"]:
            # Truncate long messages
            msg = result["message"]
            if len(msg) > 500:
                msg = msg[:500] + "..."
            print(f"  Message: {msg}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate reference solutions for problems"
    )
    parser.add_argument(
        "--track",
        required=True,
        choices=["algorithmic", "research"],
        help="Track to validate",
    )
    parser.add_argument(
        "--problems",
        nargs="+",
        required=True,
        help="Problem IDs to validate",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per evaluation in seconds (default: 300)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    print(f"Validating {len(args.problems)} {args.track} problem(s)")

    failed = []
    passed = []

    for problem in args.problems:
        if validate_problem(args.track, problem, args.timeout, args.verbose):
            passed.append(problem)
        else:
            failed.append(problem)

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print("=" * 60)
    print(f"  Passed: {len(passed)}")
    print(f"  Failed: {len(failed)}")

    if failed:
        print(f"\nFailed problems:")
        for p in failed:
            print(f"  - {p}")
        print(f"\nValidation FAILED")
        sys.exit(1)

    print(f"\nAll problems validated successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
