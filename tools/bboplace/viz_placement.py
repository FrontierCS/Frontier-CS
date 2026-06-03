#!/usr/bin/env python3
"""Visualize BBOPlace Frontier-CS 2.0 placements as SVG.

Run this inside the BBOPlace judge image, or in an environment where
BBOPLACE_ROOT points at a complete BBOPlace-Bench checkout with benchmarks.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROBLEMS_DIR = ROOT / "2.0" / "problems"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("bboplace_problem_evaluator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import evaluator from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_submission_path(problem_id: str, path: Path | None, payload: Path | None) -> Path:
    if path is not None:
        return path
    if payload is None:
        raise ValueError("pass --solution or --payload-json")

    data = json.loads(payload.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("payload JSON must be an object")
    if data.get("submission_kind", "file") != "file":
        raise ValueError("only file submissions are supported")
    code = data.get("code")
    if not isinstance(code, str):
        raise ValueError("payload JSON must contain a string code field")

    suffix = ".json" if "_direct_" in problem_id else ".py"
    tmp = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=suffix, prefix="bboplace_solution_", delete=False
    )
    with tmp:
        tmp.write(code)
    return Path(tmp.name)


def load_candidates(module: Any, solution_path: Path, benchmark: str):
    evaluator = module._ensure_evaluator(benchmark)
    info = module._benchmark_info(benchmark, evaluator)
    raw = module._run_solution(str(solution_path), info)
    candidates = module._normalize_candidates(
        raw,
        dim=info["dim"],
        node_cnt=info["node_cnt"],
        n_grid_x=info["n_grid_x"],
        n_grid_y=info["n_grid_y"],
    )
    return evaluator, info, candidates


def pick_macro_pos(module: Any, evaluator: Any, candidates: Any, requested_index: int | None):
    import numpy as np

    hpwl_values, overlap_values, macro_pos_all = evaluator.placer.evaluate(candidates)
    hpwl_arr = np.asarray(hpwl_values, dtype=float).reshape(-1)
    overlap_arr = np.asarray(overlap_values, dtype=float).reshape(-1)
    if hpwl_arr.size != candidates.shape[0]:
        raise RuntimeError("BBOPlace returned an unexpected number of HPWL values")
    if not np.all(np.isfinite(hpwl_arr)):
        raise RuntimeError("BBOPlace returned a non-finite HPWL")
    index = int(np.argmin(hpwl_arr)) if requested_index is None else int(requested_index)
    if index < 0 or index >= hpwl_arr.size:
        raise ValueError(f"candidate index {index} is outside [0, {hpwl_arr.size - 1}]")
    if float(hpwl_arr[index]) >= module.INF_HPWL_THRESHOLD:
        raise ValueError("BBOPlace could not legalize the selected candidate")
    if isinstance(macro_pos_all, (list, tuple)):
        macro_pos = macro_pos_all[index]
    else:
        macro_pos = macro_pos_all
    overlap = float(overlap_arr[index]) if overlap_arr.size > index else math.nan
    return float(hpwl_arr[index]), overlap, index, macro_pos


def color_for_rank(rank: int, count: int) -> str:
    if count <= 1:
        t = 0.0
    else:
        t = rank / (count - 1)
    # Blue-to-rose ramp with enough contrast on white.
    r = round(49 + 168 * t)
    g = round(111 - 35 * t)
    b = round(184 - 75 * t)
    return f"rgb({r},{g},{b})"


def write_svg(
    *,
    path: Path,
    title: str,
    subtitle: str,
    placedb: Any,
    macro_pos: dict[str, tuple[float, float]],
    width: int,
) -> None:
    node_info = placedb.node_info
    canvas_width = float(placedb.canvas_width)
    canvas_height = float(placedb.canvas_height)
    margin = 28.0
    title_height = 56.0
    scale = (width - 2 * margin) / max(canvas_width, 1.0)
    drawing_height = canvas_height * scale
    height = int(math.ceil(title_height + drawing_height + 2 * margin))
    area_rank = sorted(
        macro_pos,
        key=lambda name: float(node_info[name]["size_x"]) * float(node_info[name]["size_y"]),
        reverse=True,
    )
    rank_by_name = {name: rank for rank, name in enumerate(area_rank)}

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="{margin}" y="24" font-family="ui-sans-serif, system-ui, sans-serif" '
        f'font-size="18" font-weight="700" fill="#111827">{html.escape(title)}</text>',
        f'<text x="{margin}" y="45" font-family="ui-sans-serif, system-ui, sans-serif" '
        f'font-size="12" fill="#475569">{html.escape(subtitle)}</text>',
        f'<rect x="{margin}" y="{title_height + margin}" '
        f'width="{canvas_width * scale:.3f}" height="{drawing_height:.3f}" '
        'fill="#ffffff" stroke="#0f172a" stroke-width="1"/>',
    ]

    y_origin = title_height + margin
    for name in area_rank:
        x, y = macro_pos[name]
        info = node_info[name]
        size_x = float(info["size_x"])
        size_y = float(info["size_y"])
        sx = margin + float(x) * scale
        sy = y_origin + (canvas_height - float(y) - size_y) * scale
        sw = max(0.5, size_x * scale)
        sh = max(0.5, size_y * scale)
        fill = color_for_rank(rank_by_name[name], len(area_rank))
        tooltip = html.escape(
            f"{name}: x={float(x):.2f}, y={float(y):.2f}, w={size_x:.2f}, h={size_y:.2f}"
        )
        parts.append(
            f'<rect x="{sx:.3f}" y="{sy:.3f}" width="{sw:.3f}" height="{sh:.3f}" '
            f'fill="{fill}" fill-opacity="0.78" stroke="#1e293b" stroke-width="0.45">'
            f"<title>{tooltip}</title></rect>"
        )

    parts.extend(
        [
            f'<text x="{margin}" y="{height - 12}" '
            'font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" '
            'fill="#64748b">Color order follows macro area rank; hover rectangles for macro names.</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem-id", required=True, help="BBOPlace problem id")
    parser.add_argument("--benchmark", help="Benchmark name; defaults to the first task benchmark")
    parser.add_argument("--solution", type=Path, help="Path to solution.py or solution.json")
    parser.add_argument("--payload-json", type=Path, help="Harbor best_submission_payload.json")
    parser.add_argument("--candidate-index", type=int, help="Visualize a specific candidate")
    parser.add_argument("--output", type=Path, required=True, help="Output SVG path")
    parser.add_argument("--width", type=int, default=1200, help="SVG width in pixels")
    args = parser.parse_args(argv)

    problem_dir = PROBLEMS_DIR / args.problem_id
    evaluator_path = problem_dir / "evaluator.py"
    if not evaluator_path.exists():
        raise SystemExit(f"missing evaluator: {evaluator_path}")

    module = load_module(evaluator_path)
    benchmark = args.benchmark or module.BENCHMARKS[0]
    solution_path = read_submission_path(args.problem_id, args.solution, args.payload_json)
    evaluator, info, candidates = load_candidates(module, solution_path, benchmark)
    hpwl, overlap, index, macro_pos = pick_macro_pos(
        module, evaluator, candidates, args.candidate_index
    )
    baseline = float(module.BASELINE_HPWL[benchmark])
    raw_score = 100.0 * (baseline - hpwl) / baseline
    score = max(0.0, raw_score)
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    write_svg(
        path=output,
        title=f"{args.problem_id} / {benchmark}",
        subtitle=(
            f"candidate={index} macros={len(macro_pos)} hpwl={hpwl:.3f} "
            f"baseline={baseline:.3f} score={score:.3f} raw={raw_score:.3f} overlap={overlap:.6g}"
        ),
        placedb=evaluator.placer.placedb,
        macro_pos=macro_pos,
        width=args.width,
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "problem_id": args.problem_id,
                "benchmark": benchmark,
                "candidate_index": index,
                "n_candidates": int(candidates.shape[0]),
                "hpwl": hpwl,
                "baseline_hpwl": baseline,
                "score": score,
                "score_unbounded": raw_score,
                "overlap_rate": overlap,
                "macro_count": len(macro_pos),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
