"""Run single simulations without shelling out to the CLI."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Iterable, Type


# Common directory (where this file lives)
COMMON_DIR = os.path.dirname(os.path.abspath(__file__))
SIM_ROOT = os.path.join(COMMON_DIR, "cant-be-late-simulator")

if SIM_ROOT not in sys.path:
    sys.path.insert(0, SIM_ROOT)

try:  # pragma: no cover - provides no-op wandb in minimal environments
    import wandb  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised in evaluator environment
    class _WandbStub:
        run = None

        class _Config:
            def update(self, *args, **kwargs):
                return None

        config = _Config()

        @staticmethod
        def init(*args, **kwargs):  # noqa: D401
            """No-op replacement for wandb.init."""
            return None

        @staticmethod
        def log(*args, **kwargs):
            return None

    wandb = _WandbStub()
    sys.modules["wandb"] = wandb

if not hasattr(wandb, "run"):
    wandb.run = None

from sky_spot import simulate
from sky_spot.env import TraceEnv
from sky_spot.task import ChainedTask, SingleTask, Task
from sky_spot.strategies import strategy as strategy_lib

_OUTPUT_BASE = Path(
    os.environ.get(
        "GEPA_EVAL_TMPDIR",
        os.path.join(tempfile.gettempdir(), "gepa_evaluator_runs"),
    )
)
_OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

_STRATEGY_CACHE: dict[str, Type[strategy_lib.Strategy]] = {}


@dataclass
class SimulationFailure(Exception):
    error_msg: str
    def __str__(self) -> str:  # pragma: no cover - repr helper
        return self.error_msg


class _PresetArgumentParser(argparse.ArgumentParser):
    """Parser that replays a precomputed argv when strategies parse args."""

    def __init__(self, *args, preset_args: Iterable[str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._preset_args = list(preset_args or [])

    def parse_known_args(self, args=None, namespace=None):  # pragma: no cover - passthrough
        if args is None:
            args = list(self._preset_args)
        return super().parse_known_args(args=args, namespace=namespace)


def _load_strategy_class(module_path: str) -> Type[strategy_lib.Strategy]:
    module_path = os.path.abspath(module_path)
    cached = _STRATEGY_CACHE.get(module_path)
    if cached is not None:
        return cached

    spec = importlib.util.spec_from_file_location(Path(module_path).stem, module_path)
    if spec is None or spec.loader is None:
        raise SimulationFailure(f"Could not create module spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - surface to caller
        raise SimulationFailure(f"Failed to import strategy module: {exc}") from exc

    strategy_cls = _first_strategy_class(module, module_path)
    _STRATEGY_CACHE[module_path] = strategy_cls
    return strategy_cls


def _first_strategy_class(module: ModuleType, module_path: str) -> Type[strategy_lib.Strategy]:
    for attr in module.__dict__.values():
        if (
            isinstance(attr, type)
            and issubclass(attr, strategy_lib.Strategy)
            and attr not in {strategy_lib.Strategy, strategy_lib.MultiRegionStrategy}
        ):
            return attr
    raise SimulationFailure(f"No Strategy subclass found in {module_path}")


def _build_parser(cli_args: list[str]) -> _PresetArgumentParser:
    parser = _PresetArgumentParser(preset_args=cli_args)
    parser.add_argument("--deadline-hours", type=float, default=52.0)
    parser.add_argument("--task-duration-hours", type=float, nargs="+", default=[48.0])
    parser.add_argument("--restart-overhead-hours", type=float, nargs="+", default=[0.0])
    parser.add_argument("--env-start-hours", type=float, default=0.0)
    parser.add_argument("--output-dir", type=str, default=str(_OUTPUT_BASE))
    parser.add_argument("--trace-file", type=str)
    parser.add_argument("--strategy-file", type=str)
    parser.add_argument("--checkpoint-size-gb", type=float, default=50.0)
    parser.add_argument("--strategy", type=str, default="custom")
    parser.add_argument("--env", type=str, default="trace")
    parser.add_argument("--silent", action="store_true")
    return parser


def _build_task(args: argparse.Namespace) -> Task:
    durations = list(args.task_duration_hours)
    checkpoint = getattr(args, "checkpoint_size_gb", 50.0)
    if len(durations) == 1:
        return SingleTask({"duration": durations[0], "checkpoint_size_gb": checkpoint})
    sub_tasks = [{"duration": dur} for dur in durations]
    return ChainedTask({"sub_tasks": sub_tasks, "checkpoint_size_gb": checkpoint})


def run_single_simulation(program_path: str, trace_file: str, config: dict):
    """Run a single simulation inside the worker process.

    Returns:
        Tuple[bool, float, str]: success flag, cost, error message
    """

    program_path = os.path.abspath(program_path)
    trace_file = os.path.abspath(trace_file)

    cli_args = [
        "--deadline-hours",
        str(config["deadline"]),
        "--task-duration-hours",
        str(config["duration"]),
        "--restart-overhead-hours",
        str(config["overhead"]),
        "--trace-file",
        trace_file,
        "--strategy-file",
        program_path,
        "--output-dir",
        str(_OUTPUT_BASE),
        "--env",
        "trace",
        "--env-start-hours",
        "0",
        "--silent",
    ]

    try:
        strategy_cls = _load_strategy_class(program_path)
        parser = _build_parser(cli_args)
        strategy = strategy_cls._from_args(parser)
        args = strategy.args

        env_start = getattr(args, "env_start_hours", 0.0)
        envs = TraceEnv.create_env(trace_file, env_start_hours=env_start)
        task = _build_task(args)

        output_dir = getattr(args, "output_dir", str(_OUTPUT_BASE))
        os.makedirs(output_dir, exist_ok=True)
        temp_name = f"eval_{os.getpid()}_{uuid.uuid4().hex}.json"

        stats = simulate.simulate(
            envs=envs,
            strategy=strategy,
            task=task,
            trace_file=trace_file,
            deadline_hours=args.deadline_hours,
            restart_overhead_hours=args.restart_overhead_hours,
            env_start_hours=env_start,
            output_dir=output_dir,
            kwargs=vars(args),
            output_filename=temp_name,
            silent=True,
            dump_history=False,
        )

        try:
            os.remove(os.path.join(output_dir, temp_name))
        except OSError:
            pass

        costs = stats.get("costs", [])
        if not costs:
            raise SimulationFailure("Simulation produced no costs")

        avg_cost = float(sum(costs) / len(costs))
        return True, avg_cost, ""

    except SimulationFailure as exc:  # pragma: no cover - surfaced to caller
        return False, 0.0, str(exc)
    except Exception as exc:  # pragma: no cover - unexpected path
        return False, 0.0, f"Error on trace {os.path.basename(trace_file)}: {exc}"
