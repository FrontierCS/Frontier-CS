import os
import math
import json
import gzip
import csv
from argparse import Namespace
from typing import Any, List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _coerce_bool(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v > 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "t", "yes", "y", "on"):
            return True
        if s in ("0", "false", "f", "no", "n", "off", "", "none", "null", "nan"):
            return False
        try:
            return float(s) > 0
        except Exception:
            return False
    return False


def _open_maybe_gzip(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "rt", encoding="utf-8", errors="ignore")


def _find_first_list_in_json(obj: Any) -> Optional[List[Any]]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("has_spot", "spot", "availability", "spot_availability", "data", "trace", "values"):
            v = obj.get(k, None)
            if isinstance(v, list):
                return v
        for _, v in obj.items():
            if isinstance(v, list):
                return v
    return None


def _load_trace_bool(path: str, limit: Optional[int] = None) -> List[bool]:
    p = path
    base = p[:-3] if p.endswith(".gz") else p
    ext = os.path.splitext(base)[1].lower()

    if ext == ".npy":
        try:
            import numpy as np  # type: ignore
            arr = np.load(p, allow_pickle=False)
            flat = arr.ravel().tolist()
            if limit is not None:
                flat = flat[:limit]
            return [_coerce_bool(x) for x in flat]
        except Exception:
            pass

    if ext == ".json":
        try:
            if p.endswith(".gz"):
                with gzip.open(p, "rt", encoding="utf-8", errors="ignore") as f:
                    obj = json.load(f)
            else:
                with open(p, "rt", encoding="utf-8", errors="ignore") as f:
                    obj = json.load(f)
            lst = _find_first_list_in_json(obj)
            if lst is None:
                return []
            if limit is not None:
                lst = lst[:limit]
            return [_coerce_bool(x) for x in lst]
        except Exception:
            return []

    if ext == ".csv":
        out: List[bool] = []
        try:
            with _open_maybe_gzip(p) as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    x = row[0]
                    try:
                        v = float(x)
                        out.append(v > 0)
                    except Exception:
                        if _coerce_bool(x):
                            out.append(True)
                        else:
                            out.append(False)
                    if limit is not None and len(out) >= limit:
                        break
            return out
        except Exception:
            return out

    out2: List[bool] = []
    try:
        with _open_maybe_gzip(p) as f:
            for line in f:
                if not line:
                    continue
                s = line.strip()
                if not s:
                    continue
                parts = s.split()
                for tok in parts:
                    try:
                        out2.append(float(tok) > 0)
                    except Exception:
                        out2.append(_coerce_bool(tok))
                    if limit is not None and len(out2) >= limit:
                        return out2
    except Exception:
        return out2
    return out2


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

    _OD_PRICE_PER_HOUR = 3.06
    _SPOT_PRICE_PER_HOUR = 0.9701

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "rt", encoding="utf-8") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._done_sum = 0.0
        self._done_idx = 0

        self._have_traces = False
        self._avail = []
        self._best_region = []
        self._best_len = []
        self._usable_best_region = []
        self._any_spot_remaining = []
        self._horizon_steps = 0
        self._min_window_steps = 1

        try:
            trace_files = list(config.get("trace_files", []))
        except Exception:
            trace_files = []

        try:
            gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        except Exception:
            gap = 0.0
        if gap <= 0:
            gap = 3600.0

        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        if deadline <= 0:
            deadline = float(config.get("deadline", 0.0)) * 3600.0

        steps_needed = int(math.ceil(deadline / gap)) + 5
        if steps_needed < 1:
            steps_needed = 1
        self._horizon_steps = steps_needed

        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if overhead < 0:
            overhead = 0.0

        denom = (self._OD_PRICE_PER_HOUR - self._SPOT_PRICE_PER_HOUR)
        if denom <= 1e-9:
            min_window_seconds = overhead
        else:
            min_window_seconds = 2.0 * overhead * (self._OD_PRICE_PER_HOUR / denom)
        min_window_seconds = max(min_window_seconds, overhead)
        self._min_window_steps = max(1, int(math.ceil(min_window_seconds / gap)))

        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        resolved = []
        for p in trace_files:
            try:
                p2 = str(p)
            except Exception:
                continue
            if not os.path.isabs(p2):
                p2 = os.path.join(spec_dir, p2)
            resolved.append(p2)

        try:
            n_env = int(self.env.get_num_regions())
        except Exception:
            n_env = len(resolved)

        if n_env <= 0:
            n_env = len(resolved)

        if not resolved or n_env <= 0:
            self._safety_seconds = max(60.0, 4.0 * overhead)
            self._safety_seconds = min(self._safety_seconds, 1800.0)
            return self

        resolved = resolved[:n_env]

        avails: List[List[bool]] = []
        for p in resolved:
            trace = _load_trace_bool(p, limit=steps_needed)
            if len(trace) < steps_needed:
                trace = trace + [False] * (steps_needed - len(trace))
            elif len(trace) > steps_needed:
                trace = trace[:steps_needed]
            avails.append(trace)

        if not avails:
            self._safety_seconds = max(60.0, 4.0 * overhead)
            self._safety_seconds = min(self._safety_seconds, 1800.0)
            return self

        R = len(avails)
        H = steps_needed

        run_len = [[0] * (H + 1) for _ in range(R)]
        for r in range(R):
            rl = run_len[r]
            a = avails[r]
            for t in range(H - 1, -1, -1):
                rl[t] = rl[t + 1] + 1 if a[t] else 0

        best_region = [-1] * H
        best_len = [0] * H
        usable_best = [-1] * H

        for t in range(H):
            br = -1
            bl = 0
            ur = -1
            ul = 0
            for r in range(R):
                l = run_len[r][t]
                if l > bl:
                    bl = l
                    br = r
                if l >= self._min_window_steps and l > ul:
                    ul = l
                    ur = r
            best_region[t] = br
            best_len[t] = bl
            usable_best[t] = ur

        any_spot_remaining = [0] * (H + 1)
        for t in range(H - 1, -1, -1):
            any_spot_remaining[t] = any_spot_remaining[t + 1] + (1 if best_len[t] > 0 else 0)

        self._avail = avails
        self._best_region = best_region
        self._best_len = best_len
        self._usable_best_region = usable_best
        self._any_spot_remaining = any_spot_remaining
        self._have_traces = True

        self._safety_seconds = max(60.0, 4.0 * overhead)
        self._safety_seconds = min(self._safety_seconds, 1800.0)

        return self

    def _update_done_sum(self) -> None:
        try:
            tdt = self.task_done_time
        except Exception:
            return
        n = len(tdt)
        i = self._done_idx
        if i < 0:
            i = 0
        if i >= n:
            self._done_idx = n
            return
        s = 0.0
        for j in range(i, n):
            try:
                s += float(tdt[j])
            except Exception:
                pass
        self._done_sum += s
        self._done_idx = n

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_sum()

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            gap = 3600.0

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        time_left = float(getattr(self, "deadline", 0.0) or 0.0) - elapsed
        if time_left <= 0:
            return ClusterType.NONE

        remaining_work = float(getattr(self, "task_duration", 0.0) or 0.0) - float(self._done_sum)
        if remaining_work <= 0:
            return ClusterType.NONE

        rem_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        if rem_overhead < 0:
            rem_overhead = 0.0
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
        if restart_overhead < 0:
            restart_overhead = 0.0

        critical = (time_left <= (remaining_work + rem_overhead + restart_overhead + self._safety_seconds))
        if critical:
            return ClusterType.ON_DEMAND

        idx = int(elapsed / gap + 1e-9)
        if idx < 0:
            idx = 0
        if self._have_traces and self._horizon_steps > 0 and idx >= self._horizon_steps:
            idx = self._horizon_steps - 1

        if last_cluster_type == ClusterType.SPOT and has_spot:
            return ClusterType.SPOT

        if self._have_traces and 0 <= idx < len(self._usable_best_region):
            target = self._usable_best_region[idx]
            if target is not None and target >= 0:
                try:
                    cur = int(self.env.get_current_region())
                except Exception:
                    cur = -1
                if cur != target:
                    try:
                        self.env.switch_region(int(target))
                    except Exception:
                        pass
                if 0 <= target < len(self._avail) and 0 <= idx < len(self._avail[target]) and self._avail[target][idx]:
                    return ClusterType.SPOT

        if self._have_traces and 0 <= idx < len(self._any_spot_remaining):
            spot_cap = float(self._any_spot_remaining[idx]) * gap
            if spot_cap < remaining_work:
                return ClusterType.ON_DEMAND
            return ClusterType.NONE

        return ClusterType.NONE if not critical else ClusterType.ON_DEMAND