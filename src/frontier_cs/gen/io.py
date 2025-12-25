"""Common I/O utilities for solution generation."""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


def load_env_file(env_path: Path) -> None:
    """Load environment variables from a .env file if it exists."""
    if env_path.exists():
        load_dotenv(env_path)


def read_models_file(path: Path) -> List[str]:
    """Read model names from a file (one per line, # for comments)."""
    models = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            models.append(stripped)
    return models


def read_variant_indices_file(path: Path) -> List[int]:
    """Read variant indices from a file."""
    indices = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            try:
                indices.append(int(stripped))
            except ValueError:
                pass
    return indices if indices else [0]
