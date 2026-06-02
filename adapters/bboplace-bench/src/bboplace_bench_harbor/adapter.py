from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from types import SimpleNamespace

from .utils import BBOPlaceProblem, discover_problems, load_default_timeout

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


class BBOPlaceAdapter:
    """Generate Harbor-style tasks for BBOPlace-Bench."""

    def __init__(
        self,
        source_root: Path,
        output_dir: Path,
        *,
        benchmarks: list[str] | None = None,
        placers: list[str] | None = None,
        eval_gp_hpwl: bool = False,
        limit: int | None = None,
        overwrite: bool = False,
        base_image: str = "duketomlist/bboplace-bench:2.1.0",
        allow_missing_benchmark: bool = False,
        template_dir: Path | None = None,
    ):
        self.root = Path(source_root)
        self.output_dir = Path(output_dir)
        self.benchmarks = benchmarks
        self.placers = placers
        self.eval_gp_hpwl = eval_gp_hpwl
        self.limit = limit
        self.overwrite = overwrite
        self.base_image = base_image
        self.allow_missing_benchmark = allow_missing_benchmark
        self.template_dir = Path(template_dir or TEMPLATE_DIR)
        self.timeout_seconds = load_default_timeout(self.root)

    def run(self) -> list[Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        problems = discover_problems(
            self.root,
            benchmarks=self.benchmarks,
            placers=self.placers,
            eval_gp_hpwl=self.eval_gp_hpwl,
        )
        if self.limit is not None:
            problems = problems[: self.limit]

        results: list[Path] = []
        for problem in problems:
            generated = self.generate_task(problem, overwrite=self.overwrite)
            if generated is not None:
                results.append(generated)
        return results

    def generate_task(self, problem: BBOPlaceProblem, *, overwrite: bool = False) -> Path | None:
        if problem.placer == "hpo" or problem.eval_gp_hpwl:
            LOGGER.warning(
                "Generating %s, but HPO/GP HPWL requires a DREAMPlace-enabled image",
                problem.task_id,
            )

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

        task_info = self._task_info(problem)
        self._write_instruction(task_paths, problem, task_info)
        self._write_environment(task_paths, problem, task_info)
        self._write_tests(task_paths, problem, task_info)
        self._write_solution(task_paths)
        self._write_task_config(task_paths, problem)
        LOGGER.info("  [OK] %s", problem.task_id)
        return task_paths.task_dir

    def _task_info(self, problem: BBOPlaceProblem) -> dict:
        benchmark_dir = (
            self.root / "benchmarks" / problem.benchmark_base / problem.benchmark
        )
        benchmark_available = benchmark_dir.is_dir()
        if not benchmark_available and not self.allow_missing_benchmark:
            raise FileNotFoundError(
                f"Benchmark data not found: {benchmark_dir}. "
                "Download datasets into benchmarks/ or pass --allow-missing-benchmark."
            )
        return {
            "benchmark": problem.benchmark,
            "benchmark_base": problem.benchmark_base,
            "benchmark_type": problem.benchmark_type,
            "placer": problem.placer,
            "eval_gp_hpwl": problem.eval_gp_hpwl,
            "benchmark_available_at_generation": benchmark_available,
            "objective": "minimize_hpwl",
            "reward_formula": "1 / (1 + hpwl / 1e5)",
            "max_candidates_per_submission": 256,
        }

    def _write_instruction(
        self, task_paths, problem: BBOPlaceProblem, task_info: dict
    ) -> None:
        instruction = (
            "You are optimizing a BBOPlace-Bench chip placement task through a "
            "black-box evaluator.\n\n"
            "Create `/app/solution.py`. The evaluator will import it and call "
            "`solve(info)` if present. You may also define `CANDIDATES` or "
            "`CANDIDATE`. Return either one candidate vector or a list of "
            "candidate vectors. Lower HPWL is better.\n\n"
            "Run `python3 /app/submit.py --info` to fetch exact runtime metadata, "
            "including dimension and bounds. Run `bash /app/submit.sh` at any "
            "time to evaluate `/app/solution.py`; the best successful iterative "
            "submission is preserved for final scoring.\n\n"
            "Submission policy:\n"
            "- Start by running `python3 /app/submit.py --info`.\n"
            "- As soon as you have any valid candidate, write `/app/solution.py` "
            "and run `bash /app/submit.sh`.\n"
            "- Submit after every meaningful strategy change or expected "
            "improvement before continuing.\n"
            "- Keep track of the best observed reward/HPWL and do not discard a "
            "working best solution while trying riskier variants.\n\n"
            f"Benchmark: `{problem.benchmark}` ({problem.benchmark_base}, "
            f"{problem.benchmark_type})\n"
            f"Placer formulation: `{problem.placer}`\n"
            f"Global-placement HPWL: `{problem.eval_gp_hpwl}`\n\n"
            "The reward reported to Harbor is `1 / (1 + hpwl / 1e5)`. The raw "
            "HPWL is also written to verifier artifacts.\n"
        )
        if not task_info["benchmark_available_at_generation"]:
            instruction += (
                "\nNote: this task was generated without local benchmark data. "
                "It is a structural artifact until `benchmarks/` is added and "
                "the task is regenerated.\n"
            )
        task_paths.instruction_path.write_text(instruction, encoding="utf-8")

    def _write_environment(self, task_paths, problem: BBOPlaceProblem, task_info: dict) -> None:
        env_dir = task_paths.environment_dir
        self._copy_template_files(
            env_dir,
            ["Dockerfile", "Dockerfile.judge", "docker-compose.yaml", "judge_server.py", "submit.py", "submit.sh", "bboplace_runtime.py"],
        )
        for dockerfile_name in ("Dockerfile", "Dockerfile.judge"):
            path = env_dir / dockerfile_name
            path.write_text(
                path.read_text(encoding="utf-8").replace("{base_image}", self.base_image),
                encoding="utf-8",
            )
        (env_dir / "submit.sh").chmod(0o755)
        self._write_json(env_dir / "task_info.json", task_info)
        self._copy_runtime_repo(env_dir / "bboplace-bench", problem)

    def _write_tests(self, task_paths, problem: BBOPlaceProblem, task_info: dict) -> None:
        tests_dir = task_paths.tests_dir
        self._copy_template_files(
            tests_dir,
            ["evaluate.py", "test.sh"],
            template_subdir="tests",
        )
        (tests_dir / "test.sh").chmod(0o755)
        self._write_json(tests_dir / "task_info.json", task_info)

    def _write_solution(self, task_paths) -> None:
        solve_sh = task_paths.solution_dir / "solve.sh"
        shutil.copy2(self.template_dir / "solution" / "solve.sh", solve_sh)
        solve_sh.chmod(0o755)

    def _write_task_config(self, task_paths, problem: BBOPlaceProblem) -> None:
        template = (self.template_dir / "task.toml").read_text(encoding="utf-8")
        text = template.format(
            task_id=problem.task_id,
            benchmark=problem.benchmark,
            placer=problem.placer,
            timeout_sec=self.timeout_seconds,
            agent_timeout_sec=max(10800, self.timeout_seconds),
        )
        try:
            from harbor.models.task.config import TaskConfig

            config = TaskConfig.model_validate_toml(text)
            config.source = "https://github.com/lamda-bbo/BBOPlace-Bench"
            text = config.model_dump_toml()
        except ImportError:
            pass
        task_paths.config_path.write_text(text, encoding="utf-8")

    def _copy_template_files(
        self,
        target_dir: Path,
        names: list[str],
        *,
        template_subdir: str = "environment",
    ) -> None:
        src_dir = self.template_dir / template_subdir
        for name in names:
            shutil.copy2(src_dir / name, target_dir / name)

    def _copy_runtime_repo(self, target: Path, problem: BBOPlaceProblem) -> None:
        target.mkdir(parents=True, exist_ok=True)
        for name in ("src", "config"):
            shutil.copytree(self.root / name, target / name)
        if (self.root / "requirements.txt").exists():
            shutil.copy2(self.root / "requirements.txt", target / "requirements.txt")

        self._patch_placer_registry(target / "src" / "placer" / "__init__.py")
        self._patch_evaluator_imports(target / "src" / "evaluator.py")

        benchmark_src = (
            self.root / "benchmarks" / problem.benchmark_base / problem.benchmark
        )
        if benchmark_src.exists():
            benchmark_dst = target / "benchmarks" / problem.benchmark_base / problem.benchmark
            benchmark_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(benchmark_src, benchmark_dst)

        if problem.placer == "hpo" or problem.eval_gp_hpwl:
            dreamplace_src = self.root / "thirdparty" / "dreamplace"
            if dreamplace_src.exists():
                shutil.copytree(dreamplace_src, target / "thirdparty" / "dreamplace")

    def _patch_placer_registry(self, path: Path) -> None:
        path.write_text(
            "\n".join(
                [
                    "REGISTRY = {}",
                    "from .mgo_placer import MaskGuidedOptimizationPlacer",
                    "from .sp_placer import SPPlacer",
                    "REGISTRY['mgo'] = MaskGuidedOptimizationPlacer",
                    "REGISTRY['sp'] = SPPlacer",
                    "try:",
                    "    from .hpo_placer import HPOPlacer",
                    "    REGISTRY['hpo'] = HPOPlacer",
                    "except Exception as exc:",
                    "    HPO_IMPORT_ERROR = exc",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _patch_evaluator_imports(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "from src.placer.hpo_placer import params_space",
            "\n".join(
                [
                    "try:",
                    "    from src.placer.hpo_placer import params_space",
                    "except Exception:",
                    "    params_space = {}",
                ]
            ),
        )
        path.write_text(text, encoding="utf-8")

    def _write_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
