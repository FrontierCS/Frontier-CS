#!/usr/bin/env python3
"""
Generate LLM solutions for algorithmic (C++) problems.

Fetches problem statements from the judge server and generates C++ solutions.

Usage:
    python generate_solutions.py --model gpt-5                # All problems from judge
    python generate_solutions.py 1 --model gpt-5              # Single problem
    python generate_solutions.py 1 2 3 --model gpt-5          # Multiple problems
    python generate_solutions.py --model gpt-5 --variants 4   # 4 solutions per problem
    python generate_solutions.py --dryrun --model gpt-5       # Preview mode
"""

import sys
import os
import time
import argparse
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

import requests

from frontier_cs.models import get_model_prefix, is_reasoning_model
from frontier_cs.gen import (
    build_key_pools, get_fallback_api_key, APIKeyPool,
    ensure_env_loaded, precheck_required_providers,
    instantiate_llm_client, detect_provider,
    bold, dim, red, green, yellow, blue, cyan,
    model_name, problem_name as format_problem_name, solution_name as format_solution_name,
    get_failed_path, write_failed_marker,
    resolve_models,
    print_generation_summary,
)
from frontier_cs.gen.solution_format import get_solution_path


# C++ competitive programming prompt
CPP_SYSTEM_PROMPT = """You are a competitive programmer. You will be given a problem statement, please implement a solution in C++. The execution time and memory limit are also stated in the statement so be aware of the complexity of the program. Please wrap the code in ```cpp and ``` so that it is properly formatted. Your response should ONLY contain the C++ code, with no additional explanation or text."""


@dataclass
class GenerationTask:
    """Represents a single solution generation task."""
    problem_id: str
    statement: str
    model: str
    provider: str
    reasoning_model: bool
    variant_index: int
    solution_name: str
    total_variants: int = 1


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

    def submit_solution(self, problem_id: str, code: str) -> Optional[str]:
        """Submit a solution and return the submission ID."""
        try:
            files = {'code': ('solution.cpp', code)}
            data = {'pid': problem_id, 'lang': 'cpp'}
            response = self.session.post(
                f"{self.judge_url}/submit",
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('sid')
        except requests.RequestException as e:
            print(f"Error submitting solution for problem {problem_id}: {e}")
            return None

    def get_result(self, submission_id: str, poll_interval: float = 2.0, max_wait: float = 300.0) -> Dict[str, Any]:
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


def read_solution_indices(path: Path) -> List[int]:
    """Read solution indices from file (one integer per line)."""
    if not path.is_file():
        return [0]
    indices = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            indices.append(int(line))
    return indices or [0]


def generate_code(
    statement: str,
    *,
    model: str,
    api_key: Optional[str],
    log_file: Path,
    is_reasoning_model: bool,
    timeout: float,
) -> str:
    """Generate C++ solution code using an LLM."""
    user_prompt = f"Problem:\n\n{statement}\n\nGenerate solution code:"
    combined_prompt = f"{CPP_SYSTEM_PROMPT}\n\n{user_prompt}"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    llm_client, llm_config = instantiate_llm_client(
        model,
        is_reasoning_model=is_reasoning_model,
        timeout=timeout,
        base_url=None,
        api_key=api_key,
    )

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ALGORITHMIC SOLUTION GENERATION LOG\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"MODEL: {model}\n")
        f.write(f"INTERFACE CLASS: {llm_client.__class__.__name__}\n")
        for key, value in llm_config.items():
            f.write(f"{key.upper()}: {value}\n")
        f.write(f"TIMEOUT: {timeout}s\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("PROMPT:\n")
        f.write("=" * 80 + "\n")
        f.write(combined_prompt)
        f.write("\n\n")

    print(f"  Calling LLM (model: {model})...")

    MAX_RETRIES = 3
    RETRY_DELAY = 30
    content: Optional[str] = None

    for attempt in range(1, MAX_RETRIES + 1):
        response_text, meta = llm_client.call_llm(combined_prompt)
        if response_text and not response_text.strip().lower().startswith("error:"):
            content = response_text
            break

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"ERROR (attempt {attempt}/{MAX_RETRIES}): {response_text or 'Empty'}\n")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)

    if content is None:
        raise RuntimeError("LLM call failed after retries")

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAW OUTPUT:\n")
        f.write("=" * 80 + "\n")
        f.write(content)
        f.write("\n\n")

    code = extract_cpp_code(content)

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("EXTRACTED C++ CODE:\n")
        f.write("=" * 80 + "\n")
        f.write(code)
        f.write("\n")

    return code


