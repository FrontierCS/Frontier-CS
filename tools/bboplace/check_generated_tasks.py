#!/usr/bin/env python3
"""Validate generated BBOPlace Harbor tasks for the intended evaluation flow."""

from __future__ import annotations

import sys
from pathlib import Path


EXPECTED_TASKS = (
    "frontier-cs-2-0-bboplace-ispd2005",
    "frontier-cs-2-0-bboplace-iccad2015",
)
EXPECTED_JUDGE_IMAGE = "ghcr.io/frontiercs/frontiercs-bboplace-data:2026-06-ispd-iccad"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def read(path: Path) -> str:
    require(path.exists(), f"missing generated file: {path}")
    return path.read_text(encoding="utf-8")


def check_task(task_dir: Path) -> None:
    env_dir = task_dir / "environment"
    tests_dir = task_dir / "tests"

    dockerfile = read(env_dir / "Dockerfile")
    judge_dockerfile = read(env_dir / "Dockerfile.judge")
    submit_py = read(env_dir / "submit.py")
    judge_server = read(env_dir / "judge_server.py")
    evaluate_py = read(tests_dir / "evaluate.py")
    instruction = read(task_dir / "instruction.md")

    require("FROM ubuntu:24.04" in dockerfile, f"{task_dir.name}: main image changed")
    require(
        f"FROM {EXPECTED_JUDGE_IMAGE}" in judge_dockerfile,
        f"{task_dir.name}: judge image is not the BBOPlace data image",
    )
    require("{verifier_token}" not in judge_server, f"{task_dir.name}: judge token placeholder leaked")
    require("{verifier_token}" not in evaluate_py, f"{task_dir.name}: test token placeholder leaked")
    require("FINAL_ROLE_TOKEN" not in submit_py, f"{task_dir.name}: final token leaked to agent submit helper")
    require("X-Frontier-CS-Role-Token" not in submit_py, f"{task_dir.name}: final token header leaked to agent")
    require("submission_role\": \"agent\"" in submit_py, f"{task_dir.name}: submit helper does not mark agent role")
    require("final evaluation role is verifier-only" in judge_server, f"{task_dir.name}: judge does not guard final role")
    require("Runtime and resources" in instruction, f"{task_dir.name}: missing resource statement")
    require("no GPU" in instruction, f"{task_dir.name}: missing no-GPU statement")
    require(
        "`max_candidates_per_submission`: 16" in instruction,
        f"{task_dir.name}: candidate limit should be 16",
    )
    require("quick-feedback score is never used directly" in instruction, f"{task_dir.name}: missing quick/full warning")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_generated_tasks.py /path/to/generated/frontier-cs-2.0", file=sys.stderr)
        return 2
    root = Path(argv[1])
    for task_name in EXPECTED_TASKS:
        check_task(root / task_name)
    print("Generated BBOPlace tasks match the expected Harbor flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
