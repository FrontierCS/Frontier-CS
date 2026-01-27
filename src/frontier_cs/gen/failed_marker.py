"""Failed marker file utilities for solution generation."""

import json
from datetime import datetime
from pathlib import Path


def get_failed_path(solution_path: Path) -> Path:
    """Get the .FAILED file path for a solution."""
    return solution_path.with_suffix(".FAILED")


def has_failed_marker(solution_path: Path) -> bool:
    """Check if a .FAILED file exists for this solution."""
    return get_failed_path(solution_path).exists()


def write_failed_marker(solution_path: Path, error: str, model: str) -> None:
    """Write a .FAILED marker file for a failed generation."""
    failed_path = get_failed_path(solution_path)
    failed_path.parent.mkdir(parents=True, exist_ok=True)
    failed_path.write_text(json.dumps({
        "error": error,
        "model": model,
        "timestamp": datetime.now().isoformat(),
    }, indent=2), encoding="utf-8")
