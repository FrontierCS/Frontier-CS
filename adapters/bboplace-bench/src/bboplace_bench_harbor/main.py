from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from .adapter import BBOPlaceAdapter

logging.basicConfig(level=logging.INFO, format="%(message)s")

DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[4] / "datasets" / "bboplace-bench"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Harbor-style tasks from BBOPlace-Bench"
    )
    parser.add_argument(
        "--source",
        default="https://github.com/lamda-bbo/BBOPlace-Bench.git",
        help="BBOPlace-Bench repo path or git URL",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for generated Harbor tasks (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--benchmarks", nargs="+", default=None)
    parser.add_argument(
        "--placers",
        nargs="+",
        default=["mgo"],
        choices=["mgo", "sp", "hpo"],
        help="Problem formulations to generate",
    )
    parser.add_argument("--eval-gp-hpwl", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--base-image",
        default="duketomlist/bboplace-bench:2.1.0",
        help="Docker image used by generated task containers",
    )
    parser.add_argument(
        "--allow-missing-benchmark",
        action="store_true",
        help="Generate tasks even when the selected benchmark data is not present",
    )
    args = parser.parse_args()

    source = args.source
    tmp_dir: str | None = None
    try:
        if source.startswith(("http://", "https://", "git@")):
            tmp_dir = tempfile.mkdtemp(prefix="bboplace-bench-")
            print(f"Cloning {source}...")
            subprocess.run(["git", "clone", "--depth=1", source, tmp_dir], check=True)
            source = tmp_dir

        source_path = Path(source)
        if not (source_path / "src" / "evaluator.py").exists():
            raise FileNotFoundError(f"{source_path}/src/evaluator.py not found")

        print(f"Generating tasks -> {args.output_dir}/")
        adapter = BBOPlaceAdapter(
            source_path,
            args.output_dir,
            benchmarks=args.benchmarks,
            placers=args.placers,
            eval_gp_hpwl=args.eval_gp_hpwl,
            limit=args.limit,
            overwrite=args.overwrite,
            base_image=args.base_image,
            allow_missing_benchmark=args.allow_missing_benchmark,
        )
        results = adapter.run()
        print(f"\nDone: {len(results)} tasks generated")
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
