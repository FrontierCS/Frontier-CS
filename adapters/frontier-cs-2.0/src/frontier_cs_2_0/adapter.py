from __future__ import annotations

import logging
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from harbor.models.task.paths import TaskPaths

from .utils import (
    FrontierCS20Problem,
    load_problem_config,
    normalize_task_id,
    read_problem_statement,
)

LOGGER = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "task-template"


def _make_task_paths(task_dir: Path):
    try:
        from harbor.models.task.paths import TaskPaths

        return TaskPaths(task_dir=task_dir)
    except ImportError:
        return SimpleNamespace(
            task_dir=task_dir,
            environment_dir=task_dir / "environment",
            solution_dir=task_dir / "solution",
            tests_dir=task_dir / "tests",
            instruction_path=task_dir / "instruction.md",
            config_path=task_dir / "task.toml",
        )


def discover_problems(frontier_cs_root: Path) -> list[FrontierCS20Problem]:
    """Scan the Frontier-CS repo and load metadata for all 2.0 problems."""
    problems_dir = frontier_cs_root / "2.0" / "problems"
    problems: list[FrontierCS20Problem] = []

    if not problems_dir.is_dir():
        raise FileNotFoundError(f"Frontier-CS 2.0 problems not found: {problems_dir}")

    for evaluator_path in sorted(problems_dir.rglob("evaluator.py")):
        problem_dir = evaluator_path.parent
        config_path = problem_dir / "config.yaml"
        config = load_problem_config(config_path) if config_path.exists() else {}
        runtime = config.get("runtime", {}) or {}
        docker = runtime.get("docker", {}) or {}
        rel_id = str(problem_dir.relative_to(problems_dir))

        problems.append(
            FrontierCS20Problem(
                problem_id=rel_id,
                task_id=normalize_task_id(rel_id),
                problem_dir=problem_dir,
                statement=read_problem_statement(problem_dir),
                tag=str(config.get("tag", "optimization")),
                language=str(runtime.get("language", "python")),
                timeout_seconds=int(runtime.get("timeout_seconds", 10800)),
                docker_image=str(docker.get("image", "ubuntu:24.04")),
            )
        )

    return problems


