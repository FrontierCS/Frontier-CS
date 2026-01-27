#!/usr/bin/env python3
"""
Evaluate GPT-5 Reasoning Effort Solutions

Submits all gpt5_{low,medium,high} solutions to the judge, collects scores,
extracts token usage from logs, and writes everything to a CSV file.

Usage:
    python evaluate_gpt5_reasoning_effort.py                    # All problems
    python evaluate_gpt5_reasoning_effort.py 0 1 2              # Specific problems
    python evaluate_gpt5_reasoning_effort.py --dryrun           # Preview mode
"""

import sys
import os
import re
import csv
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Add project root to path
script_dir = Path(__file__).parent
algo_dir = script_dir.parent
repo_root = algo_dir.parent
sys.path.insert(0, str(repo_root / "src"))


# Terminal formatting helpers
def bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"

def dim(s: str) -> str:
    return f"\033[2m{s}\033[0m"

def red(s: str) -> str:
    return f"\033[91m{s}\033[0m"

def green(s: str) -> str:
    return f"\033[92m{s}\033[0m"

def yellow(s: str) -> str:
    return f"\033[93m{s}\033[0m"

def blue(s: str) -> str:
    return f"\033[94m{s}\033[0m"

def cyan(s: str) -> str:
    return f"\033[96m{s}\033[0m"


@dataclass
class EvaluationResult:
    """Result of evaluating a single solution."""
    problem_id: str
    reasoning_effort: str
    variant: int
    solution_file: str
    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    generation_duration: float = 0.0
    # Judge result
    score: float = 0.0
    status: str = ""
    verdict: str = ""
    compile_error: bool = False
    runtime_error: bool = False
    # Metadata
    timestamp: str = ""
    error: Optional[str] = None


