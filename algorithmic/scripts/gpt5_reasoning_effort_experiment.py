#!/usr/bin/env python3
"""
GPT-5 Reasoning Effort Experiment Script

For each algorithmic problem, generates 3 solutions with each of 3 reasoning effort levels (low, medium, high).
Tracks token usage statistics for each generation and saves all solutions to the appropriate directories.

Usage:
    python gpt5_reasoning_effort_experiment.py                    # All problems
    python gpt5_reasoning_effort_experiment.py 1 2 3              # Specific problems
    python gpt5_reasoning_effort_experiment.py --dryrun           # Preview mode
    python gpt5_reasoning_effort_experiment.py --force            # Regenerate existing

Output:
    - Solutions: algorithmic/solutions/{problem_id}/gpt5_{effort}_{variant}.cpp
    - Token stats: algorithmic/scripts/gpt5_reasoning_effort_stats.csv
    - Logs: algorithmic/scripts/generation_logs/gpt5_{effort}/...
"""

import sys
import os
import time
import argparse
import re
import csv
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

import requests
from openai import OpenAI, APITimeoutError

# Add project root to path for imports
script_dir = Path(__file__).parent
algo_dir = script_dir.parent
repo_root = algo_dir.parent
sys.path.insert(0, str(repo_root / "src"))

from frontier_cs.gen import ensure_env_loaded


# Reasoning effort levels to test
REASONING_EFFORTS = ["low", "medium", "high"]

# Number of variants per (problem, effort) combination
NUM_VARIANTS = 3

# C++ competitive programming prompt
CPP_SYSTEM_PROMPT = """You are a competitive programmer. You will be given a problem statement, please implement a solution in C++. The execution time and memory limit are also stated in the statement so be aware of the complexity of the program. Please wrap the code in ```cpp and ``` so that it is properly formatted. Your response should ONLY contain the C++ code, with no additional explanation or text."""


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
class TokenUsage:
    """Token usage statistics from a single generation."""
    problem_id: str
    reasoning_effort: str
    variant: int
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    total_tokens: int
    timestamp: str
    duration_seconds: float
    success: bool
    error: Optional[str] = None


@dataclass
class GenerationTask:
    """Represents a single solution generation task."""
    problem_id: str
    statement: str
    reasoning_effort: str
    variant: int
    solution_path: Path


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

    def get_problem_statement(self, problem_id: str) -> Optional[str]:
        """Get the problem statement for a given problem ID."""
        try:
            response = self.session.get(
                f"{self.judge_url}/problem/{problem_id}/statement",
                timeout=30
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching statement for problem {problem_id}: {e}")
            return None


def extract_cpp_code(response_text: str) -> str:
    """Extract C++ code from LLM response."""
    if not response_text:
        return ""

    code = response_text.strip()

    # Try to extract from ```cpp blocks
    cpp_pattern = r'```(?:cpp|c\+\+)?\s*\n(.*?)```'
    matches = re.findall(cpp_pattern, code, re.DOTALL)
    if matches:
        return max(matches, key=len).strip()

    # Fallback: strip markdown if present
    if code.startswith("```cpp"):
        code = code[6:].strip()
    elif code.startswith("```c++"):
        code = code[6:].strip()
    elif code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    return code


def get_solution_path(output_dir: Path, problem_id: str, effort: str, variant: int) -> Path:
    """Get the path for a solution file.
    
    Format: {output_dir}/{problem_id}/gpt5_{effort}_{variant}.cpp
    Example: solutions/1/gpt5_high_0.cpp
    """
    if variant == 0:
        filename = f"gpt5_{effort}.cpp"
    else:
        filename = f"gpt5_{effort}_{variant}.cpp"
    return output_dir / problem_id / filename


def generate_solution(
    statement: str,
    reasoning_effort: str,
    api_key: str,
    timeout: float,
    log_file: Path,
) -> Tuple[str, TokenUsage, Optional[str]]:
    """Generate a C++ solution using GPT-5 with specified reasoning effort.
    
    Returns:
        Tuple of (code, token_usage, error_message)
    """
    user_prompt = f"Problem:\n\n{statement}\n\nGenerate solution code:"
    combined_prompt = f"{CPP_SYSTEM_PROMPT}\n\n{user_prompt}"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_time = time.time()
    
    client = OpenAI(api_key=api_key, timeout=timeout)
    
    # Initialize token usage
    token_usage = TokenUsage(
        problem_id="",  # Will be filled by caller
        reasoning_effort=reasoning_effort,
        variant=0,  # Will be filled by caller
        prompt_tokens=0,
        completion_tokens=0,
        reasoning_tokens=0,
        total_tokens=0,
        timestamp=timestamp,
        duration_seconds=0,
        success=False,
        error=None,
    )
    
    # Write log header
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GPT-5 REASONING EFFORT EXPERIMENT LOG\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Reasoning Effort: {reasoning_effort}\n")
        f.write("=" * 80 + "\n\n")
        f.write("PROMPT:\n")
        f.write("=" * 80 + "\n")
        f.write(combined_prompt)
        f.write("\n\n")
    
    MAX_RETRIES = 3
    RETRY_DELAY = 30
    content: Optional[str] = None
    completion = None
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            completion = client.chat.completions.create(
                model="gpt-5",
                messages=[{"role": "user", "content": combined_prompt}],
                reasoning_effort=reasoning_effort,
            )
            
            if completion.choices and completion.choices[0].message.content:
                content = completion.choices[0].message.content
                break
                
        except APITimeoutError as e:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"TIMEOUT (attempt {attempt}/{MAX_RETRIES}): {e}\n")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                
        except Exception as e:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"ERROR (attempt {attempt}/{MAX_RETRIES}): {e}\n")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
    
    duration = time.time() - start_time
    token_usage.duration_seconds = duration
    
    if content is None:
        token_usage.error = "LLM call failed after retries"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\nFAILED: {token_usage.error}\n")
        return "", token_usage, token_usage.error
    
    # Extract token usage from completion
    if completion and hasattr(completion, 'usage') and completion.usage:
        usage = completion.usage
        token_usage.prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
        token_usage.completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
        token_usage.total_tokens = getattr(usage, 'total_tokens', 0) or 0
        
        # Extract reasoning tokens if available (OpenAI models may include this)
        if hasattr(usage, 'completion_tokens_details') and usage.completion_tokens_details:
            details = usage.completion_tokens_details
            token_usage.reasoning_tokens = getattr(details, 'reasoning_tokens', 0) or 0
    
    token_usage.success = True
    
    # Write to log
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAW OUTPUT:\n")
        f.write("=" * 80 + "\n")
        f.write(content)
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("TOKEN USAGE:\n")
        f.write("=" * 80 + "\n")
        f.write(f"Prompt tokens: {token_usage.prompt_tokens}\n")
        f.write(f"Completion tokens: {token_usage.completion_tokens}\n")
        f.write(f"Reasoning tokens: {token_usage.reasoning_tokens}\n")
        f.write(f"Total tokens: {token_usage.total_tokens}\n")
        f.write(f"Duration: {duration:.2f}s\n")
        f.write("\n")
    
    code = extract_cpp_code(content)
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("EXTRACTED C++ CODE:\n")
        f.write("=" * 80 + "\n")
        f.write(code)
        f.write("\n")
    
    return code, token_usage, None


def save_token_stats(stats: List[TokenUsage], output_path: Path) -> None:
    """Save token usage statistics to CSV file."""
    fieldnames = [
        'problem_id', 'reasoning_effort', 'variant',
        'prompt_tokens', 'completion_tokens', 'reasoning_tokens', 'total_tokens',
        'timestamp', 'duration_seconds', 'success', 'error'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for stat in stats:
            writer.writerow(asdict(stat))
    
    print(f"\n{green('✓')} Token statistics saved to: {green(str(output_path))}")


def main():
    parser = argparse.ArgumentParser(
        description="GPT-5 Reasoning Effort Experiment",
    )
    
    parser.add_argument("problem_ids", nargs="*",
                        help="Problem ID(s) to generate solutions for (default: all)")
    parser.add_argument("--judge-url", default="http://localhost:8081",
                        help="Judge server URL")
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="LLM request timeout in seconds")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate existing solutions")
    parser.add_argument("--dryrun", action="store_true",
                        help="Show what would be generated")
    parser.add_argument("--concurrency", type=int, default=2,
                        help="Maximum parallel generations (be careful with rate limits)")
    parser.add_argument("--efforts", nargs="+", default=REASONING_EFFORTS,
                        choices=REASONING_EFFORTS,
                        help="Reasoning effort levels to test")
    parser.add_argument("--variants", type=int, default=NUM_VARIANTS,
                        help="Number of variants per (problem, effort)")
    
    args = parser.parse_args()
    
    # Load environment variables
    ensure_env_loaded()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(f"{red('ERROR:')} OPENAI_API_KEY not set")
        sys.exit(1)
    
    # Output directories
    output_dir = algo_dir / "solutions"
    logs_dir = script_dir / "generation_logs"
    stats_path = script_dir / "gpt5_reasoning_effort_stats.csv"
    
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
    
    # Build tasks
    tasks: List[GenerationTask] = []
    skipped: List[str] = []
    statements_cache: Dict[str, str] = {}
    
    for problem_id in problem_ids:
        # Fetch statement once per problem
        if problem_id not in statements_cache:
            statement = judge.get_problem_statement(problem_id)
            if not statement:
                print(f"{yellow('WARNING:')} Could not get statement for problem {problem_id}")
                continue
            statements_cache[problem_id] = statement
        
        statement = statements_cache[problem_id]
        
        for effort in args.efforts:
            for variant in range(args.variants):
                sol_path = get_solution_path(output_dir, problem_id, effort, variant)
                sol_name = str(sol_path.relative_to(output_dir))
                
                if sol_path.exists() and not args.force:
                    skipped.append(sol_name)
                    continue
                
                tasks.append(GenerationTask(
                    problem_id=problem_id,
                    statement=statement,
                    reasoning_effort=effort,
                    variant=variant,
                    solution_path=sol_path,
                ))
    
    # Print plan
    print(f"\n{'=' * 60}")
    if args.dryrun:
        print(yellow(bold("DRYRUN MODE - No changes will be made")))
    else:
        print(cyan(bold("GPT-5 REASONING EFFORT EXPERIMENT")))
    print(f"{'=' * 60}\n")
    
    print(f"{bold('Configuration:')}")
    print(f"  Problems: {blue(str(len(problem_ids)))}")
    print(f"  Reasoning efforts: {blue(', '.join(args.efforts))}")
    print(f"  Variants per effort: {blue(str(args.variants))}")
    print(f"  Total generations: {blue(str(len(problem_ids) * len(args.efforts) * args.variants))}")
    print(f"  Output: {blue(str(output_dir))}")
    print(f"  Stats: {blue(str(stats_path))}")
    print()
    
    if tasks:
        print(f"{green('Will generate')} {green(bold(str(len(tasks))))} solution(s)")
    else:
        print(dim("No new solutions to generate."))
    
    if skipped:
        print(f"{yellow('Skipping')} {yellow(bold(str(len(skipped))))} existing (use --force)")
    
    print(f"\n{'=' * 60}\n")
    
    if args.dryrun:
        # Show what would be generated
        for task in tasks[:20]:  # Show first 20
            print(f"  Would generate: {task.solution_path.relative_to(output_dir)}")
        if len(tasks) > 20:
            print(f"  ... and {len(tasks) - 20} more")
        return
    
    if not tasks:
        return
    
    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    
    # Create per-effort log directories
    for effort in args.efforts:
        (logs_dir / f"gpt5_{effort}").mkdir(exist_ok=True)
    
    # Execute tasks
    all_stats: List[TokenUsage] = []
    generated: List[str] = []
    failed: List[str] = []
    
    def execute_task(task: GenerationTask) -> Tuple[str, TokenUsage]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"gpt5_{task.reasoning_effort}" / f"{task.problem_id}_{task.variant}_{timestamp}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        sol_name = str(task.solution_path.relative_to(output_dir))
        print(f"{cyan('▶')} Generating {sol_name} "
              f"({dim('effort:')} {task.reasoning_effort}, {dim('variant:')} {task.variant})")
        
        try:
            code, token_usage, error = generate_solution(
                task.statement,
                task.reasoning_effort,
                api_key,
                args.timeout,
                log_file,
            )
            
            # Update token usage with task info
            token_usage.problem_id = task.problem_id
            token_usage.variant = task.variant
            
            if error:
                print(f"  {red('✗')} {red('ERROR:')} {error}")
                return ("failed", token_usage)
            
            # Save solution
            task.solution_path.parent.mkdir(parents=True, exist_ok=True)
            task.solution_path.write_text(code, encoding="utf-8")
            print(f"  {green('✓')} Saved: {green(sol_name)}")
            print(f"      Tokens: prompt={token_usage.prompt_tokens}, "
                  f"completion={token_usage.completion_tokens}, "
                  f"reasoning={token_usage.reasoning_tokens}, "
                  f"total={token_usage.total_tokens}")
            
            return ("generated", token_usage)
            
        except Exception as exc:
            print(f"  {red('✗')} {red('ERROR:')} {exc}")
            token_usage = TokenUsage(
                problem_id=task.problem_id,
                reasoning_effort=task.reasoning_effort,
                variant=task.variant,
                prompt_tokens=0,
                completion_tokens=0,
                reasoning_tokens=0,
                total_tokens=0,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                duration_seconds=0,
                success=False,
                error=str(exc),
            )
            return ("failed", token_usage)
    
    # Run tasks
    max_workers = min(args.concurrency, len(tasks))
    print(f"{cyan('▶')} Starting generation ({bold(str(len(tasks)))} tasks, concurrency={max_workers})...\n")
    
    # Use sequential execution for low concurrency to avoid rate limits
    if max_workers <= 1:
        for task in tasks:
            status, token_usage = execute_task(task)
            all_stats.append(token_usage)
            sol_name = str(task.solution_path.relative_to(output_dir))
            if status == "generated":
                generated.append(sol_name)
            else:
                failed.append(sol_name)
            # Small delay between requests to avoid rate limits
            time.sleep(1)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(execute_task, task): task for task in tasks}
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                status, token_usage = future.result()
                all_stats.append(token_usage)
                sol_name = str(task.solution_path.relative_to(output_dir))
                if status == "generated":
                    generated.append(sol_name)
                else:
                    failed.append(sol_name)
    
    # Save token statistics
    save_token_stats(all_stats, stats_path)
    
    # Print summary
    print(f"\n{'=' * 60}")
    print(cyan(bold("GENERATION SUMMARY")))
    print(f"{'=' * 60}\n")
    
    if generated:
        print(f"{green('Generated:')} {green(bold(str(len(generated))))}")
    if failed:
        print(f"{red('Failed:')} {red(bold(str(len(failed))))}")
    if skipped:
        print(f"{yellow('Skipped:')} {yellow(bold(str(len(skipped))))}")
    
    # Token usage summary by effort level
    print(f"\n{bold('Token Usage by Reasoning Effort:')}")
    for effort in args.efforts:
        effort_stats = [s for s in all_stats if s.reasoning_effort == effort and s.success]
        if effort_stats:
            avg_prompt = sum(s.prompt_tokens for s in effort_stats) / len(effort_stats)
            avg_completion = sum(s.completion_tokens for s in effort_stats) / len(effort_stats)
            avg_reasoning = sum(s.reasoning_tokens for s in effort_stats) / len(effort_stats)
            avg_total = sum(s.total_tokens for s in effort_stats) / len(effort_stats)
            avg_duration = sum(s.duration_seconds for s in effort_stats) / len(effort_stats)
            
            print(f"\n  {bold(effort.upper())} ({len(effort_stats)} successful generations):")
            print(f"    Avg prompt tokens:     {avg_prompt:,.0f}")
            print(f"    Avg completion tokens: {avg_completion:,.0f}")
            print(f"    Avg reasoning tokens:  {avg_reasoning:,.0f}")
            print(f"    Avg total tokens:      {avg_total:,.0f}")
            print(f"    Avg duration:          {avg_duration:.1f}s")
    
    print()


if __name__ == "__main__":
    main()
