"""Incremental res2sheet: read origin sheet, merge mean/std with new data, write target sheet."""

import csv
import os
import re
import pdb
import shutil
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from utils.constant import INF

from config.benchmark import (
    benchmark_dict,
    benchmark_power_config,
)
from utils.debug import assert0, highlight


# 匹配单元格格式: "mean$\pm$std" 或 "mean$\pm$std (n_seed=N)"
_CELL_PATTERN = re.compile(
    r"^([\d.]+)\$\\pm\$([\d.]+)(?:\s*\(n_seed=(\d+)\))?\s*$",
)


def parse_cell(cell: str) -> Optional[Tuple[float, float, int]]:
    """Parse a sheet cell to (mean, std, n_seed). Returns None if unparseable."""
    if not cell or not cell.strip():
        return None
    m = _CELL_PATTERN.match(cell.strip())
    if not m:
        return None
    mean = float(m.group(1))
    std = float(m.group(2))
    n_seed = int(m.group(3)) if m.group(3) else 5
    return (mean, std, n_seed)


def merge_stats(
    n1: int, mean1: float, std1: float,
    n2: int, mean2: float, std2: float,
) -> Tuple[int, float, float]:
    """Merge two (n, mean, std) groups into one. Returns (n_total, mean_combined, std_combined)."""
    if n1 <= 0:
        return (n2, mean2, std2)
    if n2 <= 0:
        return (n1, mean1, std1)
    n = n1 + n2
    # sum_i = n_i * mean_i, sum_sq_i = n_i * (var_i + mean_i^2)
    sum1 = n1 * mean1
    sum_sq1 = n1 * (std1 ** 2 + mean1 ** 2)
    sum2 = n2 * mean2
    sum_sq2 = n2 * (std2 ** 2 + mean2 ** 2)
    mean_combined = (sum1 + sum2) / n
    var_combined = (sum_sq1 + sum_sq2) / n - mean_combined ** 2
    std_combined = float(np.sqrt(max(0.0, var_combined)))
    return (n, mean_combined, std_combined)


def _format_cell(mean: float, std: float, n_seed: int) -> str:
    """Format mean, std, n_seed to sheet cell string."""
    return f"{mean:.2f}$\\pm${std:.2f} (n_seed={n_seed})"


def res2sheet_incre(
    args, origin_sheet_path: str, target_sheet_path: str, res_path: str
) -> None:
    """Read origin sheet; if existing data for (placer, algo, benchmark), merge mean/std with new run; else write new. Write to target sheet."""
    placer_name = args.placer.lower()
    algo_name = args.algorithm.upper()
    if args.eval_gp_hpwl:
        placer_name += "(GP eval)"
        power_config = benchmark_power_config["gp"]
    else:
        power_config = benchmark_power_config["mp"]

    # 从 res_path 汇总本次运行的 HPWL
    hpwl_lst: list[float] = []
    n_seed = 0
    for seed in os.listdir(res_path):
        seed_file = os.path.join(res_path, seed, "metrics.csv")
        if not os.path.isfile(seed_file):
            continue
        df = pd.read_csv(seed_file)
        n_eval = list(df["n_eval"])
        if len(n_eval) > 0:
            value = list(df["his_best_hpwl"])[len(n_eval) - 1]
            if value != INF:
                hpwl_lst.append(value)
                n_seed += 1
    if len(hpwl_lst) == 0:
        assert0(f"No result found in {res_path}")

    new_mean = float(np.mean(hpwl_lst) / power_config[args.benchmark_base])
    new_std = float(np.std(hpwl_lst) / power_config[args.benchmark_base])


    assert args.benchmark in benchmark_dict[args.benchmark_base]
    benchmark_idx = benchmark_dict[args.benchmark_base].index(args.benchmark)
    n_bench = len(benchmark_dict[args.benchmark_base])
    header = ["placer", "algorithm"] + benchmark_dict[args.benchmark_base]

    # 优先从 target 读取已有表格（保留之前对其它 benchmark 的增量更新）；target 不存在时再用 origin 做初始
    if os.path.exists(target_sheet_path):
        read_path = target_sheet_path
    elif os.path.exists(origin_sheet_path):
        read_path = origin_sheet_path
    else:
        read_path = None
    if read_path is not None:
        with open(read_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
    else:
        rows = []

    # 若无内容，则只保留标准表头
    if not rows:
        rows = [header]

    # 计算本 benchmark 的最终 (mean, std, n_seed)：有原始数据则增量合并，否则用新数据
    row_exist = False
    for row in rows[1:]:
        if len(row) <= 2 + benchmark_idx:
            continue
        if row[0] == placer_name and row[1] == algo_name:
            row_exist = True
            existing_cell = row[2 + benchmark_idx]
            parsed = parse_cell(existing_cell)
            if parsed is not None:
                old_mean, old_std, old_n = parsed
                n_total, mean_final, std_final = merge_stats(
                    old_n, old_mean, old_std, n_seed, new_mean, new_std
                )
                row[2 + benchmark_idx] = _format_cell(mean_final, std_final, n_total)
                highlight("row exist, merged mean/std")
            else:
                row[2 + benchmark_idx] = _format_cell(new_mean, new_std, n_seed)
            break

    if not row_exist:
        # 新行：其他 benchmark 占位用 0.00±0.00 (n_seed=0)，当前列用新数据
        placeholder = _format_cell(0.0, 0.0, 0)
        new_row = [placer_name, algo_name] + [
            placeholder if i != benchmark_idx else _format_cell(new_mean, new_std, n_seed)
            for i in range(n_bench)
        ]
        rows.append(new_row)

    # 写入 target（先写临时文件再 move，保证原子性）
    target_dir = os.path.dirname(target_sheet_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    temp_path = target_sheet_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    shutil.move(temp_path, target_sheet_path)