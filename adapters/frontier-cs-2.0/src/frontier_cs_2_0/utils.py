from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FrontierCS20Problem:
    """Parsed metadata for a Frontier-CS 2.0 problem."""

    problem_id: str
    task_id: str
    problem_dir: Path
    statement: str
    tag: str
    language: str
    timeout_seconds: int
    docker_image: str
    config: dict[str, Any]


def load_problem_config(config_path: Path) -> dict[str, Any]:
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def normalize_task_id(problem_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", problem_id).strip("-").lower()
    return f"frontier-cs-2-0-{slug}"


def read_problem_statement(problem_dir: Path) -> str:
    for name in ("readme", "statement.txt", "README.md"):
        path = problem_dir / name
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""
