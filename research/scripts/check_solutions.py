#!/usr/bin/env python3
"""
Check solution coverage for research track.

This script compares expected vs actual solutions to show generation progress:

1. Computes EXPECTED solutions = models × problems × variants
   - models: from models.txt
   - problems: auto-discovered from research/problems/ (leaf dirs with readme)
   - variants: from indices.txt (e.g., [0, 1, 2] for 3 variants per model)

2. Scans ACTUAL solutions in research/solutions/{problem}/{model}.py

3. Reports coverage:
   - Generated: expected AND exists
   - Missing: expected but NOT exists
   - Extra: exists but NOT expected
   - Empty: file exists but content is empty
   - Failed: .FAILED marker files with generation error info (JSON)

Usage:
    python check_solutions.py
    python check_solutions.py --no-color
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from frontier_cs.models import get_model_prefix
from frontier_cs.gen.solution_format import (
    parse_solution_filename,
    format_solution_filename,
    FAILED_EXTENSION,
)


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
EXCLUDE_DIRS = {"common", "resources", "__pycache__", ".venv"}


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

    for p in problems_dir.rglob("*"):
        if not p.is_dir():
            continue
        if is_excluded(p):
            continue
        # Check if it's a leaf directory (problem) - has readme but no subdirs
        has_readme = (p / "readme").exists() or (p / "README.md").exists()
        if has_readme and not has_problem_subdirs(p):
            # Convert path to problem name (slash-separated to match solutions structure)
            rel_path = p.relative_to(problems_dir)
            problem_name = str(rel_path)
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
    """Compute expected solution keys in format: {problem}/{model}.py"""
    expected: Set[str] = set()
    for problem in problems:
        for model in models:
            model_prefix = get_model_prefix(model)
            for variant_idx in variants:
                filename = format_solution_filename(model_prefix, "py", variant_idx)
                # Key format: {problem}/{filename}
                expected.add(f"{problem}/{filename}")
    return expected


def scan_solutions(solutions_dir: Path) -> Dict[str, Dict]:
    """Scan solutions directory for nested solution files.

    Structure: solutions/{problem...}/{model}.py (problem can be nested like a/b/c)
    Returns dict keyed by "{problem}/{model}.{ext}" for comparison with expected set.
    """
    solutions: Dict[str, Dict] = {}
    if not solutions_dir.is_dir():
        return solutions

    # Find all solution files recursively
    for sol_file in solutions_dir.rglob("*.py"):
        if sol_file.name.startswith("."):
            continue
        # Skip _deleted directory
        if "_deleted" in sol_file.parts:
            continue

        parsed = parse_solution_filename(sol_file.name)
        if parsed:
            model, variant, ext = parsed
            # Problem is the relative path from solutions_dir to the parent directory
            problem = str(sol_file.parent.relative_to(solutions_dir))

            # Check if file is empty
            try:
                content = sol_file.read_text(encoding="utf-8").strip()
                is_empty = len(content) == 0
            except Exception:
                is_empty = True

            # Key format: {problem}/{model}.{ext} to match expected set
            key = f"{problem}/{sol_file.name}"
            solutions[key] = {
                "problem": problem,
                "model": model,
                "variant": variant,
                "ext": ext,
                "path": sol_file,
                "is_empty": is_empty,
            }

    return solutions


def scan_failed_solutions(solutions_dir: Path) -> Dict[str, Dict]:
    """Scan solutions directory for .FAILED marker files."""
    failed: Dict[str, Dict] = {}
    if not solutions_dir.is_dir():
        return failed

    # Find all .FAILED files recursively
    for failed_file in solutions_dir.rglob(f"*.{FAILED_EXTENSION}"):
        if failed_file.name.startswith("."):
            continue
        # Skip _deleted directory
        if "_deleted" in failed_file.parts:
            continue

        # Problem is the relative path from solutions_dir to the parent directory
        problem = str(failed_file.parent.relative_to(solutions_dir))

        # Parse model and variant from filename (e.g., gpt5_1.FAILED -> model=gpt5, variant=1)
        # Treat .FAILED as extension for parsing
        fake_filename = failed_file.stem + ".py"  # gpt5_1.FAILED -> gpt5_1.py
        parsed = parse_solution_filename(fake_filename)
        if parsed:
            model, variant, _ = parsed
        else:
            model = failed_file.stem
            variant = 0

        # Read JSON content for error info
        error_msg = None
        try:
            content = failed_file.read_text(encoding="utf-8").strip()
            if content:
                data = json.loads(content)
                error_msg = data.get("error", "Unknown error")
        except (json.JSONDecodeError, Exception):
            error_msg = "Failed to parse error info"

        failed[f"{problem}/{failed_file.name}"] = {
            "problem": problem,
            "model": model,
            "variant": variant,
            "path": failed_file,
            "error": error_msg,
        }

    return failed


def main():
    base_dir = Path(__file__).parent  # research/scripts/
    research_dir = base_dir.parent  # research/

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
    variants = (
        read_variant_indices(args.indices_file) if args.indices_file.exists() else [0]
    )

    if not models:
        print(warning(f"No models found in {args.models_file}"))

    # Compute expected and actual
    expected = (
        compute_expected(problems, models, variants) if problems and models else set()
    )
    actual = scan_solutions(args.solutions_dir)
    actual_set = set(actual.keys())

    # Failed solutions (.FAILED marker files)
    failed_solutions = scan_failed_solutions(args.solutions_dir)
    # Convert failed keys to match expected format: {problem}/{model}.FAILED -> {problem}/{model}.py
    failed_as_py = {
        key.replace(f".{FAILED_EXTENSION}", ".py")
        for key in failed_solutions.keys()
    }

    # Analyze
    generated = expected & actual_set  # Expected and exists
    missing = expected - actual_set - failed_as_py  # Expected but not generated (exclude failed)
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
        print(
            f"    {dim(', '.join(shown))}{dim(f', ... +{more} more') if more > 0 else ''}"
        )
    print(f"  Models: {bold(str(len(models)))}")
    if models:
        print(f"    {dim(', '.join(models))}")
    print(f"  Variants: {bold(str(len(variants)))} (indices: {variants})")
    print()

    total_expected = len(expected)
    total_generated = len(generated)
    total_missing = len(missing)
    total_extra = len(extra)

    total_failed = len(failed_solutions)

    print(f"  Expected (models × problems × variants): {bold(str(total_expected))}")
    print(f"  Generated (expected & exists): {green(bold(str(total_generated)))}")
    print(f"  Missing (expected but not generated): {yellow(bold(str(total_missing)))}")
    print(f"  Failed (generation errors): {red(bold(str(total_failed)))}")
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
        missing_by_model: Dict[str, int] = defaultdict(int)
        for key in missing:
            # Key format: {problem}/{model}.py
            if "/" in key:
                filename = key.split("/")[-1]
                parsed = parse_solution_filename(filename)
                if parsed:
                    model, _, _ = parsed
                    missing_by_model[model] += 1
        for model in sorted(missing_by_model.keys()):
            print(f"    {model}: {missing_by_model[model]} missing")
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

    # Failed solutions
    if failed_solutions:
        print(error(f"{total_failed} solutions failed to generate:"))
        # Group by model
        failed_by_model: Dict[str, List[Dict]] = defaultdict(list)
        for name, info_obj in failed_solutions.items():
            failed_by_model[info_obj["model"]].append(info_obj)

        for model in sorted(failed_by_model.keys()):
            failures = failed_by_model[model]
            print(f"    {red(model)}: {len(failures)} failed")
            # Show first few errors for this model
            for f in failures[:3]:
                variant_str = f"(variant {f['variant']})" if f.get("variant", 0) > 0 else ""
                err_preview = f["error"][:50] + "..." if f["error"] and len(f["error"]) > 50 else f["error"]
                print(f"      {dim(f['problem'])} {dim(variant_str)}: {dim(err_preview or 'No error info')}")
            if len(failures) > 3:
                print(f"      {dim(f'... and {len(failures) - 3} more')}")
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
    has_issues = len(empty_solutions) > 0 or total_failed > 0
    all_good = total_missing == 0 and not has_issues

    if all_good:
        print(success("All expected solutions are generated"))
    else:
        if total_missing > 0:
            print(
                f"  Run {bold('generate_solutions.py')} to generate missing solutions"
            )
        if total_failed > 0:
            print(
                f"  Run {bold('generate_solutions.py --only-failed')} to retry {total_failed} failed"
            )
        if empty_solutions:
            print(
                f"  Fix {bold(str(len(empty_solutions)))} solutions with empty content"
            )
    print(dim("─" * 40))

    # Export problems list
    problems_file = base_dir / "problems.txt"
    problems_file.write_text("\n".join(problems) + "\n", encoding="utf-8")
    print(f"\n  Exported {len(problems)} problems to {dim(str(problems_file))}")

    # Exit code
    return 1 if (has_issues or total_missing > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
