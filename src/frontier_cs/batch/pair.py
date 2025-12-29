"""
Pair expansion and management for batch evaluation.

A Pair represents a (solution, problem) combination to evaluate.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..models import get_model_prefix, sanitize_problem_name
from ..gen.solution_format import parse_solution_filename, format_solution_filename


@dataclass
class Pair:
    """Represents a solution-problem pair for evaluation."""

    solution: str  # Solution filename (e.g., "flash_attn.gpt5.py")
    problem: str   # Problem identifier (e.g., "flash_attn")

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


# get_model_prefix and sanitize_problem_name imported from ..models


def expand_pairs(
    problems: List[str],
    models: List[str],
    variants: Optional[List[int]] = None,
    *,
    solutions_dir: Optional[Path] = None,
    validate_paths: bool = True,
    ext: str = "py",
) -> List[Pair]:
    """
    Expand problems × models × variants into pairs.

    Args:
        problems: List of problem IDs (e.g., ["flash_attn", "cross_entropy"])
        models: List of model names (e.g., ["gpt-5", "claude-sonnet-4-5"])
        variants: List of variant indices (default: [0] for no suffix)
        solutions_dir: Directory containing solutions (for validation)
        validate_paths: Whether to validate solution paths exist
        ext: File extension (default: "py", use "cpp" for algorithmic)

    Returns:
        List of Pair objects
    """
    if variants is None:
        variants = [0]

    pairs: List[Pair] = []

    for problem in problems:
        problem_name = sanitize_problem_name(problem)

        for model in models:
            model_prefix = get_model_prefix(model)

            for variant_idx in variants:
                # Flat format: {problem}.{model}.{ext} or {problem}.{model}_{variant}.{ext}
                variant_suffix = "" if variant_idx == 0 else f"_{variant_idx}"
                model_with_variant = f"{model_prefix}{variant_suffix}"
                solution_filename = format_solution_filename(problem_name, model_with_variant, ext)

                if validate_paths and solutions_dir:
                    solution_path = solutions_dir / solution_filename
                    if not solution_path.exists():
                        continue

                pairs.append(Pair(solution=solution_filename, problem=problem))

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


def scan_solutions_dir(solutions_dir: Path) -> List[Pair]:
    """
    Scan solutions directory and build pairs from flat solution files.

    New format: {problem}.{model}.py (e.g., flash_attn.gpt5.py)
    Problem is parsed from the filename.

    Args:
        solutions_dir: Path to solutions directory

    Returns:
        List of Pair objects for valid solution files
    """
    pairs: List[Pair] = []

    if not solutions_dir.is_dir():
        return pairs

    for solution_path in sorted(solutions_dir.iterdir()):
        if not solution_path.is_file() or solution_path.name.startswith("."):
            continue

        parsed = parse_solution_filename(solution_path.name)
        if parsed:
            problem, _, _ = parsed
            pairs.append(Pair(solution=solution_path.name, problem=problem))

    return pairs
