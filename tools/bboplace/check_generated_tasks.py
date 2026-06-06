#!/usr/bin/env python3
"""Validate generated BBOPlace Harbor tasks for the intended evaluation flow."""

from __future__ import annotations

import sys
from pathlib import Path


EXPECTED_TASKS = {
    "frontier-cs-2-0-bboplace-ispd2005": {
        "candidate_limit": 16,
        "submission_path": "/app/solution.py",
        "required_text": "quick-feedback score is never used directly",
    },
    "frontier-cs-2-0-bboplace-iccad2015": {
        "candidate_limit": 16,
        "submission_path": "/app/solution.py",
        "required_text": "quick-feedback score is never used directly",
    },
    "frontier-cs-2-0-bboplace-direct-ispd2005": {
        "candidate_limit": 1,
        "submission_path": "/app/solution.json",
        "required_text": "Submit exactly one placement for `adaptec1`",
        "visible_input_copy": (
            "COPY --from=visible_input_0 "
            "/opt/bboplace-bench/benchmarks/ispd2005/adaptec1 "
            "/app/input/benchmarks/ispd2005/adaptec1"
        ),
    },
    "frontier-cs-2-0-bboplace-direct-iccad2015": {
        "candidate_limit": 1,
        "submission_path": "/app/solution.json",
        "required_text": "Submit exactly one placement for `superblue1`",
        "visible_input_copy": (
            "COPY --from=visible_input_0 "
            "/opt/bboplace-bench/benchmarks/iccad2015/superblue1 "
            "/app/input/benchmarks/iccad2015/superblue1"
        ),
    },
}
EXPECTED_JUDGE_IMAGE = "ghcr.io/frontiercs/frontiercs-bboplace-data:2026-06-ispd-iccad"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def read(path: Path) -> str:
    require(path.exists(), f"missing generated file: {path}")
    return path.read_text(encoding="utf-8")


def check_task(task_dir: Path, expected: dict[str, object]) -> None:
    env_dir = task_dir / "environment"
    tests_dir = task_dir / "tests"

    dockerfile = read(env_dir / "Dockerfile")
    judge_dockerfile = read(env_dir / "Dockerfile.judge")
    submit_py = read(env_dir / "submit.py")
    judge_server = read(env_dir / "judge_server.py")
    evaluate_py = read(tests_dir / "evaluate.py")
    instruction = read(task_dir / "instruction.md")
    submission_config = read(env_dir / "submission_config.json")

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
        f"`max_candidates_per_submission`: {expected['candidate_limit']}" in instruction
        or f"max_candidates_per_submission: {expected['candidate_limit']}" in instruction
        or f"Only one placement is accepted" in instruction,
        f"{task_dir.name}: candidate limit should be {expected['candidate_limit']}",
    )
    require(
        str(expected["required_text"]) in instruction,
        f"{task_dir.name}: missing expected BBOPlace instruction text",
    )
    require(
        str(expected["submission_path"]) in submission_config,
        f"{task_dir.name}: generated submission path mismatch",
    )
    visible_input_copy = expected.get("visible_input_copy")
    if visible_input_copy:
        require(
            "FROM ghcr.io/frontiercs/frontiercs-bboplace-data:2026-06-ispd-iccad AS visible_input_0"
            in dockerfile,
            f"{task_dir.name}: missing visible input image stage",
        )
        require(
            str(visible_input_copy) in dockerfile,
            f"{task_dir.name}: missing visible input copy",
        )
        require(
            not (env_dir / "harbor_app" / "input").exists(),
            f"{task_dir.name}: generated context should not include raw visible input",
        )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_generated_tasks.py /path/to/generated/frontier-cs-2.0", file=sys.stderr)
        return 2
    root = Path(argv[1])
    for task_name, expected in EXPECTED_TASKS.items():
        check_task(root / task_name, expected)
    print("Generated BBOPlace tasks match the expected Harbor flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
