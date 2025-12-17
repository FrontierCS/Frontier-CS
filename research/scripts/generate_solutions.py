#!/usr/bin/env python3
"""
Generate LLM solutions from problem README files.

Supports multiple providers: OpenAI, Google (Gemini), Anthropic (Claude), xAI (Grok), DeepSeek.

Usage:
    python generate_solutions.py --model gpt-5
    python generate_solutions.py research/flash_attn --model claude-sonnet-4-5
    python generate_solutions.py --dryrun  # Show what would be generated
"""

import sys
import os
import json
import time
import argparse
import re
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from importlib import metadata

from frontier_cs.models import get_model_prefix, is_reasoning_model

# Local modules
from gen_env import get_system_prompt_for_problem
from gen_api_keys import build_key_pools, get_fallback_api_key, APIKeyPool
from gen_llm import instantiate_llm_client, detect_provider
from gen_io import (
    load_env_file,
    load_solution_targets,
    read_models_file,
    read_variant_indices_file,
    read_readme,
    load_docker_config,
    get_problem_name,
)
from gen_templates import create_solution
from gen_colors import (
    bold, dim, red, green, yellow, blue, cyan, magenta,
    success, error, warning, info, header, section,
    model_name, problem_name, solution_name,
    print_header, print_section, print_success, print_error, print_warning, print_info,
)


REQUIRED_NUMPY_VERSION = "2.3.4"


@dataclass
class GenerationTask:
    """Represents a single solution generation task."""
    problem_path: Path
    display_path: str
    problem_name: str
    readme: str
    model: str
    provider: str
    reasoning_model: bool
    variant_index: int  # actual suffix index (0 -> no suffix)
    variant_position: int  # ordinal position in the configured variant list (0-based)
    solution_name: str
    total_variants: int = 1


def ensure_numpy_version(required: str) -> None:
    """Ensure the required NumPy version is installed."""
    try:
        installed = metadata.version("numpy")
    except metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            f"NumPy {required} is required but not installed; install it with "
            f"`uv pip install --python .venv/bin/python numpy=={required}`."
        ) from exc
    if installed != required:
        raise RuntimeError(
            f"NumPy {required} is required, but found {installed}; reinstall with "
            f"`uv pip install --python .venv/bin/python numpy=={required}`."
        )


def float_or_none(value: str) -> Optional[float]:
    """Parse a float or return None for 'none'/'null'."""
    text = str(value).strip()
    if text.lower() in {"none", "null"}:
        return None
    return float(text)


def int_or_none(value: str) -> Optional[int]:
    """Parse an int or return None for 'none'/'null'."""
    text = str(value).strip()
    if text.lower() in {"none", "null"}:
        return None
    return int(text)


