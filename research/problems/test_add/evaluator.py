#!/usr/bin/env python3
"""Simple test evaluator that checks if a solution can add numbers."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_solution(solution_path: Path):
    """Load solution module."""
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load {solution_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(solution_path: Path) -> dict:
    """Evaluate the solution."""
    try:
        solution = load_solution(solution_path)

        # Test cases
        test_cases = [
            (1, 2, 3),
            (0, 0, 0),
            (-5, 10, 5),
            (100, 200, 300),
            (999, 1, 1000),
        ]

        passed = 0
        for a, b, expected in test_cases:
            try:
                result = solution.add(a, b)
                if result == expected:
                    passed += 1
            except Exception:
                pass

        score = (passed / len(test_cases)) * 100
        return {"score": score, "passed": passed, "total": len(test_cases)}

    except Exception as e:
        return {"score": 0, "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("solution", type=Path, help="Path to solution file")
    args = parser.parse_args()

    result = evaluate(args.solution)
    score = result.get("score", 0)

    # Print score on last line (expected format for frontier-eval)
    print(f"Passed: {result.get('passed', 0)}/{result.get('total', 0)}")
    print(score)

    return 0 if score > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