class FrontierCS20Adapter:
    """Generate Harbor tasks for Frontier-CS 2.0 problems."""

    def __init__(
        self,
        frontier_cs_root: Path,
        output_dir: Path,
        *,
        limit: int | None = None,
        overwrite: bool = False,
        task_ids: Iterable[str] | None = None,
        template_dir: Path | None = None,
        docker_image: str | None = None,
    ):
        self.root = Path(frontier_cs_root)
        self.output_dir = Path(output_dir)
        self.limit = limit
        self.overwrite = overwrite
        self.task_ids = set(task_ids) if task_ids is not None else None
        self.template_dir = Path(template_dir or TEMPLATE_DIR)
        self.docker_image = docker_image

    def run(self) -> list[Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        problems = discover_problems(self.root)
        if self.task_ids is not None:
            problems = [p for p in problems if p.problem_id in self.task_ids]
        if self.limit is not None:
            problems = problems[: self.limit]

        results: list[Path] = []
        for problem in problems:
            generated = self.generate_task(problem, overwrite=self.overwrite)
            if generated is not None:
                results.append(generated)
        return results

    def generate_task(
        self, problem: FrontierCS20Problem, *, overwrite: bool = False
    ) -> Path | None:
        task_dir = self.output_dir / problem.task_id
        if task_dir.exists():
            if not overwrite:
                LOGGER.info("Skipping %s (already exists)", task_dir.name)
                return None
            shutil.rmtree(task_dir)

        task_paths = _make_task_paths(task_dir)
        task_paths.task_dir.mkdir(parents=True, exist_ok=True)
        task_paths.environment_dir.mkdir(parents=True, exist_ok=True)
        task_paths.solution_dir.mkdir(parents=True, exist_ok=True)
        task_paths.tests_dir.mkdir(parents=True, exist_ok=True)

        self._write_instruction(task_paths, problem)
        self._write_environment(task_paths, problem)
        self._write_tests(task_paths, problem)
        self._write_solution(task_paths, problem)
        self._write_task_config(task_paths, problem)
        LOGGER.info("  [OK] %s", problem.problem_id)
        return task_paths.task_dir

    def _write_instruction(self, task_paths: "TaskPaths", problem: FrontierCS20Problem) -> None:
        instruction = (
            "You are solving a Frontier-CS 2.0 open-ended optimization problem.\n\n"
            "Create a Python solution at `/app/solution.py`. You can call "
            "`bash /app/submit.sh` at any time to grade the current solution "
            "with the same black-box judge used by the final verifier and get "
            "score feedback. The evaluator implementation is intentionally not "
            "available in the agent workspace.\n\n"
            f"Problem id: `{problem.problem_id}`\n"
            f"Language: `{problem.language}`\n"
            f"Time limit: `{problem.timeout_seconds}s`\n\n"
            "Original problem statement:\n\n"
            f"{problem.statement.rstrip()}\n"
        )
        task_paths.instruction_path.write_text(instruction, encoding="utf-8")

    def _write_environment(self, task_paths: "TaskPaths", problem: FrontierCS20Problem) -> None:
        env_dir = task_paths.environment_dir
        dockerfile = (self.template_dir / "environment" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        image = self.docker_image or problem.docker_image
        env_dir.joinpath("Dockerfile").write_text(
            dockerfile.replace("{base_image}", image),
            encoding="utf-8",
        )

        for name in ("readme", "config.yaml"):
            src = problem.problem_dir / name
            if src.exists():
                shutil.copy2(src, env_dir / name)

        judge_dockerfile = (
            self.template_dir / "environment" / "Dockerfile.judge"
        ).read_text(encoding="utf-8")
        env_dir.joinpath("Dockerfile.judge").write_text(
            judge_dockerfile.replace("{base_image}", image),
            encoding="utf-8",
        )
        for name in ("docker-compose.yaml", "judge_server.py", "submit.py"):
            shutil.copy2(self.template_dir / "environment" / name, env_dir / name)
        # Kept in the build context for the judge image only; the main agent
        # image's Dockerfile does not copy this into /app.
        shutil.copy2(problem.problem_dir / "evaluator.py", env_dir / "problem_evaluator.py")
        submit_sh = env_dir / "submit.sh"
        shutil.copy2(self.template_dir / "environment" / "submit.sh", submit_sh)
        submit_sh.chmod(0o755)

    def _write_tests(self, task_paths: "TaskPaths", problem: FrontierCS20Problem) -> None:
        tests_dir = task_paths.tests_dir
        shutil.copy2(self.template_dir / "tests" / "test.sh", tests_dir / "test.sh")
        shutil.copy2(self.template_dir / "tests" / "evaluate.py", tests_dir / "evaluate.py")
        shutil.copy2(problem.problem_dir / "evaluator.py", tests_dir / "problem_evaluator.py")
        (tests_dir / "test.sh").chmod(0o755)

    def _write_solution(self, task_paths: "TaskPaths", problem: FrontierCS20Problem) -> None:
        solution_dir = task_paths.solution_dir
        reference = problem.problem_dir / "reference.py"
        if reference.exists():
            shutil.copy2(reference, solution_dir / "reference.py")
        solve_sh = solution_dir / "solve.sh"
        shutil.copy2(self.template_dir / "solution" / "solve.sh", solve_sh)
        solve_sh.chmod(0o755)

    def _write_task_config(self, task_paths: "TaskPaths", problem: FrontierCS20Problem) -> None:
        template = (self.template_dir / "task.toml").read_text(encoding="utf-8")
        text = template.format(
            task_id=problem.task_id,
            problem_id=problem.problem_id,
            tag=problem.tag,
            timeout_sec=problem.timeout_seconds,
            agent_timeout_sec=max(10800, problem.timeout_seconds),
        )
        try:
            from harbor.models.task.config import TaskConfig

            config = TaskConfig.model_validate_toml(text)
            config.source = "https://github.com/FrontierCS/Frontier-CS"
            text = config.model_dump_toml()
        except ImportError:
            pass
        task_paths.config_path.write_text(text, encoding="utf-8")
