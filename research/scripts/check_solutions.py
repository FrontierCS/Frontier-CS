#!/usr/bin/env python3
"""
Internal tool: Check solution coverage and eval_targets.txt consistency.

Compares three layers:
  (1) Expected: models × problems × variants (from config files)
  (2) Actual: what exists in solutions/ directory
  (3) Declared: what's listed in eval_targets.txt

Usage:
    # Full check (all three layers)
    python check_solutions.py --pairs-file eval_targets.txt

    # Check coverage only (Expected vs Actual)
    python check_solutions.py

    # Verify eval_targets.txt only (Declared vs Actual)
    python check_solutions.py --verify-pairs eval_targets.txt
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from frontier_cs.models import get_model_prefix, sanitize_problem_name


# ============================================================================
# Colors
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    @classmethod
    def disable(cls):
        """Disable colors (for non-TTY output)."""
        for attr in dir(cls):
            if not attr.startswith('_') and isinstance(getattr(cls, attr), str):
                setattr(cls, attr, '')


# Auto-disable colors if not a TTY
if not sys.stdout.isatty():
    Colors.disable()


def header(text: str) -> str:
    return f"{Colors.BOLD}{Colors.CYAN}{'═' * 60}{Colors.RESET}\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}\n{Colors.BOLD}{Colors.CYAN}{'═' * 60}{Colors.RESET}"


def success(text: str) -> str:
    return f"{Colors.BRIGHT_GREEN}✓{Colors.RESET} {text}"


def warning(text: str) -> str:
    return f"{Colors.BRIGHT_YELLOW}⚠{Colors.RESET} {Colors.YELLOW}{text}{Colors.RESET}"


def error(text: str) -> str:
    return f"{Colors.BRIGHT_RED}✗{Colors.RESET} {Colors.RED}{text}{Colors.RESET}"


def info(text: str) -> str:
    return f"{Colors.BRIGHT_BLUE}ℹ{Colors.RESET} {text}"


def dim(text: str) -> str:
    return f"{Colors.DIM}{text}{Colors.RESET}"


def count_label(label: str, count: int, color: str = Colors.WHITE) -> str:
    return f"  {color}{label}:{Colors.RESET} {Colors.BOLD}{count}{Colors.RESET}"


# ============================================================================
# File Reading
# ============================================================================

def read_list_file(path: Path) -> List[str]:
    """Read a list file (one item per line, # comments, blank lines ignored)."""
    if not path.is_file():
        return []
    items: List[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items


def read_problem_list(path: Path) -> List[str]:
    """Read problems from problems.txt, normalizing to problem ID."""
    problems = []
    for entry in read_list_file(path):
        # Remove 'research/problems/' or 'research/' prefix
        if entry.startswith("research/problems/"):
            normalized = entry[len("research/problems/"):]
        elif entry.startswith("research/"):
            normalized = entry[len("research/"):]
        else:
            normalized = entry
        problems.append(normalized)
    return problems


def read_models_list(path: Path) -> List[str]:
    """Read unique models from models.txt."""
    models: List[str] = []
    seen: Set[str] = set()
    for entry in read_list_file(path):
        if entry not in seen:
            models.append(entry)
            seen.add(entry)
    return models


def read_variant_indices(path: Path) -> List[int]:
    """Read variant indices from num_solutions.txt."""
    values = read_list_file(path)
    if not values:
        return [0]

    if len(values) == 1:
        try:
            n = int(values[0])
            return list(range(max(1, n)))
        except ValueError:
            pass

    indices: List[int] = []
    seen: Set[int] = set()
    for v in values:
        try:
            idx = int(v)
            if idx >= 0 and idx not in seen:
                indices.append(idx)
                seen.add(idx)
        except ValueError:
            pass
    return indices or [0]


def read_pairs_file(path: Path) -> List[Tuple[str, str]]:
    """Read pairs from eval_targets.txt (solution:problem per line)."""
    pairs: List[Tuple[str, str]] = []
    if not path.is_file():
        return pairs
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        solution, problem = line.split(":", 1)
        pairs.append((solution.strip(), problem.strip()))
    return pairs


# ============================================================================
# Core Logic
# ============================================================================

def compute_expected(
    problems: List[str],
    models: List[str],
    variant_indices: List[int],
) -> Dict[str, str]:
    """Compute expected solution names from config."""
    mapping: Dict[str, str] = {}
    for problem in problems:
        slug = sanitize_problem_name(problem)
        for model in models:
            prefix = get_model_prefix(model)
            for idx in variant_indices:
                suffix = "" if idx == 0 else f"_{idx}"
                solution_name = f"{prefix}_{slug}{suffix}"
                mapping[solution_name] = problem
    return mapping


def collect_actual(solutions_dir: Path) -> Set[str]:
    """List all solution directories on disk."""
    if not solutions_dir.is_dir():
        return set()
    return {entry.name for entry in solutions_dir.iterdir() if entry.is_dir()}


def analyze(
    expected: Dict[str, str],
    actual: Set[str],
    declared: List[Tuple[str, str]],
) -> dict:
    """Analyze the three layers and find discrepancies."""
    expected_set = set(expected.keys())
    declared_solutions = {sol for sol, _ in declared}
    declared_map = {sol: prob for sol, prob in declared}

    return {
        # Coverage stats
        "expected_count": len(expected_set),
        "actual_count": len(actual),
        "declared_count": len(declared),

        # Expected vs Actual
        "generated": expected_set & actual,  # Expected and exists
        "missing_generation": expected_set - actual,  # Expected but not generated

        # Actual vs Expected
        "manual_additions": actual - expected_set,  # Exists but not expected (manually added)

        # Declared vs Actual
        "declared_valid": {sol for sol in declared_solutions if sol in actual},
        "declared_invalid": {sol for sol in declared_solutions if sol not in actual},

        # Actual vs Declared
        "not_in_pairs": actual - declared_solutions,  # Exists but not in eval_targets.txt

        # Full mappings for details
        "expected_map": expected,
        "declared_map": declared_map,
    }


# ============================================================================
# Reporting
# ============================================================================

def print_coverage_report(result: dict, models: List[str]):
    """Print Expected vs Actual coverage report."""
    print(header("Solution Coverage (Expected vs Actual)"))
    print()

    expected = result["expected_count"]
    generated = len(result["generated"])
    missing = len(result["missing_generation"])
    manual = len(result["manual_additions"])

    pct = 100 * generated / expected if expected > 0 else 0

    print(count_label("Expected (models × problems × variants)", expected, Colors.BLUE))
    print(count_label("Generated (expected & exists)", generated, Colors.GREEN))
    print(count_label("Missing (expected but not generated)", missing, Colors.RED if missing else Colors.GREEN))
    print(count_label("Manual additions (exists but not expected)", manual, Colors.YELLOW if manual else Colors.DIM))
    print()

    if expected > 0:
        bar_width = 40
        filled = int(bar_width * generated / expected)
        bar = f"[{Colors.GREEN}{'█' * filled}{Colors.DIM}{'░' * (bar_width - filled)}{Colors.RESET}]"
        print(f"  Coverage: {bar} {pct:.1f}%")
        print()

    # Missing by model
    if missing > 0:
        print(warning(f"{missing} solutions not yet generated:"))
        by_prefix: Dict[str, List[str]] = defaultdict(list)
        for sol in result["missing_generation"]:
            prefix = sol.split("_", 1)[0]
            by_prefix[prefix].append(sol)

        for prefix in sorted(by_prefix.keys()):
            sols = by_prefix[prefix]
            print(f"    {Colors.DIM}{prefix}:{Colors.RESET} {len(sols)} missing")
        print()

    # Manual additions
    if manual > 0:
        print(info(f"{manual} manually added solutions (not from LLM generation):"))
        for sol in sorted(result["manual_additions"])[:5]:
            print(f"    {Colors.YELLOW}{sol}{Colors.RESET}")
        if manual > 5:
            print(dim(f"    ... and {manual - 5} more"))
        print()


def print_pairs_report(result: dict, pairs_file: Optional[Path]):
    """Print Declared (eval_targets.txt) vs Actual report."""
    print(header("Pairs Consistency (Declared vs Actual)"))
    print()

    if pairs_file is None or not pairs_file.exists():
        print(warning("No eval_targets.txt file specified or found"))
        print(dim("  Use: --pairs-file eval_targets.txt"))
        print()
        return

    declared = result["declared_count"]
    valid = len(result["declared_valid"])
    invalid = len(result["declared_invalid"])
    not_in_pairs = len(result["not_in_pairs"])

    print(count_label("Declared in eval_targets.txt", declared, Colors.BLUE))
    print(count_label("Valid (solution exists)", valid, Colors.GREEN))
    print(count_label("Invalid (solution missing)", invalid, Colors.RED if invalid else Colors.GREEN))
    print(count_label("On disk but not in eval_targets.txt", not_in_pairs, Colors.YELLOW if not_in_pairs else Colors.DIM))
    print()

    # Invalid pairs (solution doesn't exist)
    if invalid > 0:
        print(error(f"{invalid} pairs reference non-existent solutions:"))
        for sol in sorted(result["declared_invalid"])[:5]:
            prob = result["declared_map"].get(sol, "?")
            print(f"    {Colors.RED}{sol}:{prob}{Colors.RESET}")
        if invalid > 5:
            print(dim(f"    ... and {invalid - 5} more"))
        print()

    # Solutions not in eval_targets.txt
    if not_in_pairs > 0:
        print(warning(f"{not_in_pairs} solutions exist but are not in eval_targets.txt:"))

        # Separate into expected (LLM) vs manual
        expected_not_declared = result["not_in_pairs"] & result["generated"]
        manual_not_declared = result["not_in_pairs"] & result["manual_additions"]

        if expected_not_declared:
            print(f"  {Colors.CYAN}From LLM generation:{Colors.RESET}")
            for sol in sorted(expected_not_declared)[:3]:
                prob = result["expected_map"].get(sol, "unknown")
                print(f"    {sol}:{prob}")
            if len(expected_not_declared) > 3:
                print(dim(f"    ... and {len(expected_not_declared) - 3} more"))

        if manual_not_declared:
            print(f"  {Colors.YELLOW}Manually added (need problem mapping):{Colors.RESET}")
            for sol in sorted(manual_not_declared)[:3]:
                print(f"    {sol}:???")
            if len(manual_not_declared) > 3:
                print(dim(f"    ... and {len(manual_not_declared) - 3} more"))

        print()


def print_summary(result: dict, pairs_file: Optional[Path]):
    """Print final summary status."""
    has_issues = (
        len(result["missing_generation"]) > 0 or
        len(result["declared_invalid"]) > 0 or
        (pairs_file and len(result["not_in_pairs"]) > 0)
    )

    if not has_issues:
        print(success("All checks passed"))
        if pairs_file:
            print(f"  {Colors.DIM}Ready:{Colors.RESET} frontier-eval batch --pairs-file {pairs_file}")
        print()


# ============================================================================
# Main
# ============================================================================

def main():
    base_dir = Path(__file__).parent  # research/scripts/
    research_dir = base_dir.parent  # research/
    repo_root = research_dir.parent  # Root of repository

    parser = argparse.ArgumentParser(
        description="Check solution coverage and eval_targets.txt consistency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--problems-file",
        type=Path,
        default=base_dir / "problems.txt",
        help="Problems file (default: research/scripts/problems.txt)",
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        default=base_dir / "models.txt",
        help="Models file (default: research/scripts/models.txt)",
    )
    parser.add_argument(
        "--variants-file",
        type=Path,
        default=base_dir / "num_solutions.txt",
        help="Variants file (default: research/scripts/num_solutions.txt)",
    )
    parser.add_argument(
        "--solutions-dir",
        type=Path,
        default=repo_root / "solutions",
        help="Solutions directory (default: solutions/)",
    )
    parser.add_argument(
        "--pairs-file",
        type=Path,
        help="Pairs file to check (default: eval_targets.txt if exists)",
    )
    parser.add_argument(
        "--no-pairs",
        action="store_true",
        help="Skip eval_targets.txt check even if it exists",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    # Default pairs file to eval_targets.txt if not specified
    pairs_file = args.pairs_file
    if pairs_file is None and not args.no_pairs:
        default_pairs = repo_root / "eval_targets.txt"
        if default_pairs.exists():
            pairs_file = default_pairs

    # Read config files
    problems = read_problem_list(args.problems_file) if args.problems_file.exists() else []
    models = read_models_list(args.models_file) if args.models_file.exists() else []
    variants = read_variant_indices(args.variants_file) if args.variants_file.exists() else [0]

    if not problems:
        print(warning(f"No problems found in {args.problems_file}"))
    if not models:
        print(warning(f"No models found in {args.models_file}"))

    # Compute expected
    expected = compute_expected(problems, models, variants) if problems and models else {}

    # Collect actual
    actual = collect_actual(args.solutions_dir)

    # Read pairs
    declared = read_pairs_file(pairs_file) if pairs_file else []

    # Analyze
    result = analyze(expected, actual, declared)

    # Print reports
    print()

    if expected:
        print_coverage_report(result, models)

    if pairs_file:
        print_pairs_report(result, pairs_file)

    print_summary(result, pairs_file)

    # Exit code
    has_errors = (
        len(result["declared_invalid"]) > 0  # Invalid pairs
    )
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
