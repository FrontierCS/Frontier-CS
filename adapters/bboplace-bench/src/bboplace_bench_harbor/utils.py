from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


TASK_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True)
class BBOPlaceProblem:
    benchmark: str
    benchmark_base: str
    benchmark_type: str
    placer: str
    eval_gp_hpwl: bool

    @property
    def task_id(self) -> str:
        suffix = "gp" if self.eval_gp_hpwl else "mp"
        return normalize_task_id(
            f"bboplace-bench-{self.placer}-{self.benchmark}-{suffix}"
        )


def normalize_task_id(value: str) -> str:
    value = TASK_ID_RE.sub("-", value.strip().lower())
    value = value.replace("_", "-")
    value = re.sub(r"-+", "-", value).strip("-")
    if not value:
        raise ValueError("empty task id")
    return value


def load_benchmark_config(root: Path) -> dict:
    config_path = root / "config" / "benchmark.py"
    namespace: dict = {"__file__": str(config_path)}
    exec(config_path.read_text(encoding="utf-8"), namespace)
    return namespace


def load_default_timeout(root: Path) -> int:
    default_path = root / "config" / "default.yaml"
    if not default_path.exists():
        return 3600
    data = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}
    return int(data.get("timeout_seconds", 3600))


def discover_problems(
    root: Path,
    *,
    benchmarks: list[str] | None = None,
    placers: list[str] | None = None,
    eval_gp_hpwl: bool = False,
) -> list[BBOPlaceProblem]:
    cfg = load_benchmark_config(root)
    benchmark_dict = cfg["benchmark_dict"]
    benchmark_type_dict = cfg["benchmark_type_dict"]
    selected_benchmarks = set(benchmarks) if benchmarks else None
    selected_placers = placers or ["mgo"]

    problems: list[BBOPlaceProblem] = []
    for benchmark_base, names in benchmark_dict.items():
        for benchmark in names:
            if selected_benchmarks is not None and benchmark not in selected_benchmarks:
                continue
            for placer in selected_placers:
                problems.append(
                    BBOPlaceProblem(
                        benchmark=benchmark,
                        benchmark_base=benchmark_base,
                        benchmark_type=benchmark_type_dict[benchmark_base],
                        placer=placer.lower(),
                        eval_gp_hpwl=eval_gp_hpwl,
                    )
                )
    return problems
