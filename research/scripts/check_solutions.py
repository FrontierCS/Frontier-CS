#!/usr/bin/env python3
"""
Check solution coverage for research track.

Scans research/solutions/ for flat solution files ({problem}.{model}.py)
and compares against expected models × discovered problems × variants.

Usage:
    python check_solutions.py
    python check_solutions.py --no-color
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from frontier_cs.models import get_model_prefix
from frontier_cs.gen.solution_format import parse_solution_filename, format_solution_filename


class Colors:
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"

    _enabled = True

    @classmethod
    def disable(cls):
        cls._enabled = False

    @classmethod
    def c(cls, text: str, color: str) -> str:
        if not cls._enabled:
            return text
        return f"{color}{text}{cls.RESET}"


def bold(text: str) -> str:
    return Colors.c(text, Colors.BOLD)

def dim(text: str) -> str:
    return Colors.c(text, Colors.DIM)

def red(text: str) -> str:
    return Colors.c(text, Colors.RED)

def green(text: str) -> str:
    return Colors.c(text, Colors.GREEN)

def yellow(text: str) -> str:
    return Colors.c(text, Colors.YELLOW)

def blue(text: str) -> str:
    return Colors.c(text, Colors.BLUE)

def cyan(text: str) -> str:
    return Colors.c(text, Colors.CYAN)

def warning(text: str) -> str:
    return Colors.c(f"⚠ {text}", Colors.YELLOW)

def error(text: str) -> str:
    return Colors.c(f"✗ {text}", Colors.RED)

def success(text: str) -> str:
    return Colors.c(f"✓ {text}", Colors.GREEN)

def info(text: str) -> str:
    return Colors.c(f"ℹ {text}", Colors.CYAN)


# Directories to exclude when auto-discovering problems
EXCLUDE_DIRS = {'common', 'resources', '__pycache__', '.venv', 'data', 'traces', 'bin', 'lib', 'include'}


def discover_problems(problems_dir: Path) -> List[str]:
    """Auto-discover all problem names by finding leaf directories with readme files."""
    result = []

    def is_excluded(p: Path) -> bool:
        for part in p.parts:
            if part in EXCLUDE_DIRS:
                return True
        return False

    def has_problem_subdirs(p: Path) -> bool:
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
        # Check if it's a leaf directory (problem) - has readme but no subdirs
        has_readme = (p / "readme").exists() or (p / "README.md").exists()
        if has_readme and not has_problem_subdirs(p):
            # Convert path to problem name (underscore-separated)
            rel_path = p.relative_to(problems_dir)
            problem_name = "_".join(rel_path.parts)
            result.append(problem_name)

    return sorted(result)


def read_models_list(path: Path) -> List[str]:
    """Read models from models.txt."""
    models: List[str] = []
    if not path.exists():
        return models
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        models.append(line)
    return models


def read_variant_indices(path: Path) -> List[int]:
    """Read variant indices from indices.txt."""
    if not path.exists():
        return [0]
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    if not lines:
        return [0]
    # Single number = count
    if len(lines) == 1:
        try:
            count = int(lines[0])
            return list(range(count)) if count > 0 else [0]
        except ValueError:
            pass
    # Multiple lines = explicit indices
    indices = []
    for line in lines:
        try:
            indices.append(int(line))
        except ValueError:
            pass
    return indices if indices else [0]


def compute_expected(
    problems: List[str],
    models: List[str],
    variants: List[int],
) -> Set[str]:
    """Compute expected solution filenames."""
    expected: Set[str] = set()
    for problem in problems:
        for model in models:
            model_prefix = get_model_prefix(model)
            for variant_idx in variants:
                suffix = "" if variant_idx == 0 else f"_{variant_idx}"
                model_with_variant = f"{model_prefix}{suffix}"
                filename = format_solution_filename(problem, model_with_variant, "py")
                expected.add(filename)
    return expected


def scan_solutions(solutions_dir: Path) -> Dict[str, Dict]:
    """Scan solutions directory for flat solution files."""
    solutions: Dict[str, Dict] = {}
    if not solutions_dir.is_dir():
        return solutions

    for sol_file in solutions_dir.iterdir():
        if not sol_file.is_file() or sol_file.name.startswith("."):
            continue

        parsed = parse_solution_filename(sol_file.name)
        if parsed:
            problem, model, ext = parsed
            # Check if file is empty
            try:
                content = sol_file.read_text(encoding="utf-8").strip()
                is_empty = len(content) == 0
            except Exception:
                is_empty = True

            solutions[sol_file.name] = {
                "problem": problem,
                "model": model,
                "ext": ext,
                "path": sol_file,
                "is_empty": is_empty,
            }

    return solutions


def main():
    base_dir = Path(__file__).parent  # research/scripts/
    research_dir = base_dir.parent  # research/
    repo_root = research_dir.parent  # Root of repository

    parser = argparse.ArgumentParser(
        description="Check solution coverage (Expected vs Actual)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        default=base_dir / "models.txt",
        help="Models file (default: research/scripts/models.txt)",
    )
    parser.add_argument(
        "--indices-file",
        type=Path,
        default=base_dir / "indices.txt",
        help="Indices file (default: research/scripts/indices.txt)",
    )
    parser.add_argument(
        "--solutions-dir",
        type=Path,
        default=research_dir / "solutions",
        help="Solutions directory (default: research/solutions/)",
    )
    parser.add_argument(
        "--problems-dir",
        type=Path,
        default=research_dir / "problems",
        help="Problems directory for auto-discovery (default: research/problems/)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    # Auto-discover problems
    problems = discover_problems(args.problems_dir)
    if not problems:
        print(warning(f"No problems found in {args.problems_dir}"))

    # Read config files
    models = read_models_list(args.models_file) if args.models_file.exists() else []
    variants = read_variant_indices(args.indices_file) if args.indices_file.exists() else [0]

    if not models:
        print(warning(f"No models found in {args.models_file}"))

    # Compute expected and actual
    expected = compute_expected(problems, models, variants) if problems and models else set()
    actual = scan_solutions(args.solutions_dir)
    actual_set = set(actual.keys())

    # Analyze
    generated = expected & actual_set  # Expected and exists
    missing = expected - actual_set  # Expected but not generated
    extra = actual_set - expected  # Exists but not expected

    # Empty solutions
    empty_solutions = {name for name, info in actual.items() if info["is_empty"]}

    # Print report
    print()
    line = "=" * 60
    print(cyan(line))
    print(cyan(bold("Solution Coverage Report (Research Track)")))
    print(cyan(line))
    print()

    print(f"  Problems (auto-discovered): {bold(str(len(problems)))}")
    if problems:
        # Show first few problems
        shown = problems[:5]
        more = len(problems) - len(shown)
        print(f"    {dim(', '.join(shown))}{dim(f', ... +{more} more') if more > 0 else ''}")
    print(f"  Models: {bold(str(len(models)))}")
    if models:
        print(f"    {dim(', '.join(models))}")
    print(f"  Variants: {bold(str(len(variants)))} (indices: {variants})")
    print()

    total_expected = len(expected)
    total_generated = len(generated)
    total_missing = len(missing)
    total_extra = len(extra)

    print(f"  Expected (models × problems × variants): {bold(str(total_expected))}")
    print(f"  Generated (expected & exists): {green(bold(str(total_generated)))}")
    print(f"  Missing (expected but not generated): {yellow(bold(str(total_missing)))}")
    print(f"  Extra (exists but not expected): {blue(bold(str(total_extra)))}")
    print()

    # Coverage bar
    if total_expected > 0:
        coverage = total_generated / total_expected
        bar_width = 40
        filled = int(bar_width * coverage)
        bar = "█" * filled + "░" * (bar_width - filled)
        pct = f"{coverage * 100:.1f}%"
        color = green if coverage > 0.8 else yellow if coverage > 0.3 else red
        print(f"  Coverage: [{color(bar)}] {color(pct)}")
        print()

    # Missing by model
    if missing:
        print(warning(f"{total_missing} solutions not yet generated:"))
        by_model: Dict[str, int] = defaultdict(int)
        for name in missing:
            parsed = parse_solution_filename(name)
            if parsed:
                _, model, _ = parsed
                # Extract base model (strip variant suffix)
                base_model = model.rsplit("_", 1)[0] if "_" in model and model.rsplit("_", 1)[1].isdigit() else model
                by_model[base_model] += 1
        for model in sorted(by_model.keys()):
            print(f"    {model}: {by_model[model]} missing")
        print()

    # Extra solutions
    if extra:
        print(info(f"{total_extra} extra solutions (not in expected set):"))
        for name in sorted(extra)[:10]:
            info_obj = actual.get(name)
            problem = info_obj["problem"] if info_obj else "?"
            print(f"    {dim(name)}: problem={problem}")
        if len(extra) > 10:
            print(f"    {dim(f'... and {len(extra) - 10} more')}")
        print()

    # Empty solutions
    if empty_solutions:
        print(warning(f"{len(empty_solutions)} solutions with empty content:"))
        for name in sorted(empty_solutions)[:10]:
            print(f"    {yellow(name)}")
        if len(empty_solutions) > 10:
            print(f"    {dim(f'... and {len(empty_solutions) - 10} more')}")
        print()

    # Summary
    print(dim("─" * 40))
    has_issues = len(empty_solutions) > 0
    all_good = total_missing == 0 and not has_issues

    if all_good:
        print(success("All expected solutions are generated"))
    else:
        if total_missing > 0:
            print(f"  Run {bold('generate_solutions.py')} to generate missing solutions")
        if empty_solutions:
            print(f"  Fix {bold(str(len(empty_solutions)))} solutions with empty content")
    print(dim("─" * 40))

    # Exit code
    return 1 if (has_issues or total_missing > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