def parse_extra_headers(entries: List[str]) -> Dict[str, str]:
    """Parse extra HTTP headers from command line."""
    headers: Dict[str, str] = {}
    for entry in entries:
        if ":" not in entry:
            raise ValueError(f"Invalid header format (expected Key: Value): {entry}")
        key, value = entry.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def load_json_args(payload_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse JSON payload from command line."""
    if not payload_str:
        return None
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON for --payload-extra: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("--payload-extra must be a JSON object")
    return data


def resolve_api_key(explicit_key: Optional[str], key_env: Optional[str]) -> Optional[str]:
    """Resolve API key from explicit value or environment variable."""
    if explicit_key:
        return explicit_key
    if key_env:
        return os.getenv(key_env)
    return None


def is_reasoning(model: str, override: Optional[bool]) -> bool:
    """Check if a model is a reasoning model."""
    return is_reasoning_model(model, override)


def generate_code(
    readme: str,
    *,
    model: str,
    api_key: Optional[str],
    log_file: Path,
    api_base: str,
    endpoint: str,
    temperature: Optional[float],
    max_tokens: Optional[int],
    max_reasoning_tokens: Optional[int],
    is_reasoning_model: bool,
    extra_headers: Dict[str, str],
    timeout: float,
    payload_overrides: Optional[Dict[str, Any]],
    api_key_header: Optional[str],
    api_key_prefix: Optional[str],
    problem_name: str = "",
    problem_path: Optional[Path] = None,
    docker_config: Optional[Dict] = None,
) -> str:
    """Generate solution code using an LLM."""
    base_url = (api_base or "").strip()
    if base_url.lower() in {"none", ""}:
        base_url = None
    else:
        base_url = base_url.rstrip("/")

    endpoint_hint = (endpoint or "").strip() or "auto"

    # Get environment-specific system prompt
    system_prompt = get_system_prompt_for_problem(problem_name, problem_path, docker_config)

    # Prepare prompts
    user_prompt = f"Problem:\n\n{readme}\n\nGenerate solution code:"
    combined_prompt = f"{system_prompt}\n\n{user_prompt}"

    # Log request details
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_headers: Dict[str, str] = dict(extra_headers)
    ignored_controls: Dict[str, Any] = {}
    if final_headers:
        ignored_controls["extra_headers"] = final_headers
    if payload_overrides:
        ignored_controls["payload_overrides"] = payload_overrides
    if api_key_header:
        ignored_controls["api_key_header"] = api_key_header
    if api_key_prefix:
        ignored_controls["api_key_prefix"] = api_key_prefix
    if temperature is not None:
        ignored_controls["temperature"] = temperature
    if max_tokens is not None and not is_reasoning_model:
        ignored_controls["max_tokens"] = max_tokens
    if max_reasoning_tokens is not None and is_reasoning_model:
        ignored_controls["max_reasoning_tokens"] = max_reasoning_tokens

    llm_client, llm_config = instantiate_llm_client(
        model,
        is_reasoning_model=is_reasoning_model,
        timeout=timeout,
        base_url=base_url,
        api_key=api_key,
    )

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GPT GENERATION LOG\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"MODEL: {model}\n")
        f.write(f"INTERFACE CLASS: {llm_client.__class__.__name__}\n")
        for key, value in llm_config.items():
            f.write(f"{key.upper()}: {value}\n")
        f.write(f"ENDPOINT HINT: {endpoint_hint}\n")
        f.write(f"TIMEOUT: {timeout}s\n")
        f.write(f"REASONING MODEL: {is_reasoning_model}\n")
        f.write(f"API KEY PROVIDED: {'yes' if bool(api_key) else 'no'}\n")
        if ignored_controls:
            f.write("IGNORED CONTROLS (not supported by llm_interface):\n")
            f.write(json.dumps(ignored_controls, indent=2, ensure_ascii=False))
            f.write("\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("SYSTEM PROMPT:\n")
        f.write("=" * 80 + "\n")
        f.write(system_prompt)
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("USER PROMPT:\n")
        f.write("=" * 80 + "\n")
        f.write(user_prompt)
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("CALLING test_scripts.llm_interface...\n")
        f.write("=" * 80 + "\n\n")

    print(f"Calling llm_interface (model: {model})...")

    MAX_RETRIES = 5
    RETRY_DELAY = 30
    content: Optional[str] = None
    meta: Any = None
    for attempt in range(1, MAX_RETRIES + 1):
        response_text, meta = llm_client.call_llm(combined_prompt)
        content_ok = bool(response_text and not response_text.strip().lower().startswith("error:"))
        if content_ok:
            content = response_text
            break

        error_message = response_text or "Empty response"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"ERROR calling llm_interface (attempt {attempt}/{MAX_RETRIES}): {error_message}\n")

        if attempt < MAX_RETRIES:
            sleep_time = RETRY_DELAY * attempt
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"Retrying after {sleep_time}s...\n")
            time.sleep(sleep_time)

    if content is None:
        raise RuntimeError("llm_interface call failed after retries")

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAW OUTPUT:\n")
        f.write("=" * 80 + "\n")
        f.write(content)
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("LLM METADATA (stringified):\n")
        f.write("=" * 80 + "\n")
        f.write(str(meta))
        f.write("\n\n")

    code = content.strip()

    # Try to extract code from markdown code blocks
    code_block_pattern = r'```(?:python)?\s*\n(.*?)```'
    matches = re.findall(code_block_pattern, code, re.DOTALL)
    if matches:
        code = max(matches, key=len).strip()
    else:
        if code.startswith("```python"):
            code = code[9:].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

    # Log cleaned code
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CLEANED CODE (after removing markdown):\n")
        f.write("=" * 80 + "\n")
        f.write(code)
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("END OF LOG\n")
        f.write("=" * 80 + "\n")

    return code


def build_tasks(
    args,
    repo_root: Path,
    base_dir: Path,
    models_list: List[str],
    normalized_problems: List[Tuple[Path, str]],
    prefix_to_model: Dict[str, str],
) -> Tuple[List[GenerationTask], List[str]]:
    """Build the list of generation tasks."""
    tasks: List[GenerationTask] = []
    skipped: List[str] = []

    if args.solutions_file:
        # Solutions file mode
        solutions_path = Path(args.solutions_file)
        if not solutions_path.is_absolute():
            solutions_path = base_dir / solutions_path
        solution_targets = load_solution_targets(solutions_path)
        print(f"Loaded {len(solution_targets)} target solution(s) from {solutions_path}.")

        problem_cache: Dict[str, Tuple[Path, str, str]] = {}
        for solution_name, problem_entry in solution_targets:
            model_prefix = solution_name.split("_", 1)[0]
            model = prefix_to_model.get(model_prefix)
            if not model:
                print(f"WARNING: No model mapping found for solution prefix '{model_prefix}'; skipping {solution_name}.")
                continue

            provider = detect_provider(model)

            if problem_entry.startswith("research/"):
                relative_problem_str = problem_entry
            else:
                relative_problem_str = f"research/problems/{problem_entry.lstrip('./')}"

            try:
                problem_path_real = (repo_root / relative_problem_str).resolve()
            except Exception:
                print(f"WARNING: Invalid problem path '{problem_entry}' for {solution_name}; skipping.")
                continue

            if not problem_path_real.is_dir():
                print(f"WARNING: Problem path {problem_path_real} not found; skipping {solution_name}.")
                continue

            cache_key = relative_problem_str
            if cache_key not in problem_cache:
                try:
                    readme_text = read_readme(problem_path_real)
                except FileNotFoundError as exc:
                    print(f"WARNING: {exc}; skipping {solution_name}.")
                    continue
                try:
                    rel_path_for_name = problem_path_real.relative_to(repo_root / "research")
                except ValueError:
                    rel_path_for_name = Path(problem_path_real.name)
                problem_name = get_problem_name(rel_path_for_name)
                problem_cache[cache_key] = (problem_path_real, readme_text, problem_name)

            problem_path_real, readme_text, inferred_problem_name = problem_cache[cache_key]

            tail_parts = solution_name.rsplit("_", 1)
            variant_index = 0
            if len(tail_parts) == 2 and tail_parts[1].isdigit():
                variant_index = int(tail_parts[1])
            total_variants_for_task = max(variant_index + 1, 1)

            sol_dir = repo_root / "solutions" / solution_name
            if sol_dir.exists():
                if args.force:
                    if not args.dryrun:
                        try:
                            shutil.rmtree(sol_dir)
                        except Exception as exc:
                            print(f"WARNING: Failed to remove {sol_dir}: {exc}; skipping")
                            skipped.append(solution_name)
                            continue
                else:
                    skipped.append(solution_name)
                    continue

            tasks.append(
                GenerationTask(
                    problem_path=problem_path_real,
                    display_path=problem_entry,
                    problem_name=inferred_problem_name,
                    readme=readme_text,
                    model=model,
                    provider=provider,
                    reasoning_model=is_reasoning(model, args.reasoning_override),
                    variant_index=variant_index,
                    variant_position=variant_index,
                    solution_name=solution_name,
                    total_variants=total_variants_for_task,
                )
            )
    else:
        # Problem list mode
        variants_file = base_dir / "num_solutions.txt"
        if args.variants is None:
            try:
                variant_indices = read_variant_indices_file(variants_file)
            except Exception as exc:
                print(f"WARNING: Failed to read {variants_file}: {exc}; defaulting to [0]")
                variant_indices = [0]
        else:
            variant_indices = list(range(args.variants))

        for problem_path_real, display_path in normalized_problems:
            if not problem_path_real.is_dir():
                print(f"WARNING: Problem path {problem_path_real} not found; skipping")
                continue

            try:
                readme = read_readme(problem_path_real)
            except FileNotFoundError as exc:
                print(f"WARNING: {exc}; skipping {problem_path_real}")
                continue

            relative_problem_path = problem_path_real
            if problem_path_real.is_absolute():
                try:
                    relative_problem_path = problem_path_real.relative_to(repo_root / "research")
                except ValueError:
                    relative_problem_path = Path(problem_path_real.name)

            problem_name = args.name or get_problem_name(relative_problem_path)

            for model in models_list:
                reasoning_model = is_reasoning(model, args.reasoning_override)
                model_prefix = get_model_prefix(model)
                provider = detect_provider(model)

                for pos, variant_index in enumerate(variant_indices):
                    suffix = "" if variant_index == 0 else f"_{variant_index}"
                    solution_name = f"{model_prefix}_{problem_name}{suffix}"
                    sol_dir = repo_root / "solutions" / solution_name

                    if sol_dir.exists():
                        if args.force:
                            if not args.dryrun:
                                try:
                                    shutil.rmtree(sol_dir)
                                except Exception as exc:
                                    print(f"WARNING: Failed to remove {sol_dir}: {exc}; skipping")
                                    skipped.append(solution_name)
                                    continue
                        else:
                            skipped.append(solution_name)
                            continue

                    tasks.append(
                        GenerationTask(
                            problem_path=problem_path_real,
                            display_path=display_path,
                            problem_name=problem_name,
                            readme=readme,
                            model=model,
                            provider=provider,
                            reasoning_model=reasoning_model,
                            variant_index=variant_index,
                            variant_position=pos,
                            solution_name=solution_name,
                            total_variants=len(variant_indices),
                        )
                    )

    return tasks, skipped


def main():
    base_dir = Path(__file__).parent  # research/scripts/
    research_dir = base_dir.parent  # research/
    repo_root = research_dir.parent  # Root of the repository
    ensure_numpy_version(REQUIRED_NUMPY_VERSION)
    load_env_file(base_dir / ".env")

    parser = argparse.ArgumentParser(
        description="Generate LLM solutions from problem README files",
        epilog="""
Target selection (mutually exclusive):
  Problem-based: problem_path, --problem, --problems-file (generate new solutions)
  Solution-based: --solution, --solutions-file (regenerate existing solutions)

Examples:
  %(prog)s --problem "cant_be_late*" --model gpt-4o --dryrun
  %(prog)s --problems-file problems.txt
  %(prog)s research/problems/vdb_pareto/balanced --model claude-sonnet-4-5
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Target selection - Problem-based (generate new)
    problem_group = parser.add_argument_group("Problem selection (generate new solutions)")
    problem_group.add_argument("problem_path", nargs="?", help="Path to a single problem dir")
    problem_group.add_argument("--problem", dest="problem_patterns", action="append", default=[],
                               help="Problem name pattern (wildcards supported), repeatable")
    problem_group.add_argument("--problems-file", dest="problems_file",
                               help="File containing problem directories")

    # Target selection - Solution-based (regenerate existing)
    solution_group = parser.add_argument_group("Solution selection (regenerate existing)")
    solution_group.add_argument("--solution", dest="solution_patterns", action="append", default=[],
                                help="Solution name pattern (wildcards supported), repeatable")
    solution_group.add_argument("--solutions-file", dest="solutions_file",
                                help="File listing solution:problem entries")

    # Model selection
    model_group = parser.add_argument_group("Model selection")
    model_exclusive = model_group.add_mutually_exclusive_group()
    model_exclusive.add_argument("--model", dest="models", nargs="+",
                                 help="Target model identifier(s), e.g. --model gpt-5 gpt-5.1")
    model_exclusive.add_argument("--models-file", help="Newline-delimited model list")

    # API configuration
    api_group = parser.add_argument_group("API configuration")
    api_group.add_argument("--api-key", help="API key value")
    api_group.add_argument("--api-key-env", help="Environment variable for API key")
    api_group.add_argument("--api-base", default=os.getenv("MODEL_API_BASE", "https://api.openai.com/v1"),
                           help="Base URL for the API")
    api_group.add_argument("--timeout", type=float, default=float(os.getenv("MODEL_API_TIMEOUT", "180")),
                           help="Request timeout in seconds")

    # Generation parameters
    gen_group = parser.add_argument_group("Generation parameters")
    gen_group.add_argument("--temperature", type=float_or_none, default=0.7,
                           help="Sampling temperature or 'none'")
    gen_group.add_argument("--max-tokens", type=int_or_none, default=65536,
                           help="Max tokens for standard models")
    gen_group.add_argument("--reasoning-model", dest="reasoning_override", action="store_const",
                           const=True, default=None, help="Force reasoning mode")
    gen_group.add_argument("--no-reasoning-model", dest="reasoning_override", action="store_const",
                           const=False, help="Force standard mode")

    # Execution control
    exec_group = parser.add_argument_group("Execution control")
    exec_group.add_argument("--force", action="store_true", help="Regenerate existing solutions")
    exec_group.add_argument("--dryrun", action="store_true", help="Show what would be generated")
    exec_group.add_argument("--variants", type=int, default=None,
                            help="Number of solutions per model")
    exec_group.add_argument("--concurrency", type=int, default=max(1, min(8, os.cpu_count() or 4)),
                            help="Maximum parallel generations")

    # Hidden/advanced options
    parser.add_argument("--name", help=argparse.SUPPRESS)  # Solution name override
    parser.add_argument("--endpoint", default="chat/completions", help=argparse.SUPPRESS)
    parser.add_argument("--api-key-header", default="Authorization", help=argparse.SUPPRESS)
    parser.add_argument("--api-key-prefix", default="Bearer", help=argparse.SUPPRESS)
    parser.add_argument("--header", dest="extra_headers", action="append", default=[], help=argparse.SUPPRESS)
    parser.add_argument("--max-reasoning-tokens", type=int_or_none, default=65536, help=argparse.SUPPRESS)
    parser.add_argument("--payload-extra", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Check for mutually exclusive target groups
    has_problem_targets = args.problem_path or args.problem_patterns or args.problems_file
    has_solution_targets = args.solution_patterns or args.solutions_file

    if has_problem_targets and has_solution_targets:
        print("ERROR: Cannot mix problem-based (--problem, --problems-file) and solution-based (--solution, --solutions-file) options")
        sys.exit(1)

    # Default to problems.txt if no targets provided
    if not has_problem_targets and not has_solution_targets:
        problems_default = base_dir / "problems.txt"
        if problems_default.is_file():
            args.problems_file = str(problems_default)
            has_problem_targets = True
            print(f"No targets provided; defaulting to {problems_default}.")
        else:
            print("ERROR: Provide --problem, --problems-file, --solution, or --solutions-file")
            sys.exit(1)

    # Parse extra headers
    try:
        extra_headers = parse_extra_headers(args.extra_headers)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    # Parse payload overrides
    try:
        payload_overrides = load_json_args(args.payload_extra)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    # Resolve API key
    default_api_key = resolve_api_key(args.api_key, args.api_key_env)

    # Normalize API key header/prefix
    api_key_header = args.api_key_header
    if api_key_header and api_key_header.lower() == "none":
        api_key_header = None

    api_key_prefix = args.api_key_prefix
    if api_key_prefix and api_key_prefix.lower() == "none":
        api_key_prefix = None

    # Validate args
    if args.variants is not None and args.variants < 1:
        print("ERROR: --variants must be >= 1")
        sys.exit(1)

    if args.concurrency < 1:
        print("ERROR: --concurrency must be >= 1")
        sys.exit(1)

    # Handle --solution patterns (expands to solutions-file format)
    if args.solution_patterns:
        import fnmatch

        # Scan solutions directory and read config.yaml for problem mapping
        solutions_dir = repo_root / "solutions"
        solution_to_problem: Dict[str, str] = {}
        if solutions_dir.is_dir():
            for sol_dir in solutions_dir.iterdir():
                if sol_dir.is_dir() and not sol_dir.name.startswith('.'):
                    config_file = sol_dir / "config.yaml"
                    if config_file.exists():
                        try:
                            content = config_file.read_text(encoding="utf-8")
                            for line in content.splitlines():
                                if line.strip().startswith("problem:"):
                                    problem = line.split(":", 1)[1].strip()
                                    solution_to_problem[sol_dir.name] = problem
                                    break
                        except Exception:
                            pass

        all_solutions = set(solution_to_problem.keys())

        matched_solutions: List[Tuple[str, str]] = []
        for pattern in args.solution_patterns:
            matched = False
            for sol_name in sorted(all_solutions):
                if fnmatch.fnmatch(sol_name, pattern) or fnmatch.fnmatch(sol_name, f"*{pattern}*"):
                    prob_path = solution_to_problem.get(sol_name, "")
                    if prob_path:
                        matched_solutions.append((sol_name, prob_path))
                        matched = True
            if not matched:
                print(f"WARNING: No solutions matched pattern '{pattern}'")

        if matched_solutions:
            # Write to temp file and set as solutions_file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for sol_name, prob_path in matched_solutions:
                    f.write(f"{sol_name}:{prob_path}\n")
                args.solutions_file = f.name
            print(f"Matched {len(matched_solutions)} solution(s) from pattern(s)")

    # Build problem sources
    problem_sources: List[Tuple[Path, str]] = []

    # Handle --problem patterns (supports wildcards)
    if args.problem_patterns:
        import fnmatch
        problems_dir = repo_root / "research" / "problems"
        all_problems = []
        if problems_dir.is_dir():
            def find_problems_recursive(directory: Path, depth: int = 0, max_depth: int = 3) -> List[Path]:
                """Recursively find problem directories (those with readme files)."""
                if depth > max_depth:
                    return []

                excluded = {'common', 'resources', '__pycache__', 'data'}

                # Check if this directory has a readme
                has_readme = (directory / "readme").exists() or (directory / "README.md").exists()

                # Find subdirectories (potential variants/categories)
                subdirs = [sub for sub in directory.iterdir()
                           if sub.is_dir() and not sub.name.startswith('.')
                           and sub.name not in excluded]

                # Recursively find problems in subdirs
                sub_problems = []
                for sub in subdirs:
                    sub_problems.extend(find_problems_recursive(sub, depth + 1, max_depth))

                if sub_problems:
                    # Subdirectories have problems - use those (don't use parent readme)
                    return sub_problems
                elif has_readme:
                    # This directory is a problem (leaf with readme)
                    return [directory]
                elif subdirs:
                    # Has subdirs but no readme anywhere - error
                    print(f"ERROR: {directory.name}/ has subdirectories but no readme files found")
                    sys.exit(1)
                else:
                    return []

            for category in problems_dir.iterdir():
                if category.is_dir() and not category.name.startswith('.'):
                    all_problems.extend(find_problems_recursive(category))

        for pattern in args.problem_patterns:
            matched = False
            for prob_path in all_problems:
                # Match against full path or just the problem name
                rel_path = prob_path.relative_to(repo_root)
                prob_name = "_".join(prob_path.relative_to(problems_dir).parts)
                if fnmatch.fnmatch(str(rel_path), f"*{pattern}*") or \
                   fnmatch.fnmatch(prob_name, pattern) or \
                   fnmatch.fnmatch(prob_path.name, pattern):
                    display = str(rel_path)
                    problem_sources.append((prob_path, display))
                    matched = True
            if not matched:
                print(f"WARNING: No problems matched pattern '{pattern}'")

    if args.problems_file:
        list_path = Path(args.problems_file)
        if not list_path.is_absolute():
            list_path = base_dir / list_path
        if not list_path.is_file():
            print(f"ERROR: Problem list file {list_path} not found")
            sys.exit(1)
        for raw_line in list_path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            problem_sources.append((Path(stripped), stripped))

    if args.problem_path:
        problem_sources.append((Path(args.problem_path), args.problem_path))

    # Normalize and deduplicate problems
    seen_problems: set[str] = set()
    normalized_problems: List[Tuple[Path, str]] = []
    for path_obj, display in problem_sources:
        key = display
        if key in seen_problems:
            continue
        seen_problems.add(key)
        if not path_obj.is_absolute():
            resolved = repo_root / path_obj
        else:
            resolved = path_obj
        normalized_problems.append((resolved, display))

    if args.name and not args.solutions_file and len(normalized_problems) != 1:
        print("ERROR: --name can only be used when generating a single problem")
        sys.exit(1)

    # Create logs directory
    logs_dir = repo_root / "generation_logs"
    if not args.dryrun:
        logs_dir.mkdir(exist_ok=True)

    # Resolve model selection
    models_source_desc = ""
    if args.models:
        models_list = args.models
        if len(models_list) == 1:
            print(f"Using model from --model: {models_list[0]}")
            models_source_desc = f"--model ({models_list[0]})"
        else:
            print(f"Using {len(models_list)} models from --model: {', '.join(models_list)}")
            models_source_desc = f"--model ({len(models_list)} models)"
    elif args.models_file:
        # User explicitly specified --models-file, must exist
        models_path = Path(args.models_file)
        if not models_path.is_absolute():
            models_path = base_dir / models_path
        if not models_path.is_file():
            print(f"ERROR: Models file not found: {models_path}")
            sys.exit(1)
        models_list = read_models_file(models_path)
        if not models_list:
            print(f"ERROR: Models file is empty: {models_path}")
            sys.exit(1)
        print(f"Detected {len(models_list)} models from {models_path}.")
        models_source_desc = f"--models-file ({models_path})"
    else:
        # Default: use models.txt
        models_path = base_dir / "models.txt"
        if not models_path.is_file():
            print(f"ERROR: No model specified and {models_path} not found.")
            print("Use --model <model> or create models.txt")
            sys.exit(1)
        models_list = read_models_file(models_path)
        if not models_list:
            print(f"ERROR: Models file is empty: {models_path}")
            sys.exit(1)
        print(f"Detected {len(models_list)} models from {models_path}.")
        models_source_desc = f"models.txt ({models_path})"

    # Build key pools
    provider_key_pools = build_key_pools(default_api_key)
    if provider_key_pools:
        for provider, pool in provider_key_pools.items():
            print(f"Loaded {pool.size()} API key(s) for provider '{provider}'.")

    # Build prefix to model mapping
    prefix_to_model: Dict[str, str] = {}
    for model in models_list:
        prefix = get_model_prefix(model)
        if prefix in prefix_to_model and prefix_to_model[prefix] != model:
            print(f"WARNING: Multiple models map to prefix '{prefix}'. Using {prefix_to_model[prefix]}.")
            continue
        prefix_to_model[prefix] = model

    # Load docker config for GPU detection
    docker_config = load_docker_config(base_dir / "docker_images.txt")

    # Build tasks
    tasks, skipped = build_tasks(
        args, repo_root, base_dir, models_list, normalized_problems, prefix_to_model
    )

    total_tasks = len(tasks)

    # Print generation plan (both dryrun and normal mode)
    def print_generation_plan(is_dryrun: bool) -> None:
        line = "=" * 60
        if is_dryrun:
            print(f"\n{yellow(line)}")
            print(yellow(bold("DRYRUN MODE - No changes will be made")))
            print(f"{yellow(line)}\n")
        else:
            print(f"\n{cyan(line)}")
            print(cyan(bold("GENERATION PLAN")))
            print(f"{cyan(line)}\n")

        print(f"{bold('Configuration:')}")
        print(f"  Models: {blue(models_source_desc)}")
        print(f"  Problems: {blue(str(len(normalized_problems)))}")
        print(f"  Concurrency: {blue(str(args.concurrency))}")
        print(f"  Force: {blue(str(args.force))}")
        print()

        if tasks:
            action = "Would generate" if is_dryrun else "Will generate"
            print(f"{green(action)} {green(bold(str(total_tasks)))} solution(s):\n")
            # Group by problem
            by_problem: Dict[str, List[GenerationTask]] = {}
            for task in tasks:
                key = task.display_path
                if key not in by_problem:
                    by_problem[key] = []
                by_problem[key].append(task)

            for problem, problem_tasks in by_problem.items():
                print(f"  {problem_name(problem)}:")
                for task in problem_tasks:
                    print(f"    {dim('-')} {solution_name(task.solution_name)} "
                          f"({dim('model:')} {model_name(task.model)}, "
                          f"{dim('variant:')} {task.variant_index})")
                print()
        else:
            print(dim("No new solutions to generate.\n"))

        if skipped:
            action = "Would skip" if is_dryrun else "Skipping"
            print(f"{yellow(action)} {yellow(bold(str(len(skipped))))} existing solution(s):")
            for name in skipped[:10]:
                print(f"  {dim('-')} {dim(name)}")
            if len(skipped) > 10:
                print(f"  {dim(f'... and {len(skipped) - 10} more')}")
            print()

        color = yellow if is_dryrun else cyan
        print(color(line))
        if is_dryrun:
            print(yellow("Run without --dryrun to execute"))
        print(color(line) + "\n")

    # Show plan
    print_generation_plan(args.dryrun)

    if args.dryrun:
        return

    # Execute tasks
    if total_tasks == 0:
        print("No new tasks to generate.")
        return

    generated: List[str] = []
    failed: List[str] = []

    def execute_task(task: GenerationTask) -> Tuple[str, str, Optional[str], str, Optional[int]]:
        variant_label = f"{task.variant_position + 1}/{task.total_variants}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_file = logs_dir / f"{task.solution_name}_{timestamp}.log"
        print(f"{cyan('▶')} Generating {solution_name(task.solution_name)} "
              f"({dim('model:')} {model_name(task.model)}, {dim('variant')} {variant_label})...")
        print(f"  {dim('Log:')} {dim(str(log_file))}")

        pool = provider_key_pools.get(task.provider)
        api_key_for_task: Optional[str] = None
        pool_token: Optional[int] = None

        if pool:
            api_key_for_task, pool_token = pool.acquire()
            if api_key_for_task is None:
                message = f"No available API key for provider {task.provider}; skipping."
                print(f"  {red('✗')} {red('ERROR:')} {message}")
                return ("failed", task.solution_name, message, task.provider, None)
        else:
            api_key_for_task = get_fallback_api_key(task.provider, default_api_key)

        try:
            code = generate_code(
                task.readme,
                model=task.model,
                api_key=api_key_for_task,
                log_file=log_file,
                api_base=args.api_base,
                endpoint=args.endpoint,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                max_reasoning_tokens=args.max_reasoning_tokens,
                is_reasoning_model=task.reasoning_model,
                extra_headers=extra_headers,
                timeout=args.timeout,
                payload_overrides=payload_overrides,
                api_key_header=api_key_header,
                api_key_prefix=api_key_prefix,
                problem_name=task.problem_name,
                problem_path=task.problem_path,
                docker_config=docker_config,
            )
            # Extract problem path (remove "research/problems/" prefix if present)
            problem_for_config = task.display_path
            for prefix in ("research/problems/", "problems/"):
                if problem_for_config.startswith(prefix):
                    problem_for_config = problem_for_config[len(prefix):]
                    break
            sol_dir = create_solution(repo_root, task.solution_name, code, problem=problem_for_config)
            print(f"  {green('✓')} Created: {green(str(sol_dir))}")
            print(f"  {dim('Log saved:')} {dim(str(log_file))}")
            return ("generated", task.solution_name, None, task.provider, pool_token)
        except Exception as exc:
            message = f"{exc} (log: {log_file})"
            print(f"  {red('✗')} {red('ERROR:')} {exc}")
            return ("failed", task.solution_name, message, task.provider, pool_token)

    if total_tasks:
        max_workers = min(args.concurrency, total_tasks)
        print(f"{cyan('▶')} Starting generation ({bold(str(total_tasks))} tasks, concurrency={max_workers})...\n")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(execute_task, task): task for task in tasks}
            for future in as_completed(future_to_task):
                status, sol_name, error_text, provider, pool_token = future.result()
                pool = provider_key_pools.get(provider)
                if pool:
                    if status == "generated":
                        pool.report_success(pool_token)
                    else:
                        pool.report_failure(pool_token, error_text)
                if status == "generated":
                    generated.append(sol_name)
                else:
                    failed.append(sol_name if error_text is None else f"{sol_name} ({error_text})")

    # Print summary
    print(f"\n{bold('Summary:')}")
    line = "─" * 40
    print(dim(line))
    if generated:
        print(f"  {green('✓')} Generated: {green(bold(str(len(generated))))} solution(s)")
        for name in generated[:5]:
            print(f"    {dim('•')} {solution_name(name)}")
        if len(generated) > 5:
            print(f"    {dim(f'... and {len(generated) - 5} more')}")
    else:
        print(f"  {dim('•')} No new solutions generated.")
    if skipped:
        print(f"  {yellow('○')} Skipped: {yellow(bold(str(len(skipped))))} existing (use {bold('--force')} to regenerate)")
    if failed:
        print(f"  {red('✗')} Failed: {red(bold(str(len(failed))))} solution(s)")
        for name in failed[:5]:
            print(f"    {dim('•')} {red(name)}")
        if len(failed) > 5:
            print(f"    {dim(f'... and {len(failed) - 5} more')}")
    print(dim(line))


if __name__ == "__main__":
    main()
