"""Run single simulations without shelling out to the CLI."""

import importlib.util
import json
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Type


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
from sky_spot.task import SingleTask
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


def _first_strategy_class(
    module: ModuleType, module_path: str
) -> Type[strategy_lib.Strategy]:
    # Prefer 'Solution' class if it exists and is a Strategy subclass
    if hasattr(module, "Solution"):
        solution_cls = module.Solution
        if isinstance(solution_cls, type) and issubclass(
            solution_cls, strategy_lib.Strategy
        ):
            return solution_cls

    # Fallback: find any Strategy subclass
    for attr in module.__dict__.values():
        if (
            isinstance(attr, type)
            and issubclass(attr, strategy_lib.Strategy)
            and attr not in {strategy_lib.Strategy, strategy_lib.MultiRegionStrategy}
        ):
            return attr
    raise SimulationFailure(f"No Solution or Strategy subclass found in {module_path}")


def run_single_simulation(program_path: str, trace_file: str, config: dict):
    """Run a single simulation inside the worker process.

    Returns:
        Tuple[bool, float, str]: success flag, cost, error message
    """

    program_path = os.path.abspath(program_path)
    trace_file = os.path.abspath(trace_file)

    try:
        # Load the Solution class
        strategy_cls = _load_strategy_class(program_path)

        # Write config to a temp spec file
        spec_data = {
            "deadline": config["deadline"],
            "duration": config["duration"],
            "overhead": config["overhead"],
            "trace_file": trace_file,
        }
        spec_fd, spec_path = tempfile.mkstemp(suffix=".json", prefix="spec_")
        try:
            with os.fdopen(spec_fd, "w") as f:
                json.dump(spec_data, f)

            # Create instance via solve(spec_path)
            strategy = strategy_cls.__new__(strategy_cls)
            strategy.solve(spec_path)
        finally:
            try:
                os.remove(spec_path)
            except OSError:
                pass

        # Get config values for simulation
        deadline_hours = float(config["deadline"])
        duration_hours = float(config["duration"])
        overhead_hours = float(config["overhead"])

        envs = TraceEnv.create_env(trace_file, env_start_hours=0.0)
        task = SingleTask({"duration": duration_hours, "checkpoint_size_gb": 50.0})

        output_dir = str(_OUTPUT_BASE)
        os.makedirs(output_dir, exist_ok=True)
        temp_name = f"eval_{os.getpid()}_{uuid.uuid4().hex}.json"

        stats = simulate.simulate(
            envs=envs,
            strategy=strategy,
            task=task,
            trace_file=trace_file,
            deadline_hours=deadline_hours,
            restart_overhead_hours=[overhead_hours],
            env_start_hours=0.0,
            output_dir=output_dir,
            kwargs={},
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
