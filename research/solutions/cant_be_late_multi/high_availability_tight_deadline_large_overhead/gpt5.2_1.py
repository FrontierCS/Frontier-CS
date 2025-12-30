import os
import json
import math
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None


def _to_bool01(x: Any) -> int:
    if isinstance(x, bool):
        return 1 if x else 0
    if x is None:
        return 0
    if isinstance(x, (int, float)):
        return 1 if x > 0 else 0
    s = str(x).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on", "available", "avail"):
        return 1
    if s in ("0", "false", "f", "no", "n", "off", "unavailable", "unavail"):
        return 0
    try:
        v = float(s)
        return 1 if v > 0 else 0
    except Exception:
        return 0


def _extract_availability_from_json(data: Any) -> Optional[List[int]]:
    if isinstance(data, list):
        if not data:
            return []
        if all(isinstance(x, (bool, int, float, str, type(None))) for x in data):
            return [_to_bool01(x) for x in data]
        if all(isinstance(x, dict) for x in data):
            keys = ("has_spot", "available", "availability", "spot", "interrupt", "interrupted")
            for k in keys:
                if k in data[0]:
                    vals = [_to_bool01(d.get(k)) for d in data]
                    if k in ("interrupt", "interrupted"):
                        vals = [0 if v else 1 for v in vals]
                    return vals
            # Fallback: take last value of each dict if scalar-like
            vals: List[int] = []
            for d in data:
                if not d:
                    vals.append(0)
                    continue
                v = next(reversed(d.values()))
                vals.append(_to_bool01(v))
            return vals
        return None
    if isinstance(data, dict):
        for k in ("availability", "has_spot", "spot", "available"):
            if k in data and isinstance(data[k], list):
                return [_to_bool01(x) for x in data[k]]
        for k in ("interrupt", "interrupted"):
            if k in data and isinstance(data[k], list):
                raw = [_to_bool01(x) for x in data[k]]
                return [0 if v else 1 for v in raw]
        for k in ("data", "trace", "values", "series"):
            if k in data and isinstance(data[k], list):
                return _extract_availability_from_json(data[k])
        return None
    return None


def _load_trace_file(path: str, max_len: int = 200000) -> Optional[bytearray]:
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".npy" and np is not None:
            arr = np.load(path, allow_pickle=True)
            flat = arr.reshape(-1)
            n = min(int(flat.shape[0]), max_len)
            out = bytearray(n)
            for i in range(n):
                out[i] = _to_bool01(flat[i])
            return out
    except Exception:
        pass

    # Try JSON (even if extension not .json)
    try:
        with open(path, "r", encoding="utf-8") as f:
            first = f.read(1)
            while first and first.isspace():
                first = f.read(1)
            if first in ("[", "{"):
                f.seek(0)
                data = json.load(f)
                vals = _extract_availability_from_json(data)
                if vals is None:
                    return None
                if len(vals) > max_len:
                    vals = vals[:max_len]
                return bytearray(vals)
    except Exception:
        pass

    # Text/CSV
    try:
        out = bytearray()
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if len(out) >= max_len:
                    break
                s = line.strip()
                if not s:
                    continue
                # Skip headers
                if any(c.isalpha() for c in s) and not all(ch in "01" for ch in s.replace(",", "").replace(" ", "")):
                    continue
                # Tokenize
                if "," in s:
                    tok = s.split(",")[-1].strip()
                else:
                    parts = s.split()
                    tok = parts[-1].strip() if parts else s
                out.append(_to_bool01(tok))
        return out
    except Exception:
        return None


def _compute_run_lengths(avail: bytearray) -> array:
    n = len(avail)
    run = array("I", [0]) * n
    c = 0
    for i in range(n - 1, -1, -1):
        if avail[i]:
            c += 1
            run[i] = c
        else:
            c = 0
            run[i] = 0
    return run


