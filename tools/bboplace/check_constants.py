#!/usr/bin/env python3
"""Check BBOPlace evaluator constants against the data manifest."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools" / "bboplace" / "data_manifest.json"
EVALUATORS = (
    (
        "ispd2005",
        ROOT / "2.0" / "problems" / "bboplace_ispd2005" / "evaluator.py",
        None,
    ),
    (
        "iccad2015",
        ROOT / "2.0" / "problems" / "bboplace_iccad2015" / "evaluator.py",
        None,
    ),
)


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for dataset, evaluator_path, benchmark_override in EVALUATORS:
        module = load_module(evaluator_path)
        expected_scored = benchmark_override or manifest["datasets"][dataset]["benchmarks_scored"]
        all_constants = manifest["scoring_constants"][dataset]["baseline_hpwl"]
        expected_constants = {key: all_constants[key] for key in expected_scored}
        actual_scored = list(module.BENCHMARKS)
        actual_constants = {key: float(value) for key, value in module.BASELINE_HPWL.items()}
        if actual_scored != expected_scored:
            raise SystemExit(
                f"{evaluator_path}: benchmark list mismatch: {actual_scored} != {expected_scored}"
            )
        if actual_constants != expected_constants:
            raise SystemExit(
                f"{evaluator_path}: baseline constants mismatch: {actual_constants} != {expected_constants}"
            )
    print("BBOPlace constants match data_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
