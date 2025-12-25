"""Solution file naming utilities.

Standard format: {problem}.{model}.{ext}

Examples:
    flash_attn.gpt5.py      -> problem=flash_attn, model=gpt5
    cross_entropy.claude.py -> problem=cross_entropy, model=claude
    1.gpt5.cpp              -> problem=1, model=gpt5
"""

import re
from pathlib import Path
from typing import Optional, Tuple


def validate_problem_name(problem: str) -> None:
    """Validate that a problem name doesn't contain dots."""
    if '.' in problem:
        raise ValueError(f"Problem name cannot contain '.': {problem}")


def parse_solution_filename(filename: str) -> Optional[Tuple[str, str, str]]:
    """Parse a solution filename into (problem, model, ext).

    Format: {problem}.{model}.{ext}
    - problem: first segment (before first dot)
    - ext: last segment (after last dot)
    - model: everything in between (may contain dots like gpt5.1)

    Examples:
        flash_attn.gpt5.py -> (flash_attn, gpt5, py)
        0.gpt5.2.cpp -> (0, gpt5.2, cpp)
        cant_be_late.gemini2.5pro.py -> (cant_be_late, gemini2.5pro, py)

    Args:
        filename: Filename like "flash_attn.gpt5.py" or "0.gpt5.2.cpp"

    Returns:
        Tuple of (problem, model, ext) or None if not parseable
    """
    # Must have at least 2 dots: problem.model.ext
    if filename.count('.') < 2:
        return None

    # Extension is after the last dot
    base, ext = filename.rsplit('.', 1)
    if not ext:
        return None

    # Problem is before the first dot, model is everything in between
    first_dot = base.find('.')
    if first_dot == -1:
        return None

    problem = base[:first_dot]
    model = base[first_dot + 1:]

    if not problem or not model:
        return None

    return problem, model, ext


def format_solution_filename(problem: str, model: str, ext: str) -> str:
    """Format a solution filename.

    Args:
        problem: Problem ID (e.g., "flash_attn", "1")
        model: Model prefix (e.g., "gpt5", "claude")
        ext: File extension without dot (e.g., "py", "cpp")

    Returns:
        Filename like "flash_attn.gpt5.py"
    """
    validate_problem_name(problem)
    return f"{problem}.{model}.{ext}"


def get_solution_path(
    solutions_dir: Path,
    problem: str,
    model: str,
    ext: str,
) -> Path:
    """Get the path for a solution file.

    Args:
        solutions_dir: Directory containing solutions
        problem: Problem ID
        model: Model prefix
        ext: File extension without dot

    Returns:
        Path to the solution file
    """
    filename = format_solution_filename(problem, model, ext)
    return solutions_dir / filename


def scan_solutions_dir(solutions_dir: Path) -> list[Tuple[Path, str, str]]:
    """Scan a solutions directory for solution files.

    Args:
        solutions_dir: Directory to scan

    Returns:
        List of (path, problem, model) tuples
    """
    results = []
    if not solutions_dir.is_dir():
        return results

    for path in solutions_dir.iterdir():
        if not path.is_file():
            continue
        parsed = parse_solution_filename(path.name)
        if parsed:
            problem, model, _ = parsed
            results.append((path, problem, model))

    return results