class Solution(MultiRegionStrategy):
    NAME = "oracle_greedy_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._forced_on_demand = False
        self._work_done = 0.0
        self._task_done_len = 0

        self._trace_enabled = False
        self._trace_invert = 0  # 0 unknown, 1 no invert, -1 invert, 2 disabled
        self._traces: List[bytearray] = []
        self._runs: List[array] = []

        trace_files = config.get("trace_files") or []
        if isinstance(trace_files, list) and trace_files:
            loaded: List[bytearray] = []
            for p in trace_files:
                if not isinstance(p, str):
                    loaded = []
                    break
                a = _load_trace_file(p, max_len=200000)
                if a is None:
                    loaded = []
                    break
                loaded.append(a)
            if loaded:
                self._traces = loaded
                self._runs = [_compute_run_lengths(a) for a in loaded]
                self._trace_enabled = True

        return self

    def _sync_work_done(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n <= self._task_done_len:
            return
        s = 0.0
        for i in range(self._task_done_len, n):
            s += float(td[i])
        self._work_done += s
        self._task_done_len = n

    def _trace_has_spot(self, region: int, idx: int) -> Optional[bool]:
        if not self._trace_enabled:
            return None
        if region < 0 or region >= len(self._traces):
            return None
        a = self._traces[region]
        if idx < 0 or idx >= len(a):
            return None
        v = 1 if a[idx] else 0
        if self._trace_invert == -1:
            v ^= 1
        return bool(v)

    def _trace_run_steps(self, region: int, idx: int) -> int:
        if not self._trace_enabled:
            return 0
        if region < 0 or region >= len(self._runs):
            return 0
        r = self._runs[region]
        if idx < 0 or idx >= len(r):
            return 0
        return int(r[idx])

    def _calibrate_trace(self, cur_region: int, idx: int, has_spot: bool) -> None:
        if not self._trace_enabled or self._trace_invert in (1, -1, 2):
            return
        v = self._trace_has_spot(cur_region, idx)
        if v is None:
            self._trace_invert = 2
            self._trace_enabled = False
            return
        if v == has_spot:
            self._trace_invert = 1
            return
        # Try inverted
        self._trace_invert = -1
        v2 = self._trace_has_spot(cur_region, idx)
        if v2 is not None and v2 == has_spot:
            return
        self._trace_invert = 2
        self._trace_enabled = False

    def _would_restart(self, last_cluster_type: ClusterType, target_cluster_type: ClusterType, cur_region: int, target_region: int) -> bool:
        if target_cluster_type != last_cluster_type:
            return True
        if target_region != cur_region:
            return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._sync_work_done()

        env = self.env
        gap = float(getattr(env, "gap_seconds", 1.0))
        elapsed = float(getattr(env, "elapsed_seconds", 0.0))
        time_left = float(self.deadline) - elapsed

        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        cur_region = int(env.get_current_region())
        num_regions = int(env.get_num_regions())

        idx = int((elapsed + 1e-9) // gap)

        if self._trace_enabled and self._trace_invert == 0:
            self._calibrate_trace(cur_region, idx, bool(has_spot))

        if self._trace_enabled and self._trace_invert in (1, -1):
            v = self._trace_has_spot(cur_region, idx)
            if v is not None and v != bool(has_spot):
                self._trace_enabled = False
                self._trace_invert = 2

        if self._forced_on_demand:
            return ClusterType.ON_DEMAND

        # If we can provably finish on spot without interruption (oracle), do it.
        if self._trace_enabled and self._trace_invert in (1, -1):
            best_finish_region = -1
            best_finish_no_restart = False
            best_finish_run = -1
            for r in range(min(num_regions, len(self._traces))):
                run_steps = self._trace_run_steps(r, idx)
                if run_steps <= 0:
                    continue
                # Must have spot now to start a consecutive run
                if not self._trace_has_spot(r, idx):
                    continue
                restart = self._would_restart(last_cluster_type, ClusterType.SPOT, cur_region, r)
                required = remaining_work + (self.restart_overhead if restart else float(getattr(self, "remaining_restart_overhead", 0.0)))
                if required <= time_left + 1e-6 and (run_steps * gap) >= required - 1e-6:
                    # Prefer no restart, then longer run
                    if best_finish_region == -1:
                        best_finish_region = r
                        best_finish_no_restart = not restart
                        best_finish_run = run_steps
                    else:
                        if (not restart) and (not best_finish_no_restart):
                            best_finish_region = r
                            best_finish_no_restart = True
                            best_finish_run = run_steps
                        elif (best_finish_no_restart == (not restart)) and run_steps > best_finish_run:
                            best_finish_region = r
                            best_finish_run = run_steps
            if best_finish_region != -1:
                if best_finish_region != cur_region:
                    env.switch_region(best_finish_region)
                return ClusterType.SPOT

        # Decide if we must commit to on-demand to guarantee completion.
        need_restart_od = (last_cluster_type != ClusterType.ON_DEMAND)
        min_time_od = remaining_work + (self.restart_overhead if need_restart_od else float(getattr(self, "remaining_restart_overhead", 0.0)))
        safety = max(1e-3, 0.05 * gap)
        if min_time_od >= time_left - safety:
            self._forced_on_demand = True
            return ClusterType.ON_DEMAND

        # Use spot whenever possible; if none, idle (free) until forced to on-demand.
        if self._trace_enabled and self._trace_invert in (1, -1):
            # Prefer staying if current region has spot
            if self._trace_has_spot(cur_region, idx):
                return ClusterType.SPOT
            # Switch to best region with spot now (max consecutive run)
            best_r = -1
            best_run = -1
            for r in range(min(num_regions, len(self._traces))):
                if not self._trace_has_spot(r, idx):
                    continue
                run_steps = self._trace_run_steps(r, idx)
                if run_steps > best_run:
                    best_run = run_steps
                    best_r = r
            if best_r != -1:
                if best_r != cur_region:
                    env.switch_region(best_r)
                return ClusterType.SPOT
            return ClusterType.NONE

        # Fallback without traces: only use spot if told it's available in current region.
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE