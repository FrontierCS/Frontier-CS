#!/usr/bin/env python3
"""
SQL Parser Fuzzer Evaluator

Evaluates a fuzzer's ability to generate inputs that maximize code coverage
of the target SQL parser within a time budget.
"""

import argparse
import importlib.util
import json
import math
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List

# Add resources to path for imports
HERE = Path(__file__).resolve().parent
RESOURCES_DIR = HERE / "resources"
sys.path.insert(0, str(RESOURCES_DIR))

DEFAULT_SPEC = HERE / "resources" / "submission_spec.json"
ARTIFACT_PATH = Path("./output_ans").resolve()


def load_solution_module(solution_path: Path) -> ModuleType:
    """Load the solution module from the given path."""
    if not solution_path.exists():
        raise FileNotFoundError(f"solution.py not found at {solution_path}")
    spec = importlib.util.spec_from_file_location("submitted_solution", solution_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load spec for {solution_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialize_artifact(result: Any, solution_path: Path) -> Path:
    """Materialize the solution result into an artifact file."""
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(result, dict):
        with ARTIFACT_PATH.open("w", encoding="utf-8") as fout:
            json.dump(result, fout)
        return ARTIFACT_PATH
    if isinstance(result, str):
        # Check if the string could be a file path (reasonable length and no newlines)
        is_possible_path = len(result) < 4096 and '\n' not in result
        if is_possible_path:
            candidate = Path(result)
            try:
                if candidate.is_file():
                    with ARTIFACT_PATH.open("w", encoding="utf-8") as fout:
                        json.dump({"program_path": str(candidate.resolve())}, fout)
                    return ARTIFACT_PATH
            except OSError:
                pass
        # Treat as code string
        with ARTIFACT_PATH.open("w", encoding="utf-8") as fout:
            json.dump({"code": result}, fout)
        return ARTIFACT_PATH
    raise TypeError(
        "Solution.solve() must return a dict/path-string/code-string; got "
        f"{type(result)!r}."
    )


def load_fuzzer_from_artifact(artifact_path: Path) -> Any:
    """Load the fuzz function from the artifact."""
    with artifact_path.open("r", encoding="utf-8") as fin:
        artifact = json.load(fin)
    
    if "code" in artifact:
        # Write code to temporary file and import as module
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(artifact["code"])
                temp_file = f.name
            
            spec = importlib.util.spec_from_file_location("temp_fuzzer_module", temp_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if not hasattr(module, "fuzz"):
                raise ValueError("Code must define a 'fuzz' function")
            
            os.unlink(temp_file)
            return module.fuzz
        except Exception as e:
            try:
                if 'temp_file' in locals():
                    os.unlink(temp_file)
            except:
                pass
            raise
    
    elif "program_path" in artifact:
        program_path = Path(artifact["program_path"])
        if not program_path.exists():
            raise FileNotFoundError(f"Program file not found: {program_path}")
        
        spec = importlib.util.spec_from_file_location("submitted_program", program_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load spec for {program_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, "fuzz"):
            raise ValueError("Program must define a 'fuzz' function")
        return module.fuzz
    
    else:
        raise ValueError("Artifact must contain either 'code' or 'program_path'")


class CoverageTracker:
    """Tracks coverage during fuzzing with parse_sql wrapper."""
    
    def __init__(self, resources_dir: Path):
        self.resources_dir = resources_dir
        self.sql_engine_dir = resources_dir / "sql_engine"
        self.parse_call_count = 0
        self.total_statements = 0
        self.successful_parses = 0
        self.failed_parses = 0
        
        # Import coverage and sql_engine
        import coverage
        self.coverage_module = coverage
        
        # Files to measure coverage on
        self.parser_files = [
            str(self.sql_engine_dir / "parser.py"),
            str(self.sql_engine_dir / "tokenizer.py"),
            str(self.sql_engine_dir / "ast_nodes.py"),
        ]
        
        # Create coverage object
        self.cov = coverage.Coverage(
            branch=True,
            source=[str(self.sql_engine_dir)],
        )
        
        # Import parse_sql
        from sql_engine import parse_sql as _parse_sql
        self._parse_sql = _parse_sql
    
    def start(self):
        """Start coverage tracking."""
        self.cov.start()
    
    def stop(self):
        """Stop coverage tracking."""
        self.cov.stop()
        self.cov.save()
    
    def parse_sql(self, statements: List[str]) -> None:
        """
        Parse a batch of SQL statements.
        
        This function is passed to the fuzzer's fuzz() function.
        """
        self.parse_call_count += 1
        
        if not isinstance(statements, list):
            statements = [statements]
        
        for stmt in statements:
            if not isinstance(stmt, str):
                continue
            self.total_statements += 1
            try:
                self._parse_sql(stmt)
                self.successful_parses += 1
            except Exception:
                self.failed_parses += 1
    
    def get_coverage_result(self) -> Dict[str, Any]:
        """Analyze and return coverage results."""
        total_lines = 0
        covered_lines = 0
        total_branches = 0
        covered_branches = 0
        
        for filepath in self.parser_files:
            if os.path.exists(filepath):
                try:
                    analysis = self.cov.analysis2(filepath)
                    _, executable_lines, excluded_lines, missing_lines, _ = analysis
                    
                    file_total = len(executable_lines)
                    file_covered = file_total - len(missing_lines)
                    total_lines += file_total
                    covered_lines += file_covered
                except Exception:
                    pass
        
        # Get branch coverage
        try:
            for filepath in self.parser_files:
                if os.path.exists(filepath):
                    file_analysis = self.cov._analyze(filepath)
                    if hasattr(file_analysis, 'numbers'):
                        nums = file_analysis.numbers
                        if hasattr(nums, 'n_branches'):
                            total_branches += nums.n_branches
                            if hasattr(nums, 'n_missing_branches'):
                                covered_branches += nums.n_branches - nums.n_missing_branches
        except Exception:
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
            "successful_parses": self.successful_parses,
            "failed_parses": self.failed_parses,
            "total_statements": self.total_statements,
            "parse_call_count": self.parse_call_count,
        }


def evaluate_fuzzer(fuzz_func: Any, resources_dir: Path, time_budget: float = 60.0) -> Dict[str, Any]:
    """
    Run the fuzzer and measure coverage.
    
    Calls fuzz(parse_sql) repeatedly until time budget is exhausted or fuzzer returns False.
    """
    tracker = CoverageTracker(resources_dir)
    
    start_time = time.time()
    fuzz_calls = 0
    
    tracker.start()
    
    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= time_budget:
                break
            
            try:
                result = fuzz_func(tracker.parse_sql)
                fuzz_calls += 1
                
                # If fuzzer returns False, stop early
                if result is False:
                    break
            except Exception as e:
                # Log but continue fuzzing
                print(f"[evaluator] Fuzzer raised exception: {e}", file=sys.stderr)
                fuzz_calls += 1
                # Give the fuzzer a chance to recover on next call
                continue
    finally:
        tracker.stop()
    
    elapsed_time = time.time() - start_time
    coverage_result = tracker.get_coverage_result()
    
    # Calculate score
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
    
    # Efficiency bonus: fewer parse calls = higher bonus (30% weight, 0-30 points)
    # Formula: 30 * 2^(-N/N_ref) where N_ref = 500
    N_REF = 500
    parse_calls = coverage_result["parse_call_count"]
    efficiency_bonus = 30 * math.pow(2, -parse_calls / N_REF) if parse_calls > 0 else 30
    
    score = coverage_score + efficiency_bonus
    
    return {
        "score": score,
        "coverage_score": coverage_score,
        "efficiency_bonus": efficiency_bonus,
        "line_coverage": coverage_result["line_coverage"],
        "branch_coverage": coverage_result["branch_coverage"],
        "lines_covered": coverage_result["lines_covered"],
        "total_lines": coverage_result["total_lines"],
        "branches_covered": coverage_result["branches_covered"],
        "total_branches": coverage_result["total_branches"],
        "successful_parses": coverage_result["successful_parses"],
        "failed_parses": coverage_result["failed_parses"],
        "total_statements": coverage_result["total_statements"],
        "parse_call_count": coverage_result["parse_call_count"],
        "fuzz_calls": fuzz_calls,
        "elapsed_time": elapsed_time,
        "time_budget": time_budget,
    }


def evaluate(solution_path: Path, spec_path: Path = None) -> Dict[str, Any]:
    """Main evaluation function."""
    try:
        # Load solution module
        module = load_solution_module(solution_path)
        
        if not hasattr(module, "Solution"):
            raise ValueError("Solution module must define a 'Solution' class")
        
        solution_class = module.Solution
        solution_instance = solution_class()
        
        if not hasattr(solution_instance, "solve"):
            raise ValueError("Solution class must have a 'solve' method")
        
        # Get solution result
        result = solution_instance.solve(str(RESOURCES_DIR))
        
        # Materialize artifact
        artifact_path = materialize_artifact(result, solution_path)
        
        # Load fuzz function from artifact
        fuzz_func = load_fuzzer_from_artifact(artifact_path)
        
        # Evaluate fuzzer performance
        evaluation_result = evaluate_fuzzer(fuzz_func, RESOURCES_DIR, time_budget=60.0)
        
        return {
            "status": "success",
            "runs_successfully": 1.0,
            "artifact_path": str(artifact_path),
            **evaluation_result,
        }
        
    except Exception as e:
        return {
            "status": "error",
            "runs_successfully": 0.0,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "score": 0,
        }


def main():
    parser = argparse.ArgumentParser(description="Evaluate SQL Parser Fuzzer solutions")
    parser.add_argument(
        "--solution-path",
        "--solution",
        dest="solution_path",
        type=Path,
        default=Path("./solution.py"),
        help="Path to solution.py file",
    )
    parser.add_argument(
        "--spec-path",
        type=Path,
        default=DEFAULT_SPEC,
        help="Path to specification file (unused, for compatibility)",
    )
    parser.add_argument(
        "--output-path",
        "--out",
        dest="output_path",
        type=Path,
        default=Path("./result.json"),
        help="Path to output result file",
    )
    
    args = parser.parse_args()
    
    # Run evaluation
    result = evaluate(args.solution_path, args.spec_path)
    
    # Write result
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    with args.output_path.open("w", encoding="utf-8") as fout:
        json.dump(result, fout, indent=2)
    
    # Print summary
    if result["status"] == "success":
        print(f"Evaluation completed successfully!")
        print(f"Score: {result['score']:.2f}/100")
        print(f"Line coverage: {result['line_coverage']:.2f}%")
        print(f"Branch coverage: {result['branch_coverage']:.2f}%")
        print(f"Coverage score: {result['coverage_score']:.2f}")
        print(f"Efficiency bonus: {result['efficiency_bonus']:.2f}")
        print(f"Total statements parsed: {result['total_statements']}")
        print(f"Parse calls: {result['parse_call_count']}")
        print(f"Fuzz calls: {result['fuzz_calls']}")
        print(f"Elapsed time: {result['elapsed_time']:.2f}s")
        
        # Print score as last line for compatibility
        print(f"{result['score']} {result['score']}")
    else:
        print(f"Evaluation failed: {result['error']}")
        print("0")
        sys.exit(1)


if __name__ == "__main__":
    main()
