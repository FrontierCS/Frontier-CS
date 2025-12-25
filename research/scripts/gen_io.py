"""File I/O utilities for solution generation."""

import re
from pathlib import Path
from typing import Dict, List, Tuple


def load_env_file(env_path: Path) -> None:
    """Load environment variables from a .env file."""
    from dotenv import load_dotenv
    if env_path.is_file():
        load_dotenv(env_path)


def load_solution_targets(path: Path) -> List[Tuple[str, str]]:
    """Load solution:problem pairs from a solutions file."""
    if not path.is_file():
        raise FileNotFoundError(f"Solutions file not found: {path}")
    targets = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and ":" in line:
            solution, problem = line.split(":", 1)
            targets.append((solution.strip(), problem.strip()))
    return targets


def read_models_file(path: Path) -> List[str]:
    """Read model names from a file (one per line)."""
    if not path.is_file():
        return []
    models = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            models.append(line)
    return models


def read_variant_indices_file(path: Path) -> List[int]:
    """Read variant indices from file (one integer per line)."""
    if not path.is_file():
        return [0]
    indices = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            indices.append(int(line))
    return indices or [0]


def read_readme(problem_path: Path) -> str:
    """Read the README file from a problem directory."""
    for name in ["readme", "README.md", "README", "readme.md"]:
        readme = problem_path / name
        if readme.exists():
            return readme.read_text(encoding='utf-8')
    raise FileNotFoundError(f"No README in {problem_path}")


def load_docker_config(config_path: Path) -> Dict[str, Tuple[str, bool, bool]]:
    """
    Load docker image configuration from docker_images.txt.

    Returns:
        Dict mapping problem_name -> (image, gpu_enabled, dind_enabled)
    """
    if not config_path.exists():
        return {}

    config = {}
    for line in config_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        problem_name, rest = line.split("=", 1)
        parts = rest.split(",")
        image = parts[0].strip() if parts else ""

        gpu_enabled = False
        dind_enabled = False

        for part in parts[1:]:
            part = part.strip().lower()
            if part in ("gpu", "true", "1"):
                gpu_enabled = True
            elif part in ("dind", "docker"):
                dind_enabled = True

        config[problem_name.strip()] = (image, gpu_enabled, dind_enabled)

    return config


def write_problems_from_pairs(pairs_path: Path, target_path: Path) -> None:
    """Extract problem paths from a pairs file and write to a problems file."""
    if not pairs_path.is_file():
        return

    problems: List[str] = []
    seen: set[str] = set()
    for raw_line in pairs_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        _, problem = stripped.split(":", 1)
        problem_clean = problem.strip()
        if not problem_clean:
            continue
        if not problem_clean.startswith("research/") and not problem_clean.startswith("./research/"):
            problem_clean = f"research/{problem_clean.lstrip('./')}"
        if problem_clean not in seen:
            seen.add(problem_clean)
            problems.append(problem_clean)

    if not problems:
        return

    target_path.write_text("\n".join(problems) + "\n", encoding="utf-8")


def sanitize_model_suffix(model: str) -> str:
    """Sanitize model name for use as a filename suffix."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_") or "model"


def get_problem_name(problem_path: Path) -> str:
    """
    Extract the problem name from the problem path.
    Returns just the problem identifier without any model prefix.
    Examples:
    - research/vdb_pareto/balanced -> vdb_pareto_balanced
    - research/cant_be_late_multi/high_availability -> cant_be_late_multi_high_availability
    """
    if problem_path.is_absolute():
        try:
            problem_path = problem_path.relative_to(problem_path.anchor)
        except ValueError:
            pass

    parts = [p for p in problem_path.parts if p and p != "problems"]
    if not parts:
        raise ValueError(f"Unable to derive problem name from '{problem_path}'")
    return "_".join(parts)