def main():
    script_dir = Path(__file__).parent
    algo_dir = script_dir.parent
    repo_root = algo_dir.parent

    parser = argparse.ArgumentParser(
        description="Generate LLM solutions for algorithmic (C++) problems",
    )

    # Problem selection (default: all problems from judge)
    parser.add_argument("problem_ids", nargs="*",
                        help="Problem ID(s) to generate solutions for")
    parser.add_argument("--problem", dest="problems", nargs="+",
                        help="Problem ID(s) to generate solutions for")
    parser.add_argument("--problems-file", dest="problems_file", default=None,
                        help="File containing problem IDs (default: auto-discover from judge)")

    # Model selection
    model_group = parser.add_mutually_exclusive_group()
    model_group.add_argument("--model", dest="models", nargs="+",
                             help="Model identifier(s)")
    model_group.add_argument("--models-file", help="File with model list")

    # Judge configuration
    parser.add_argument("--judge-url", default="http://localhost:8081",
                        help="Judge server URL")

    # Generation parameters
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="LLM request timeout in seconds")
    parser.add_argument("--indices", type=int, default=None,
                        help="Number of solutions to generate (e.g., --indices 4)")
    parser.add_argument("--indices-file", dest="indices_file", default="indices.txt",
                        help="File with solution indices to generate")

    # Execution control
    parser.add_argument("--force", action="store_true",
                        help="Regenerate existing solutions")
    parser.add_argument("--only-failed", action="store_true",
                        help="Only regenerate solutions that previously failed (.FAILED files)")
    parser.add_argument("--mark-failed", action="store_true",
                        help="Create .FAILED files for missing solutions without generating (for tracking)")
    parser.add_argument("--dryrun", action="store_true",
                        help="Show what would be generated")
    parser.add_argument("--concurrency", type=int, default=4,
                        help="Maximum parallel generations")

    args = parser.parse_args()

    # Output directory for algorithmic solutions
    output_dir = algo_dir / "solutions"

    # Initialize judge client
    judge = AlgorithmicJudgeClient(args.judge_url)

    if not judge.is_available():
        print(f"{red('ERROR:')} Judge server not available at {args.judge_url}")
        print("Start the judge with: cd algorithmic && docker compose up -d")
        sys.exit(1)

    # Get problem list (positional args take precedence, default: all from judge)
    if args.problem_ids:
        problem_ids = args.problem_ids
    elif args.problems:
        problem_ids = args.problems
    elif args.problems_file:
        problems_path = Path(args.problems_file)
        if not problems_path.is_absolute():
            problems_path = script_dir / problems_path
        if not problems_path.is_file():
            print(f"{red('ERROR:')} Problems file not found: {problems_path}")
            sys.exit(1)
        problem_ids = [
            line.strip() for line in problems_path.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not problem_ids:
            print(f"{red('ERROR:')} No problems found in {problems_path}")
            sys.exit(1)
        print(f"Loaded {len(problem_ids)} problems from {problems_path}")
    else:
        # Default: get all problems from judge
        problem_ids = judge.get_all_problems()
        if not problem_ids:
            print(f"{red('ERROR:')} No problems found on judge server")
            sys.exit(1)
        print(f"Auto-discovered {len(problem_ids)} problems from judge")

    # Get model list
    model_result = resolve_models(
        model_arg=args.models,
        models_file=Path(args.models_file) if args.models_file else None,
        default_models_path=script_dir / "models.txt",
        base_dir=script_dir,
    )
    models_list = model_result.models
    print(f"Using {len(models_list)} model(s): {', '.join(models_list)}")

    # Load .env file
    ensure_env_loaded()

    # Collect required providers from models
    required_providers = set()
    for model in models_list:
        provider = detect_provider(model)
        required_providers.add(provider)

    # Precheck API keys (validates before starting)
    valid_keys, check_results = precheck_required_providers(list(required_providers))

    # Build key pools with only valid keys and RPM weights
    provider_key_pools = build_key_pools(valid_keys, check_results)

    # Determine solution indices
    if args.indices is not None:
        # Explicit count
        solution_indices = list(range(args.indices))
    else:
        # Use indices file (default: indices.txt)
        indices_path = Path(args.indices_file)
        if not indices_path.is_absolute():
            indices_path = script_dir / indices_path
        if indices_path.is_file():
            solution_indices = read_solution_indices(indices_path)
            print(f"Loaded {len(solution_indices)} indices from {indices_path}")
        else:
            solution_indices = [0]

    # Create output and logs directories
    logs_dir = script_dir / "generation_logs"
    if not args.dryrun:
        output_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(exist_ok=True)

    # Build tasks
    tasks: List[GenerationTask] = []
    skipped: List[str] = []

    for problem_id in problem_ids:
        statement = judge.get_problem_statement(problem_id)
        if not statement:
            print(f"{yellow('WARNING:')} Could not get statement for problem {problem_id}")
            continue

        for model in models_list:
            model_prefix = get_model_prefix(model)
            provider = detect_provider(model)
            reasoning = is_reasoning_model(model)

            for variant_idx in solution_indices:
                # Nested format: {problem}/{model}.cpp or {problem}/{model}_{variant}.cpp
                sol_path = get_solution_path(output_dir, problem_id, model_prefix, "cpp", variant_idx)
                sol_filename = str(sol_path.relative_to(output_dir))
                failed_path = get_failed_path(sol_path)

                # Handle --only-failed: only process solutions with .FAILED marker
                if args.only_failed:
                    if not failed_path.exists():
                        continue  # Skip - no failure marker
                    # Has .FAILED - will regenerate
                elif sol_path.exists() and not args.force:
                    skipped.append(sol_filename)
                    continue
                elif failed_path.exists() and not args.force:
                    # Already tried and failed, skip unless --force
                    skipped.append(f"{sol_filename} (previously failed)")
                    continue

                tasks.append(GenerationTask(
                    problem_id=problem_id,
                    statement=statement,
                    model=model,
                    provider=provider,
                    reasoning_model=reasoning,
                    variant_index=variant_idx,
                    solution_name=sol_filename,
                    total_variants=len(solution_indices),
                ))

    # Print plan
    print(f"\n{'=' * 60}")
    if args.dryrun:
        print(yellow(bold("DRYRUN MODE - No changes will be made")))
    else:
        print(cyan(bold("GENERATION PLAN")))
    print(f"{'=' * 60}\n")

    print(f"{bold('Configuration:')}")
    print(f"  Problems: {blue(str(len(problem_ids)))}")
    print(f"  Models: {blue(str(len(models_list)))}")
    print(f"  Solutions: {blue(str(len(solution_indices)))} (indices: {solution_indices})")
    print(f"  Output: {blue(str(output_dir))}")
    print()

    if tasks:
        print(f"{green('Will generate')} {green(bold(str(len(tasks))))} solution(s)")
    else:
        print(dim("No new solutions to generate."))

    if skipped:
        print(f"{yellow('Skipping')} {yellow(bold(str(len(skipped))))} existing (use --force)")

    print(f"\n{'=' * 60}\n")

    if args.dryrun:
        return

    if not tasks:
        return

    # Handle --mark-failed: create .FAILED files without generating
    if args.mark_failed:
        marked = 0
        for task in tasks:
            sol_path = output_dir / task.solution_name
            write_failed_marker(sol_path, "Not generated (marked as failed)", task.model)
            marked += 1
        print(f"{yellow('Marked')} {yellow(bold(str(marked)))} solution(s) as failed (.FAILED files created)")
        return

    # Execute tasks
    generated: List[str] = []
    failed: List[str] = []

    def execute_task(task: GenerationTask) -> Tuple[str, str, Optional[str], str, Optional[int]]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"{task.solution_name}_{timestamp}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"{cyan('▶')} Generating {format_solution_name(task.solution_name)} "
              f"({dim('problem:')} {task.problem_id}, {dim('model:')} {model_name(task.model)})")

        pool = provider_key_pools.get(task.provider)
        api_key: Optional[str] = None
        pool_token: Optional[int] = None

        if pool:
            api_key, pool_token = pool.acquire()
            if api_key is None:
                return ("failed", task.solution_name, "No API key available", task.provider, None)
        else:
            api_key = get_fallback_api_key(task.provider)

        sol_path = output_dir / task.solution_name
        failed_path = get_failed_path(sol_path)

        try:
            code = generate_code(
                task.statement,
                model=task.model,
                api_key=api_key,
                log_file=log_file,
                is_reasoning_model=task.reasoning_model,
                timeout=args.timeout,
            )

            # Save solution to nested directory
            sol_path.parent.mkdir(parents=True, exist_ok=True)
            sol_path.write_text(code, encoding="utf-8")
            print(f"  {green('✓')} Saved: {green(str(sol_path))}")

            # Delete .FAILED file if it exists (successful retry)
            if failed_path.exists():
                failed_path.unlink()

            return ("generated", task.solution_name, None, task.provider, pool_token)

        except Exception as exc:
            print(f"  {red('✗')} {red('ERROR:')} {exc}")
            # Write .FAILED marker file
            write_failed_marker(sol_path, str(exc), task.model)
            print(f"  {yellow('!')} Created: {yellow(str(failed_path))}")
            return ("failed", task.solution_name, str(exc), task.provider, pool_token)

    # Run tasks
    max_workers = min(args.concurrency, len(tasks))
    print(f"{cyan('▶')} Starting generation ({bold(str(len(tasks)))} tasks, concurrency={max_workers})...\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(execute_task, task): task for task in tasks}
        for future in as_completed(future_to_task):
            status, sol_name, error_text, provider, pool_token = future.result()
            pool = provider_key_pools.get(provider)
            if pool and pool_token is not None:
                if status == "generated":
                    pool.report_success(pool_token)
                else:
                    pool.report_failure(pool_token, error_text)
            if status == "generated":
                generated.append(sol_name)
            else:
                failed.append(sol_name if error_text is None else f"{sol_name} ({error_text})")

    # Print summary
    print_generation_summary(generated, failed, skipped, format_name=format_solution_name)


if __name__ == "__main__":
    main()
