"""Solution file naming utilities.

Nested format: {solutions_dir}/{problem}/{model}.{ext}

Examples:
    solutions/flash_attn/gpt5.py           -> problem=flash_attn, model=gpt5
    solutions/llm_sql/large/claude4.5sonnet_1.py -> problem=llm_sql/large, model=claude4.5sonnet, variant=1
    algorithmic/solutions/1/gpt5.cpp       -> problem=1, model=gpt5
"""

from pathlib import Path
from typing import Optional, Tuple


def parse_solution_filename(filename: str) -> Optional[Tuple[str, int, str]]:
    """Parse a solution filename into (model, variant, ext).

    Format: {model}.{ext} or {model}_{variant}.{ext}

    Examples:
        gpt5.py -> (gpt5, 0, py)
        gpt5_1.py -> (gpt5, 1, py)
        claude4.5sonnet_2.cpp -> (claude4.5sonnet, 2, cpp)

    Args:
        filename: Filename like "gpt5.py" or "gpt5_1.cpp"

    Returns:
        Tuple of (model, variant, ext) or None if not parseable
    """
    if '.' not in filename:
        return None

    stem, ext = filename.rsplit('.', 1)
    if not ext or not stem:
        return None

    # Check for variant suffix: model_N
    parts = stem.rsplit('_', 1)
    if len(parts) == 2 and parts[1].isdigit():
        model = parts[0]
        variant = int(parts[1])
    else:
        model = stem
        variant = 0

    return model, variant, ext


def format_solution_filename(model: str, ext: str, variant: int = 0) -> str:
    """Format a solution filename.

    Args:
        model: Model prefix (e.g., "gpt5", "claude4.5sonnet")
        ext: File extension without dot (e.g., "py", "cpp")
        variant: Variant index (0 = no suffix)

    Returns:
        Filename like "gpt5.py" or "gpt5_1.py"
    """
    suffix = "" if variant == 0 else f"_{variant}"
    return f"{model}{suffix}.{ext}"


def get_solution_path(
    solutions_dir: Path,
    problem: str,
    model: str,
    ext: str,
    variant: int = 0,
) -> Path:
    """Get the path for a solution file.

    Nested format: {solutions_dir}/{problem}/{model}.{ext}

    Args:
        solutions_dir: Directory containing solutions
        problem: Problem ID (e.g., "flash_attn", "llm_sql/large")
        model: Model prefix (e.g., "gpt5", "claude4.5sonnet")
        ext: File extension without dot (e.g., "py", "cpp")
        variant: Variant index (0 = no suffix)

    Returns:
        Path to the solution file
    """
    filename = format_solution_filename(model, ext, variant)
    return solutions_dir / problem / filename


def parse_solution_path(
    solution_path: Path,
    solutions_dir: Path,
) -> Optional[Tuple[str, str, int, str]]:
    """Parse a solution file path into components.

    Args:
        solution_path: Full path to solution file
        solutions_dir: Base solutions directory

    Returns:
        Tuple of (problem, model, variant, ext) or None if not parseable
    """
    try:
        rel = solution_path.relative_to(solutions_dir)
    except ValueError:
        return None

    # Problem is the directory path (all parent dirs relative to solutions_dir)
    problem = str(rel.parent)
    if problem == '.':
        return None  # File directly in solutions_dir is invalid

    # Parse filename
    parsed = parse_solution_filename(solution_path.name)
    if not parsed:
        return None

    model, variant, ext = parsed
    return problem, model, variant, ext


def scan_solutions_dir(solutions_dir: Path) -> list[Tuple[Path, str, str, int]]:
    """Scan a solutions directory for solution files (nested structure).

    Args:
        solutions_dir: Directory to scan

    Returns:
        List of (path, problem, model, variant) tuples
    """
    results = []
    if not solutions_dir.is_dir():
        return results

    # Recursively find all solution files
    for path in solutions_dir.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue

        parsed = parse_solution_path(path, solutions_dir)
        if parsed:
            problem, model, variant, _ = parsed
            results.append((path, problem, model, variant))

    return results
