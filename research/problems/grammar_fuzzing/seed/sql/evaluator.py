#!/usr/bin/env python3
"""
Grammar Fuzzing Evaluator - SQL Parser Variant

Evaluates a fuzzer's ability to generate inputs that maximize code coverage
of the target SQL parser within a time budget.
"""

import argparse
import importlib.util
import json
import os
import sys
import time
import traceback
from pathlib import Path


class Evaluator:
    def __init__(self, problem_dir: str):
        self.problem_dir = Path(problem_dir)
        self.resources_dir = self.problem_dir / "resources"
        self.grammar_path = self.resources_dir / "sql_grammar.txt"
        self.sql_engine_dir = self.resources_dir / "sql_engine"
        self.time_budget_seconds = 60

        # Ensure resources directory is in path
        if str(self.resources_dir) not in sys.path:
            sys.path.insert(0, str(self.resources_dir))

    def _measure_coverage(self, statements: list[str]) -> dict:
        """
        Measure code coverage of the parser when processing the given statements.
        
        Returns dict with line_coverage, branch_coverage, lines_covered, total_lines, etc.
        """
        import coverage

        # Files to measure coverage on
        parser_files = [
            str(self.sql_engine_dir / "parser.py"),
            str(self.sql_engine_dir / "tokenizer.py"),
            str(self.sql_engine_dir / "ast_nodes.py"),
        ]

        # Create a coverage object targeting the sql_engine files
        cov = coverage.Coverage(
            branch=True,
            source=[str(self.sql_engine_dir)],
        )

        cov.start()
        
        successful_parses = 0
        failed_parses = 0
        
        try:
            # Import the sql_engine package fresh
            from sql_engine import parse_sql
            
            # Run each statement through the parser
            for stmt in statements:
                try:
                    parse_sql(stmt)
                    successful_parses += 1
                except Exception:
                    failed_parses += 1
        finally:
            cov.stop()

        # Analyze coverage
        cov.save()
        
        # Get coverage data for all files
        total_lines = 0
        covered_lines = 0
        total_branches = 0
        covered_branches = 0
        
        for filepath in parser_files:
            if os.path.exists(filepath):
                try:
                    analysis = cov.analysis2(filepath)
                    # analysis returns: (filename, executable_lines, excluded_lines, missing_lines, formatted_missing)
                    _, executable_lines, excluded_lines, missing_lines, _ = analysis
                    
                    file_total = len(executable_lines)
                    file_covered = file_total - len(missing_lines)
                    total_lines += file_total
                    covered_lines += file_covered
                except Exception:
                    pass
        
        # Get branch coverage using analysis_v2 or branch analysis
        try:
            for filepath in parser_files:
                if os.path.exists(filepath):
                    # Use branch_stats which returns (branch_total, branch_covered) tuples
                    file_analysis = cov._analyze(filepath)
                    if hasattr(file_analysis, 'numbers'):
                        nums = file_analysis.numbers
                        if hasattr(nums, 'n_branches') and hasattr(nums, 'n_partial_branches'):
                            total_branches += nums.n_branches
                            covered_branches += nums.n_branches - nums.n_missing_branches if hasattr(nums, 'n_missing_branches') else 0
        except Exception:
            # Fallback: just report 0 for branch coverage if not available
            pass

        line_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0
        branch_coverage = (covered_branches / total_branches * 100) if total_branches > 0 else 0.0

        return {
            "line_coverage": line_coverage,
            "branch_coverage": branch_coverage,
            "lines_covered": covered_lines,
            "total_lines": total_lines,
            "branches_covered": covered_branches,
            "total_branches": total_branches,
            "successful_parses": successful_parses,
            "failed_parses": failed_parses,
            "total_statements": len(statements),
        }

    def evaluate(self, solution_module_path: str) -> dict:
        """
        Evaluate a solution's fuzzer implementation.
        
        The solution should implement:
            class Solution:
                def solve(self, grammar_path, parser_module_path, time_budget_seconds) -> list[str]
        """
        # Load the solution module
        spec = importlib.util.spec_from_file_location("solution", solution_module_path)
        solution = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(solution)
        except Exception as e:
            return {
                "score": 0.0,
                "runs_successfully": 0.0,
                "error": f"Failed to load solution: {e}",
            }

        if not hasattr(solution, "Solution"):
            return {
                "score": 0.0,
                "runs_successfully": 0.0,
                "error": "Missing Solution class",
            }

        try:
            solver = solution.Solution()
        except Exception as e:
            return {
                "score": 0.0,
                "runs_successfully": 0.0,
                "error": f"Failed to instantiate Solution: {e}",
            }

        # Run the fuzzer with time budget
        start_time = time.time()
        
        try:
            statements = solver.solve(
                resources_path=str(self.resources_dir),
            )
        except Exception as e:
            return {
                "score": 0.0,
                "runs_successfully": 0.0,
                "error": f"Fuzzer execution failed: {e}",
                "traceback": traceback.format_exc(),
            }
        
        elapsed_time = time.time() - start_time
        
        # Validate output
        if not isinstance(statements, list):
            return {
                "score": 0.0,
                "runs_successfully": 0.0,
                "error": f"Expected list of statements, got {type(statements).__name__}",
            }

        # Filter to only string statements
        valid_statements = [s for s in statements if isinstance(s, str)]
        
        if len(valid_statements) == 0:
            return {
                "score": 0.0,
                "runs_successfully": 1.0,
                "error": "No valid statements generated",
                "elapsed_time": elapsed_time,
            }

        # Measure coverage
        try:
            coverage_result = self._measure_coverage(valid_statements)
        except Exception as e:
            return {
                "score": 0.0,
                "runs_successfully": 0.0,
                "error": f"Coverage measurement failed: {e}",
                "traceback": traceback.format_exc(),
            }

        if "error" in coverage_result:
            return {
                "score": 0.0,
                "runs_successfully": 0.0,
                **coverage_result,
            }

        # Scoring formula:
        # - Non-linear coverage score (0-70 points) - rewards high coverage more
        # - Efficiency bonus for fewer test cases (0-30 points)
        
        import math
        num_tests = coverage_result["total_statements"]
        line_cov = coverage_result["line_coverage"]
        branch_cov = coverage_result["branch_coverage"]
        
        # Weighted coverage: 60% line + 40% branch
        weighted_cov = 0.6 * line_cov + 0.4 * branch_cov
        
        # Non-linear coverage score: cubic function to reward high coverage more
        # Basic coverage is easy to achieve; advanced coverage is more valuable
        # adjusted_cov = (weighted_cov / 100)^3 * 100
        adjusted_cov = math.pow(weighted_cov / 100, 3) * 100
        
        # Coverage score: 70% weight, scaled to 0-70 points
        coverage_score = 0.7 * adjusted_cov
        
        # Efficiency bonus: fewer test cases = higher bonus (30% weight, 0-30 points)
        # Formula: 30 * 2^(-N/N_ref) where N_ref = 50
        # - 1 test: ~30 points
        # - 50 tests: ~15 points
        # - 200 tests: ~3.75 points
        N_REF = 50
        efficiency_bonus = 30 * math.pow(2, -num_tests / N_REF) if num_tests > 0 else 0
        
        score = coverage_score + efficiency_bonus

        return {
            "score": score,
            "runs_successfully": 1.0,
            "line_coverage": coverage_result["line_coverage"],
            "branch_coverage": coverage_result["branch_coverage"],
            "lines_covered": coverage_result["lines_covered"],
            "total_lines": coverage_result["total_lines"],
            "branches_covered": coverage_result["branches_covered"],
            "total_branches": coverage_result["total_branches"],
            "successful_parses": coverage_result["successful_parses"],
            "failed_parses": coverage_result["failed_parses"],
            "total_statements": coverage_result["total_statements"],
            "coverage_score": coverage_score,
            "efficiency_bonus": efficiency_bonus,
            "elapsed_time": elapsed_time,
            "time_budget": self.time_budget_seconds,
        }


def main():
    parser = argparse.ArgumentParser(description="Grammar Fuzzing Evaluator")
    parser.add_argument("--solution", required=True, help="Path to solution.py")
    parser.add_argument("--out", required=True, help="Path to output results JSON")
    args = parser.parse_args()

    try:
        problem_dir = os.path.dirname(os.path.abspath(__file__))
        result = Evaluator(problem_dir).evaluate(args.solution)
    except Exception as e:
        print(f"[evaluator] ERROR: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        result = {"score": 0.0, "runs_successfully": 0.0, "error": str(e)}

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
