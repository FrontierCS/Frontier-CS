"""Model resolution utilities for solution generation."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .io import read_models_file


@dataclass
class ModelResolutionResult:
    """Result of model resolution."""

    models: List[str]
    source_description: str  # Human-readable source description


def resolve_models(
    model_arg: Optional[List[str]],
    models_file: Optional[Path],
    default_models_path: Path,
    base_dir: Optional[Path] = None,
) -> ModelResolutionResult:
    """Resolve model selection from CLI args or default file.

    Priority:
    1. model_arg: Direct list from --model CLI arg
    2. models_file: Path from --models-file CLI arg
    3. default_models_path: Default models.txt location

    Args:
        model_arg: List of model names from CLI (e.g., ["gpt-5", "claude-4"])
        models_file: Path to models file from CLI
        default_models_path: Default path to models.txt
        base_dir: Base directory for resolving relative paths (defaults to default_models_path.parent)

    Returns:
        ModelResolutionResult with models list and source description

    Raises:
        SystemExit: If models file not found or empty
    """
    if base_dir is None:
        base_dir = default_models_path.parent

    if model_arg:
        # Direct model list from CLI
        models_list = model_arg
        if len(models_list) == 1:
            source_desc = f"--model ({models_list[0]})"
        else:
            source_desc = f"--model ({len(models_list)} models)"
        return ModelResolutionResult(models=models_list, source_description=source_desc)

    if models_file:
        # User explicitly specified --models-file
        models_path = Path(models_file)
        if not models_path.is_absolute():
            models_path = base_dir / models_path
        if not models_path.is_file():
            print(f"ERROR: Models file not found: {models_path}")
            sys.exit(1)
        models_list = read_models_file(models_path)
        if not models_list:
            print(f"ERROR: Models file is empty: {models_path}")
            sys.exit(1)
        source_desc = f"--models-file ({models_path})"
        return ModelResolutionResult(models=models_list, source_description=source_desc)

    # Default: use default_models_path
    if not default_models_path.is_file():
        print(f"ERROR: No model specified and {default_models_path} not found.")
        print("Use --model <model> or create models.txt")
        sys.exit(1)
    models_list = read_models_file(default_models_path)
    if not models_list:
        print(f"ERROR: Models file is empty: {default_models_path}")
        sys.exit(1)
    source_desc = f"models.txt ({default_models_path})"
    return ModelResolutionResult(models=models_list, source_description=source_desc)
