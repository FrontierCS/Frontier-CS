#!/usr/bin/env python3
"""Common evaluator logic for N-body simulation problem.

This module contains shared evaluation logic used by all variants.
Variant-specific evaluators configure parameters and call these functions.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class VariantConfig:
    """Configuration for a specific problem variant."""
    num_particles: int
    num_iterations: int
    space_size: float
    num_runs: int
    # Scoring: maps speedup range [min_speedup, max_speedup] to [0, 100]
    min_speedup: float  # Speedup that gives 0 points
    max_speedup: float  # Speedup that gives 100 points


def compile_and_run(
    solution_path: Path,
    work_dir: Path,
    common_dir: Path,
    config: VariantConfig
) -> Dict[str, Any]:
    """Compile the submitted C++ code with benchmark harness and run it."""
    
    # Copy common files to work directory
    shutil.copy(common_dir / "world.h", work_dir / "world.h")
    shutil.copy(common_dir / "timing.h", work_dir / "timing.h")
    shutil.copy(common_dir / "benchmark.cpp", work_dir / "benchmark.cpp")
    shutil.copy(common_dir / "baseline.cpp", work_dir / "baseline.cpp")
    
    # Copy the submitted solution
    shutil.copy(solution_path, work_dir / "solution.cpp")
    
    # Create combined source that includes solution, baseline, and benchmark
    combined_source = '''
#include "solution.cpp"
#include "baseline.cpp"
#include "benchmark.cpp"
'''
    combined_file = work_dir / "combined.cpp"
    combined_file.write_text(combined_source)
    
    # Compile
    output_binary = work_dir / "nbody_benchmark"
    compile_cmd = [
        "g++", "-O2", "-fopenmp", "-std=c++17",
        "-I", str(work_dir),
        "-o", str(output_binary),
        str(combined_file)
    ]
    
    compile_result = subprocess.run(
        compile_cmd,
        capture_output=True,
        text=True,
        cwd=work_dir
    )
    
    if compile_result.returncode != 0:
        return {
            "status": "compile_error",
            "error": compile_result.stderr,
            "score": 0,
        }
    
    # Run benchmark
    result_file = work_dir / "result.txt"
    run_cmd = [
        str(output_binary),
        "-n", str(config.num_particles),
        "-i", str(config.num_iterations),
        "-s", str(config.space_size),
        "-r", str(config.num_runs),
        "-o", str(result_file)
    ]
    
    run_result = subprocess.run(
        run_cmd,
        capture_output=True,
        text=True,
        cwd=work_dir,
        timeout=600  # 10 minute timeout
    )
    
    # Parse results
    if not result_file.exists():
        return {
            "status": "runtime_error",
            "error": run_result.stderr or "No result file generated",
            "stdout": run_result.stdout,
            "score": 0,
        }
    
    results = {}
    with open(result_file) as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                results[key] = value
    
    return {
        "status": "success",
        "sequential_time": float(results.get("sequential_time", 0)),
        "parallel_time": float(results.get("parallel_time", 0)),
        "speedup": float(results.get("speedup", 1)),
        "correct": results.get("correct", "false") == "true",
        "stdout": run_result.stdout,
        "stderr": run_result.stderr,
    }


def calculate_score(speedup: float, correct: bool, config: VariantConfig) -> tuple[float, float]:
    """Calculate bounded and unbounded scores.
    
    Score mapping:
    - min_speedup = 0 points
    - max_speedup = 100 points
    - Linear interpolation between
    - Capped at 100 for bounded, unbounded can exceed
    """
    if not correct:
        return 0.0, 0.0
    
    # Linear mapping from [min_speedup, max_speedup] to [0, 100]
    speedup_range = config.max_speedup - config.min_speedup
    raw_score = (speedup - config.min_speedup) / speedup_range * 100.0
    
    bounded_score = max(0.0, min(100.0, raw_score))
    unbounded_score = max(0.0, raw_score)
    
    return bounded_score, unbounded_score


def evaluate(
    solution_path: Path,
    common_dir: Path,
    config: VariantConfig
) -> Dict[str, Any]:
    """Main evaluation function."""
    
    try:
        if not solution_path.exists():
            raise FileNotFoundError(f"Solution file not found: {solution_path}")
        
        # Check file extension
        if solution_path.suffix != ".cpp":
            raise ValueError(f"Solution must be a .cpp file, got: {solution_path.suffix}")
        
        # Create temp directory and run
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            run_result = compile_and_run(solution_path, work_dir, common_dir, config)
        
        if run_result["status"] != "success":
            return {
                "status": run_result["status"],
                "error": run_result.get("error", "Unknown error"),
                "score": 0,
                "score_unbounded": 0,
            }
        
        # Calculate score
        bounded, unbounded = calculate_score(
            run_result["speedup"],
            run_result["correct"],
            config
        )
        
        return {
            "status": "success",
            "sequential_time": run_result["sequential_time"],
            "parallel_time": run_result["parallel_time"],
            "speedup": run_result["speedup"],
            "correct": run_result["correct"],
            "score": bounded,
            "score_unbounded": unbounded,
            "stdout": run_result.get("stdout", ""),
            "stderr": run_result.get("stderr", ""),
        }
        
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "error": "Execution timed out",
            "score": 0,
            "score_unbounded": 0,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "score": 0,
            "score_unbounded": 0,
        }


def run_evaluator(config: VariantConfig, default_spec: Path):
    """Main entry point for variant evaluators."""
    parser = argparse.ArgumentParser(description="Evaluate N-body simulation solutions")
    parser.add_argument(
        "--solution-path",
        type=Path,
        default=Path("./solution.cpp"),
        help="Path to solution.cpp file",
    )
    parser.add_argument(
        "--spec-path",
        type=Path,
        default=default_spec,
        help="Path to specification file",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("./result.json"),
        help="Path to output result file",
    )
    
    args = parser.parse_args()
    
    # Determine common directory (parent of the variant directory)
    here = Path(__file__).resolve().parent
    common_dir = here  # evaluator_common.py is already in common/
    
    # Run evaluation
    result = evaluate(args.solution_path, common_dir, config)
    
    # Write result
    with args.output_path.open("w", encoding="utf-8") as fout:
        json.dump(result, fout, indent=2)
    
    # Print benchmark output
    if result.get("stdout"):
        print(result["stdout"])
    
    # Print summary
    if result["status"] == "success":
        print(f"Evaluation completed successfully!")
        print(f"Speedup: {result.get('speedup', 0):.3f}x")
        print(f"Correct: {result.get('correct', False)}")
        print(f"Score: {result.get('score', 0):.2f}/100")
        # Print stderr if correctness failed (contains mismatch details)
        if not result.get('correct', False) and result.get('stderr'):
            print(f"Correctness error details:\n{result.get('stderr')}")
        # Print score as last line for framework to extract
        score = result.get("score", 0)
        score_unbounded = result.get("score_unbounded", score)
        print(f"{score} {score_unbounded}")
    else:
        print(f"Evaluation failed: {result.get('error', 'Unknown error')}")
        print("0")
        sys.exit(1)