class AlgorithmicJudgeClient:
    """Client for interacting with the algorithmic judge server."""

    def __init__(self, judge_url: str = "http://localhost:8081"):
        self.judge_url = judge_url.rstrip("/")
        self.session = requests.Session()

    def is_available(self) -> bool:
        """Check if the judge server is available."""
        try:
            response = self.session.get(f"{self.judge_url}/problems", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_all_problems(self) -> List[str]:
        """Get list of all problem IDs."""
        try:
            response = self.session.get(f"{self.judge_url}/problems", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [str(p['id']) for p in data.get('problems', [])]
        except requests.RequestException as e:
            print(f"Error fetching problems from judge: {e}")
            return []

    def submit_solution(self, problem_id: str, code: str) -> Optional[str]:
        """Submit a solution and return the submission ID."""
        try:
            files = {'code': ('solution.cpp', code)}
            data = {'pid': problem_id, 'lang': 'cpp'}
            response = self.session.post(
                f"{self.judge_url}/submit",
                files=files,
                data=data,
                timeout=600
            )
            response.raise_for_status()
            return response.json().get('sid')
        except requests.RequestException as e:
            print(f"Error submitting solution for problem {problem_id}: {e}")
            return None

    def get_result(self, submission_id: str, poll_interval: float = 2.0, max_wait: float = 1200.0) -> Dict:
        """Poll for submission result."""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = self.session.get(
                    f"{self.judge_url}/result/{submission_id}",
                    timeout=10
                )
                if response.status_code == 404:
                    time.sleep(poll_interval)
                    continue
                response.raise_for_status()
                result = response.json()
                if result.get('status') in ['done', 'error']:
                    return result
                time.sleep(poll_interval)
            except requests.RequestException:
                time.sleep(poll_interval)
        return {"status": "error", "error": "Timeout waiting for result", "score": 0}


def parse_solution_filename(filename: str) -> Optional[Tuple[str, int]]:
    """Parse solution filename to extract reasoning effort and variant.
    
    Examples:
        gpt5_high.cpp -> ("high", 0)
        gpt5_low_1.cpp -> ("low", 1)
        gpt5_medium_2.cpp -> ("medium", 2)
    
    Returns None for non-matching files.
    """
    # Pattern: gpt5_{effort}.cpp or gpt5_{effort}_{variant}.cpp
    pattern = r'^gpt5_(low|medium|high)(?:_(\d+))?\.cpp$'
    match = re.match(pattern, filename)
    if not match:
        return None
    
    effort = match.group(1)
    variant = int(match.group(2)) if match.group(2) else 0
    return (effort, variant)


def find_log_file(logs_dir: Path, effort: str, problem_id: str, variant: int) -> Optional[Path]:
    """Find the log file for a given solution."""
    effort_dir = logs_dir / f"gpt5_{effort}"
    if not effort_dir.exists():
        return None
    
    # Log files are named: {problem_id}_{variant}_{timestamp}.log
    pattern = f"{problem_id}_{variant}_*.log"
    matches = list(effort_dir.glob(pattern))
    
    if not matches:
        return None
    
    # Return the most recent one
    return max(matches, key=lambda p: p.stat().st_mtime)


def extract_token_usage(log_file: Path) -> Dict[str, float]:
    """Extract token usage from a log file."""
    result = {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'reasoning_tokens': 0,
        'total_tokens': 0,
        'duration': 0.0,
    }
    
    if not log_file or not log_file.exists():
        return result
    
    try:
        content = log_file.read_text(encoding='utf-8')
        
        # Extract token counts
        patterns = {
            'prompt_tokens': r'Prompt tokens:\s*(\d+)',
            'completion_tokens': r'Completion tokens:\s*(\d+)',
            'reasoning_tokens': r'Reasoning tokens:\s*(\d+)',
            'total_tokens': r'Total tokens:\s*(\d+)',
            'duration': r'Duration:\s*([\d.]+)s',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                result[key] = float(match.group(1))
        
    except Exception as e:
        print(f"Warning: Could not parse log file {log_file}: {e}")
    
    return result


def evaluate_solution(
    judge: AlgorithmicJudgeClient,
    problem_id: str,
    solution_path: Path,
    effort: str,
    variant: int,
    logs_dir: Path,
) -> EvaluationResult:
    """Evaluate a single solution."""
    result = EvaluationResult(
        problem_id=problem_id,
        reasoning_effort=effort,
        variant=variant,
        solution_file=solution_path.name,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    
    # Extract token usage from log
    log_file = find_log_file(logs_dir, effort, problem_id, variant)
    if log_file:
        token_info = extract_token_usage(log_file)
        result.prompt_tokens = int(token_info['prompt_tokens'])
        result.completion_tokens = int(token_info['completion_tokens'])
        result.reasoning_tokens = int(token_info['reasoning_tokens'])
        result.total_tokens = int(token_info['total_tokens'])
        result.generation_duration = token_info['duration']
    
    # Read solution code
    try:
        code = solution_path.read_text(encoding='utf-8')
    except Exception as e:
        result.error = f"Could not read solution: {e}"
        result.status = "error"
        return result
    
    # Submit to judge
    submission_id = judge.submit_solution(problem_id, code)
    if not submission_id:
        result.error = "Failed to submit solution"
        result.status = "error"
        return result
    
    # Wait for result
    judge_result = judge.get_result(submission_id)
    
    result.status = judge_result.get('status', 'unknown')
    result.score = float(judge_result.get('score', 0))
    result.verdict = judge_result.get('verdict', '')
    
    # Check for errors
    if 'compile' in result.verdict.lower() or 'compilation' in result.verdict.lower():
        result.compile_error = True
    if 'runtime' in result.verdict.lower() or 'error' in result.verdict.lower():
        result.runtime_error = True
    
    if judge_result.get('error'):
        result.error = judge_result['error']
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate GPT-5 Reasoning Effort Solutions",
    )
    
    parser.add_argument("problem_ids", nargs="*",
                        help="Problem ID(s) to evaluate (default: all)")
    parser.add_argument("--judge-url", default="http://localhost:8081",
                        help="Judge server URL")
    parser.add_argument("--dryrun", action="store_true",
                        help="Show what would be evaluated")
    parser.add_argument("--concurrency", type=int, default=16,
                        help="Maximum parallel evaluations")
    parser.add_argument("--output", type=str, default="gpt5_reasoning_effort_results.csv",
                        help="Output CSV file name")
    
    args = parser.parse_args()
    
    # Directories
    solutions_dir = algo_dir / "solutions"
    logs_dir = script_dir / "generation_logs"
    output_path = script_dir / args.output
    
    # Initialize judge client
    judge = AlgorithmicJudgeClient(args.judge_url)
    
    if not judge.is_available():
        print(f"{red('ERROR:')} Judge server not available at {args.judge_url}")
        print("Start the judge with: cd algorithmic && docker compose up -d")
        sys.exit(1)
    
    # Get problem list
    if args.problem_ids:
        problem_ids = args.problem_ids
    else:
        problem_ids = judge.get_all_problems()
        if not problem_ids:
            print(f"{red('ERROR:')} No problems found on judge server")
            sys.exit(1)
        print(f"Auto-discovered {len(problem_ids)} problems from judge")
    
    # Find all matching solutions
    tasks: List[Tuple[str, Path, str, int]] = []  # (problem_id, path, effort, variant)
    
    for problem_id in problem_ids:
        problem_dir = solutions_dir / problem_id
        if not problem_dir.exists():
            continue
        
        for solution_file in problem_dir.iterdir():
            if not solution_file.is_file():
                continue
            
            parsed = parse_solution_filename(solution_file.name)
            if parsed:
                effort, variant = parsed
                tasks.append((problem_id, solution_file, effort, variant))
    
    # Sort tasks by problem_id (numeric), then effort, then variant
    def sort_key(t):
        pid, path, effort, variant = t
        effort_order = {'low': 0, 'medium': 1, 'high': 2}
        try:
            pid_num = int(pid)
        except ValueError:
            pid_num = float('inf')
        return (pid_num, effort_order.get(effort, 99), variant)
    
    tasks.sort(key=sort_key)
    
    # Print plan
    print(f"\n{'=' * 60}")
    if args.dryrun:
        print(yellow(bold("DRYRUN MODE - No evaluations will be performed")))
    else:
        print(cyan(bold("GPT-5 REASONING EFFORT EVALUATION")))
    print(f"{'=' * 60}\n")
    
    print(f"{bold('Configuration:')}")
    print(f"  Problems: {blue(str(len(problem_ids)))}")
    print(f"  Solutions to evaluate: {blue(str(len(tasks)))}")
    print(f"  Output: {blue(str(output_path))}")
    print()
    
    # Count by effort
    effort_counts = {'low': 0, 'medium': 0, 'high': 0}
    for _, _, effort, _ in tasks:
        effort_counts[effort] = effort_counts.get(effort, 0) + 1
    
    print(f"{bold('Solutions by effort:')}")
    for effort, count in effort_counts.items():
        print(f"  {effort}: {blue(str(count))}")
    
    print(f"\n{'=' * 60}\n")
    
    if args.dryrun:
        for pid, path, effort, variant in tasks[:30]:
            print(f"  Would evaluate: {path.relative_to(solutions_dir)}")
        if len(tasks) > 30:
            print(f"  ... and {len(tasks) - 30} more")
        return
    
    if not tasks:
        print(dim("No solutions to evaluate."))
        return
    
    # Execute evaluations
    all_results: List[EvaluationResult] = []
    
    def execute_evaluation(task: Tuple[str, Path, str, int]) -> EvaluationResult:
        problem_id, solution_path, effort, variant = task
        rel_path = solution_path.relative_to(solutions_dir)
        print(f"{cyan('▶')} Evaluating {rel_path}")
        
        # Create a new judge client for each thread to avoid session conflicts
        thread_judge = AlgorithmicJudgeClient(args.judge_url)
        
        result = evaluate_solution(
            thread_judge, problem_id, solution_path, effort, variant, logs_dir
        )
        
        if result.error:
            print(f"  {red('✗')} {red('ERROR:')} {result.error}")
        else:
            score_color = green if result.score > 0 else red
            print(f"  {green('✓')} Score: {score_color(f'{result.score:.2f}')}, "
                  f"Tokens: {result.total_tokens}, "
                  f"Reasoning: {result.reasoning_tokens}")
        
        return result
    
    print(f"{cyan('▶')} Starting evaluation ({bold(str(len(tasks)))} solutions)...\n")
    
    # Run evaluations with limited concurrency
    max_workers = min(args.concurrency, len(tasks))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(execute_evaluation, task): task for task in tasks}
        for future in as_completed(future_to_task):
            result = future.result()
            all_results.append(result)
    
    # Sort results
    all_results.sort(key=lambda r: (
        int(r.problem_id) if r.problem_id.isdigit() else float('inf'),
        {'low': 0, 'medium': 1, 'high': 2}.get(r.reasoning_effort, 99),
        r.variant
    ))
    
    # Save to CSV
    fieldnames = [
        'problem_id', 'reasoning_effort', 'variant', 'solution_file',
        'prompt_tokens', 'completion_tokens', 'reasoning_tokens', 'total_tokens',
        'generation_duration', 'score', 'status', 'verdict',
        'compile_error', 'runtime_error', 'timestamp', 'error'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in all_results:
            writer.writerow(asdict(result))
    
    print(f"\n{green('✓')} Results saved to: {green(str(output_path))}")
    
    # Print summary
    print(f"\n{'=' * 60}")
    print(cyan(bold("EVALUATION SUMMARY")))
    print(f"{'=' * 60}\n")
    
    successful = [r for r in all_results if r.score > 0]
    failed = [r for r in all_results if r.score == 0 or r.error]
    
    print(f"Total evaluated: {bold(str(len(all_results)))}")
    print(f"  Successful (score > 0): {green(bold(str(len(successful))))}")
    print(f"  Failed/Zero score: {red(bold(str(len(failed))))}")
    
    # Summary by effort level
    print(f"\n{bold('Results by Reasoning Effort:')}")
    for effort in ['low', 'medium', 'high']:
        effort_results = [r for r in all_results if r.reasoning_effort == effort]
        if not effort_results:
            continue
        
        successful_effort = [r for r in effort_results if r.score > 0]
        avg_score = sum(r.score for r in effort_results) / len(effort_results) if effort_results else 0
        avg_tokens = sum(r.total_tokens for r in effort_results) / len(effort_results) if effort_results else 0
        avg_reasoning = sum(r.reasoning_tokens for r in effort_results) / len(effort_results) if effort_results else 0
        
        print(f"\n  {bold(effort.upper())} ({len(effort_results)} solutions):")
        print(f"    Success rate: {len(successful_effort)}/{len(effort_results)} ({100*len(successful_effort)/len(effort_results):.1f}%)")
        print(f"    Avg score: {avg_score:.2f}")
        print(f"    Avg total tokens: {avg_tokens:,.0f}")
        print(f"    Avg reasoning tokens: {avg_reasoning:,.0f}")
    
    print()


if __name__ == "__main__":
    main()
