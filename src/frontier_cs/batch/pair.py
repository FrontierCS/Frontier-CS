"""
Pair expansion and management for batch evaluation.

A Pair represents a (solution, problem) combination to evaluate.

Solution structure (nested):
    solutions/{problem}/{model}.{ext}
    solutions/{problem}/{model}_{variant}.{ext}

Examples:
    solutions/flash_attn/gpt5.py
    solutions/llm_sql/large/claude4.5sonnet_1.py
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..models import get_model_prefix
from ..gen.solution_format import format_solution_filename, get_solution_path


@dataclass
class Pair:
    """Represents a solution-problem pair for evaluation."""

    solution: str  # Relative path to solution (e.g., "flash_attn/gpt5.py")
    problem: str   # Problem identifier (e.g., "flash_attn", "llm_sql/large")

    @property
    def id(self) -> str:
        """Unique identifier for this pair."""
        return f"{self.solution}:{self.problem}"

    @property
    def safe_name(self) -> str:
        """Filesystem-safe name for this pair."""
        base = f"{self.solution}-{self.problem}"
        digest = hashlib.md5(base.encode("utf-8")).hexdigest()[:8]
        sanitized = _sanitize_name(base)
        suffix = f"-{digest}"
        max_len = 63
        available = max_len - len(suffix)
        trimmed = sanitized[:available].rstrip("-")
        return _sanitize_name(f"{trimmed}{suffix}")

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Pair):
            return self.id == other.id
        return False


def _sanitize_name(name: str) -> str:
    """Sanitize a name to be a valid cluster/file name."""
    cleaned = []
    valid = "abcdefghijklmnopqrstuvwxyz0123456789-"
    last_dash = False
    for ch in name.lower():
        if ch in valid:
            cleaned.append(ch)
            last_dash = ch == "-"
        else:
            if not last_dash:
                cleaned.append("-")
                last_dash = True
    sanitized = "".join(cleaned).strip("-")
    return sanitized or "job"


def _interleave_pairs(pairs: List[Pair]) -> List[Pair]:
    """
    Interleave pairs by problem for better load balancing.

    Instead of evaluating all solutions for problem A, then all for problem B,
    this interleaves them: A1, B1, C1, A2, B2, C2, ...
    """
    from collections import defaultdict

    # Group pairs by problem
    by_problem: dict = defaultdict(list)
    for pair in pairs:
        by_problem[pair.problem].append(pair)

    # Interleave: round-robin across problems
    result: List[Pair] = []
    problems = list(by_problem.keys())
    max_len = max(len(v) for v in by_problem.values()) if by_problem else 0

    for i in range(max_len):
        for problem in problems:
            if i < len(by_problem[problem]):
                result.append(by_problem[problem][i])

    return result


def expand_pairs(
    problems: List[str],
    models: List[str],
    variants: Optional[List[int]] = None,
    *,
    solutions_dir: Optional[Path] = None,
    validate_paths: bool = True,
    ext: str = "py",
    interleave: bool = True,
) -> List[Pair]:
    """
    Expand problems × models × variants into pairs.

    Args:
        problems: List of problem IDs (e.g., ["flash_attn", "llm_sql/large"])
        models: List of model names (e.g., ["gpt-5", "claude-sonnet-4-5"])
        variants: List of variant indices (default: [0] for no suffix)
        solutions_dir: Directory containing solutions (for validation)
        validate_paths: Whether to validate solution paths exist
        ext: File extension (default: "py", use "cpp" for algorithmic)
        interleave: Interleave pairs by problem for load balancing (default: True)

    Returns:
        List of Pair objects
    """
    if variants is None:
        variants = [0]

    pairs: List[Pair] = []

    for problem in problems:
        for model in models:
            model_prefix = get_model_prefix(model)

            for variant_idx in variants:
                # Nested format: {problem}/{model}.{ext}
                solution_path = get_solution_path(
                    solutions_dir or Path("."),
                    problem,
                    model_prefix,
                    ext,
                    variant_idx,
                )

                if validate_paths and solutions_dir:
                    if not solution_path.exists():
                        continue

                # Store relative path from solutions_dir
                rel_path = str(solution_path.relative_to(solutions_dir)) if solutions_dir else solution_path.name
                pairs.append(Pair(solution=rel_path, problem=problem))

    if interleave:
        pairs = _interleave_pairs(pairs)

    return pairs


def read_pairs_file(path: Path) -> List[Pair]:
    """
    Read pairs from a pairs file.

    Format: one pair per line as "solution:problem"
    Lines starting with # are comments.
    """
    pairs: List[Pair] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" not in stripped:
                raise ValueError(f"Invalid pair line (expected solution:problem): {stripped}")
            solution, problem = stripped.split(":", 1)
            pairs.append(Pair(solution=solution.strip(), problem=problem.strip()))

    return pairs


def read_problems_file(path: Path) -> List[str]:
    """Read problems from a problems file (one per line)."""
    problems: List[str] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Normalize: remove 'research/' prefix if present
            if stripped.startswith("research/"):
                stripped = stripped[len("research/"):]
            problems.append(stripped)

    return problems


def read_models_file(path: Path) -> List[str]:
    """Read models from a models file (one per line)."""
    models: List[str] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            models.append(stripped)

    return models


def read_variants_file(path: Path) -> List[int]:
    """Read variant indices from a file (one per line)."""
    variants: List[int] = []

    if not path.exists():
        return [0]  # Default: just index 0 (no suffix)

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                variants.append(int(stripped))
            except ValueError:
                pass

    return variants if variants else [0]


def scan_solutions_dir(solutions_dir: Path, *, interleave: bool = True) -> List[Pair]:
    """
    Scan solutions directory and build pairs from nested solution files.

    Nested format: {solutions_dir}/{problem}/{model}.{ext}
    Problem is the directory path relative to solutions_dir.

    Args:
        solutions_dir: Path to solutions directory
        interleave: Interleave pairs by problem for load balancing (default: True)

    Returns:
        List of Pair objects for valid solution files
    """
    from ..gen.solution_format import scan_solutions_dir as _scan_solutions

    pairs: List[Pair] = []

    if not solutions_dir.is_dir():
        return pairs

    for path, problem, model, variant in _scan_solutions(solutions_dir):
        rel_path = str(path.relative_to(solutions_dir))
        pairs.append(Pair(solution=rel_path, problem=problem))

    if interleave:
        pairs = _interleave_pairs(pairs)

    return pairs
