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
from frontier_cs.gen import (
    build_key_pools, get_fallback_api_key, APIKeyPool,
    ensure_env_loaded, precheck_required_providers,
    instantiate_llm_client, detect_provider,
    bold, dim, red, green, yellow, blue, cyan, magenta,
    success, error, warning, info, header, section,
    model_name, problem_name as format_problem_name, solution_name as format_solution_name,
    print_header, print_section, print_success, print_error, print_warning, print_info,
    get_failed_path, write_failed_marker,
    resolve_models,
    print_generation_summary,
)
from frontier_cs.gen.solution_format import (
    format_solution_filename,
    get_solution_path,
)

# Local modules (research-specific)
from gen_env import get_system_prompt_for_problem
from gen_io import (
    load_env_file,
    load_solution_targets,
    read_variant_indices_file,
    read_readme,
    load_docker_config,
    get_problem_name,
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


# Directories to exclude when auto-discovering problems
EXCLUDE_DIRS = {'common', 'resources', '__pycache__', '.venv', 'data', 'traces', 'bin', 'lib', 'include'}


def discover_problems(problems_dir: Path) -> List[Path]:
    """Auto-discover all problem directories by finding leaf directories.

    Excludes special directories like common/, resources/, __pycache__, .venv/, etc.
    A problem directory is a directory with no subdirectories (except excluded ones).
    """
    result = []

    def is_excluded(p: Path) -> bool:
        """Check if path or any parent is in exclude list."""
        for part in p.parts:
            if part in EXCLUDE_DIRS:
                return True
        return False

    def has_problem_subdirs(p: Path) -> bool:
        """Check if directory has non-excluded subdirectories."""
        try:
            for child in p.iterdir():
                if child.is_dir() and child.name not in EXCLUDE_DIRS:
                    return True
        except PermissionError:
            pass
        return False

    for p in problems_dir.rglob('*'):
        if not p.is_dir():
            continue
        if is_excluded(p):
            continue
        if not has_problem_subdirs(p):
            result.append(p)

    return sorted(result)


def generate_code(
    readme: str,
    *,
    model: str,
    api_key: Optional[str],
    log_file: Path,
    is_reasoning_model: bool,
    timeout: float,
    problem_name: str = "",
    problem_path: Optional[Path] = None,
    docker_config: Optional[Dict] = None,
) -> str:
    """Generate solution code using an LLM."""

    # Get environment-specific system prompt
    system_prompt = get_system_prompt_for_problem(problem_name, problem_path, docker_config)

    # Prepare prompts
    user_prompt = f"Problem:\n\n{readme}\n\nGenerate solution code:"
    combined_prompt = f"{system_prompt}\n\n{user_prompt}"

    # Log request details
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
        f.write("GPT GENERATION LOG\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"MODEL: {model}\n")
        f.write(f"INTERFACE CLASS: {llm_client.__class__.__name__}\n")
        for key, value in llm_config.items():
            f.write(f"{key.upper()}: {value}\n")
        f.write(f"TIMEOUT: {timeout}s\n")
        f.write(f"REASONING MODEL: {is_reasoning_model}\n")
        f.write(f"API KEY PROVIDED: {'yes' if bool(api_key) else 'no'}\n")
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

    print(f"Calling llm_interface (model: {model}, problem: {problem_name})...")

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
        print(f"  [problem: {problem_name}] Error (attempt {attempt}/{MAX_RETRIES}): {error_message[:200]}")
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
        # Solutions file mode - for regenerating existing solutions
        # New format: solution filenames like "flash_attn.gpt5.py:research/problems/flash_attn"
        solutions_path = Path(args.solutions_file)
        if not solutions_path.is_absolute():
            solutions_path = base_dir / solutions_path
        solution_targets = load_solution_targets(solutions_path)
        print(f"Loaded {len(solution_targets)} target solution(s) from {solutions_path}.")

        problem_cache: Dict[str, Tuple[Path, str, str]] = {}
        for sol_filename, problem_entry in solution_targets:
            # Parse new format: {problem}.{model}.py
            parts = sol_filename.rsplit('.', 2)
            if len(parts) != 3:
                print(f"WARNING: Invalid solution filename format '{sol_filename}'; skipping.")
                continue
            _, model_with_variant, _ = parts

            # Extract model prefix (strip variant suffix like _1, _2)
            model_base = model_with_variant.rsplit("_", 1)[0] if "_" in model_with_variant and model_with_variant.rsplit("_", 1)[1].isdigit() else model_with_variant
            model = prefix_to_model.get(model_base)
            if not model:
                print(f"WARNING: No model mapping for '{model_base}' in '{sol_filename}'; skipping.")
                continue

            # Parse variant index
            variant_index = 0
            if "_" in model_with_variant:
                variant_parts = model_with_variant.rsplit("_", 1)
                if len(variant_parts) == 2 and variant_parts[1].isdigit():
                    variant_index = int(variant_parts[1])

            provider = detect_provider(model)

            if problem_entry.startswith("research/"):
                relative_problem_str = problem_entry
            else:
                relative_problem_str = f"research/problems/{problem_entry.lstrip('./')}"

            try:
                problem_path_real = (repo_root / relative_problem_str).resolve()
            except Exception:
                print(f"WARNING: Invalid problem path '{problem_entry}' for {sol_filename}; skipping.")
                continue

            if not problem_path_real.is_dir():
                print(f"WARNING: Problem path {problem_path_real} not found; skipping {sol_filename}.")
                continue

            cache_key = relative_problem_str
            if cache_key not in problem_cache:
                try:
                    readme_text = read_readme(problem_path_real)
                except FileNotFoundError as exc:
                    print(f"WARNING: {exc}; skipping {sol_filename}.")
                    continue
                try:
                    rel_path_for_name = problem_path_real.relative_to(repo_root / "research")
                except ValueError:
                    rel_path_for_name = Path(problem_path_real.name)
                inferred_problem_name = get_problem_name(rel_path_for_name)
                problem_cache[cache_key] = (problem_path_real, readme_text, inferred_problem_name)

            problem_path_real, readme_text, inferred_problem_name = problem_cache[cache_key]

            sol_file = repo_root / "solutions" / sol_filename
            failed_path = get_failed_path(sol_file)

            # Handle --only-failed: only process solutions with .FAILED marker
            if args.only_failed:
                if not failed_path.exists():
                    continue  # Skip - no failure marker
                # Has .FAILED - will regenerate
            elif sol_file.exists():
                if args.force:
                    if not args.dryrun:
                        try:
                            sol_file.unlink()
                        except Exception as exc:
                            print(f"WARNING: Failed to remove {sol_file}: {exc}; skipping")
                            skipped.append(sol_filename)
                            continue
                else:
                    skipped.append(sol_filename)
                    continue
            elif failed_path.exists() and not args.force:
                # Already tried and failed, skip unless --force
                skipped.append(f"{sol_filename} (previously failed)")
                continue

            tasks.append(
                GenerationTask(
                    problem_path=problem_path_real,
                    display_path=problem_entry,
                    problem_name=inferred_problem_name,
                    readme=readme_text,
                    model=model,
                    provider=provider,
                    reasoning_model=is_reasoning_model(model),
                    variant_index=variant_index,
                    variant_position=variant_index,
                    solution_name=sol_filename,
                    total_variants=max(variant_index + 1, 1),
                )
            )
    else:
        # Problem list mode - determine solution indices
        if args.indices is not None:
            # Explicit count
            variant_indices = list(range(args.indices))
        else:
            # Use indices file (default: indices.txt)
            indices_path = Path(args.indices_file)
            if not indices_path.is_absolute():
                indices_path = base_dir / indices_path
            if indices_path.is_file():
                variant_indices = read_variant_indices_file(indices_path)
                print(f"Loaded {len(variant_indices)} indices from {indices_path}")
            else:
                variant_indices = [0]

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
                reasoning_model = is_reasoning_model(model)
                model_prefix = get_model_prefix(model)
                provider = detect_provider(model)

                for pos, variant_index in enumerate(variant_indices):
                    # Nested format: {problem}/{model}.py or {problem}/{model}_{variant}.py
                    solutions_dir = repo_root / "research" / "solutions"
                    sol_file = get_solution_path(solutions_dir, problem_name, model_prefix, "py", variant_index)
                    sol_filename = str(sol_file.relative_to(solutions_dir))
                    failed_path = get_failed_path(sol_file)

                    # Handle --only-failed: only process solutions with .FAILED marker
                    if args.only_failed:
                        if not failed_path.exists():
                            continue  # Skip - no failure marker
                        # Has .FAILED - will regenerate
                    elif sol_file.exists():
                        if args.force:
                            if not args.dryrun:
                                try:
                                    sol_file.unlink()
                                except Exception as exc:
                                    print(f"WARNING: Failed to remove {sol_file}: {exc}; skipping")
                                    skipped.append(sol_filename)
                                    continue
                        else:
                            skipped.append(sol_filename)
                            continue
                    elif failed_path.exists() and not args.force:
                        # Already tried and failed, skip unless --force
                        skipped.append(f"{sol_filename} (previously failed)")
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
                            solution_name=sol_filename,
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
    problem_group.add_argument("--problems-file", dest="problems_file", default=None,
                               help="File containing problem directories (default: auto-discover)")

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
    api_group.add_argument("--timeout", type=float, default=600.0,
                           help="Request timeout in seconds")

    # Execution control
    exec_group = parser.add_argument_group("Execution control")
    exec_group.add_argument("--force", action="store_true", help="Regenerate existing solutions")
    exec_group.add_argument("--only-failed", action="store_true",
                            help="Only regenerate solutions that previously failed (.FAILED files)")
    exec_group.add_argument("--mark-failed", action="store_true",
                            help="Create .FAILED files for missing solutions without generating (for tracking)")
    exec_group.add_argument("--dryrun", action="store_true", help="Show what would be generated")
    exec_group.add_argument("--indices", type=int, default=None,
                            help="Number of solutions to generate (e.g., --indices 4)")
    exec_group.add_argument("--indices-file", dest="indices_file", default="indices.txt",
                            help="File with solution indices to generate")
    exec_group.add_argument("--concurrency", type=int, default=4,
                            help="Maximum parallel generations")

    # Hidden/advanced options
    parser.add_argument("--name", help=argparse.SUPPRESS)  # Solution name override

    args = parser.parse_args()

    # Check for mutually exclusive target groups
    has_problem_targets = args.problem_path or args.problem_patterns or args.problems_file
    has_solution_targets = args.solution_patterns or args.solutions_file

    if has_problem_targets and has_solution_targets:
        print("ERROR: Cannot mix problem-based (--problem, --problems-file) and solution-based (--solution, --solutions-file) options")
        sys.exit(1)

    # Default to auto-discovery if no targets provided
    auto_discover = False
    if not has_problem_targets and not has_solution_targets:
        auto_discover = True
        has_problem_targets = True

    # Validate args
    if args.concurrency < 1:
        print("ERROR: --concurrency must be >= 1")
        sys.exit(1)

    # Handle --solution patterns (expands to solutions-file format)
    if args.solution_patterns:
        import fnmatch
        from frontier_cs.gen.solution_format import parse_solution_filename

        # Scan solutions directory for flat files
        solutions_dir = repo_root / "solutions"
        solution_to_problem: Dict[str, str] = {}
        if solutions_dir.is_dir():
            for sol_file in solutions_dir.iterdir():
                if sol_file.is_file() and not sol_file.name.startswith('.'):
                    parsed = parse_solution_filename(sol_file.name)
                    if parsed:
                        problem, _, _ = parsed
                        # Problem name from filename maps to problem path
                        solution_to_problem[sol_file.name] = f"problems/{problem.replace('_', '/')}"

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
    problems_dir = repo_root / "research" / "problems"

    # Handle --problem patterns (supports wildcards)
    if args.problem_patterns:
        import fnmatch
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
        # Load problems from file
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
        print(f"Loaded {len(problem_sources)} problems from {list_path}")

    if auto_discover:
        # Auto-discover all problems from problems/ directory
        discovered = discover_problems(problems_dir)
        print(f"Auto-discovered {len(discovered)} problems from {problems_dir}")
        for prob_path in discovered:
            rel_path = prob_path.relative_to(problems_dir)
            problem_sources.append((prob_path, str(rel_path)))

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
    model_result = resolve_models(
        model_arg=args.models,
        models_file=Path(args.models_file) if args.models_file else None,
        default_models_path=base_dir / "models.txt",
        base_dir=base_dir,
    )
    models_list = model_result.models
    models_source_desc = model_result.source_description
    if len(models_list) == 1:
        print(f"Using model from {models_source_desc}")
    else:
        print(f"Detected {len(models_list)} models from {models_source_desc}.")

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
                print(f"  {format_problem_name(problem)}:")
                for task in problem_tasks:
                    print(f"    {dim('-')} {format_solution_name(task.solution_name)} "
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

    # Handle --mark-failed: create .FAILED files without generating
    if args.mark_failed:
        solutions_dir = research_dir / "solutions"
        marked = 0
        for task in tasks:
            sol_file = solutions_dir / task.solution_name
            write_failed_marker(sol_file, "Not generated (marked as failed)", task.model)
            marked += 1
        print(f"{yellow('Marked')} {yellow(bold(str(marked)))} solution(s) as failed (.FAILED files created)")
        return

    generated: List[str] = []
    failed: List[str] = []

    def execute_task(task: GenerationTask) -> Tuple[str, str, Optional[str], str, Optional[int]]:
        variant_label = f"{task.variant_position + 1}/{task.total_variants}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_file = logs_dir / f"{task.solution_name}_{timestamp}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"{cyan('▶')} Generating {format_solution_name(task.solution_name)} "
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
            api_key_for_task = get_fallback_api_key(task.provider)

        solutions_dir = research_dir / "solutions"
        sol_file = solutions_dir / task.solution_name
        failed_path = get_failed_path(sol_file)

        try:
            code = generate_code(
                task.readme,
                model=task.model,
                api_key=api_key_for_task,
                log_file=log_file,
                is_reasoning_model=task.reasoning_model,
                timeout=args.timeout,
                problem_name=task.problem_name,
                problem_path=task.problem_path,
                docker_config=docker_config,
            )
            # Write solution to nested directory
            sol_file.parent.mkdir(parents=True, exist_ok=True)
            sol_file.write_text(code, encoding="utf-8")
            print(f"  {green('✓')} Created: {green(str(sol_file))}")
            print(f"  {dim('Log saved:')} {dim(str(log_file))}")

            # Delete .FAILED file if it exists (successful retry)
            if failed_path.exists():
                failed_path.unlink()

            return ("generated", task.solution_name, None, task.provider, pool_token)
        except Exception as exc:
            message = f"{exc} (log: {log_file})"
            print(f"  {red('✗')} {red('ERROR:')} {exc}")
            # Write .FAILED marker file
            write_failed_marker(sol_file, str(exc), task.model)
            print(f"  {yellow('!')} Created: {yellow(str(failed_path))}")
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
    print_generation_summary(generated, failed, skipped, format_name=format_solution_name)

    # Write detailed summary to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = logs_dir / f"generation_summary_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Generation Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Generated: {len(generated)} solution(s)\n")
        f.write("-" * 40 + "\n")
        for name in generated:
            f.write(f"  {name}\n")
        f.write("\n")
        f.write(f"Skipped: {len(skipped)} solution(s)\n")
        f.write("-" * 40 + "\n")
        for name in skipped:
            f.write(f"  {name}\n")
        f.write("\n")
        f.write(f"Failed: {len(failed)} solution(s)\n")
        f.write("-" * 40 + "\n")
        for name in failed:
            f.write(f"  {name}\n")
    print(f"\n{dim('Detailed summary saved to:')} {cyan(str(summary_file))}")


if __name__ == "__main__":
    main()
