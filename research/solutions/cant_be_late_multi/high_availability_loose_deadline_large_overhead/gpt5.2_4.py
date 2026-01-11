import json
import math
import os
import csv
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _to_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if math.isnan(v):
            return None
        return v != 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "t", "yes", "y", "on"):
            return True
        if s in ("0", "false", "f", "no", "n", "off", ""):
            return False
        try:
            x = float(s)
            if math.isnan(x):
                return None
            return x != 0
        except Exception:
            return None
    return None


def _extract_bool_series_from_json(obj: Any) -> Optional[List[bool]]:
    if isinstance(obj, list):
        out: List[bool] = []
        for e in obj:
            if isinstance(e, dict):
                for k in ("has_spot", "spot", "availability", "avail", "available"):
                    if k in e:
                        b = _to_bool(e[k])
                        if b is None:
                            continue
                        out.append(b)
                        break
                else:
                    # Try single value dict
                    if len(e) == 1:
                        b = _to_bool(next(iter(e.values())))
                        if b is not None:
                            out.append(b)
            else:
                b = _to_bool(e)
                if b is not None:
                    out.append(b)
        return out if out else None
    if isinstance(obj, dict):
        for k in ("has_spot", "spot", "availability", "avail", "available", "trace", "traces", "data", "values"):
            if k in obj:
                series = _extract_bool_series_from_json(obj[k])
                if series:
                    return series
        # Try dict of index->value
        if obj and all(isinstance(k, (str, int)) for k in obj.keys()):
            try:
                items = sorted(obj.items(), key=lambda kv: int(kv[0]))
                out2: List[bool] = []
                for _, v in items:
                    b = _to_bool(v)
                    if b is not None:
                        out2.append(b)
                return out2 if out2 else None
            except Exception:
                return None
    return None


def _load_trace_file(path: str) -> List[bool]:
    ext = os.path.splitext(path)[1].lower()

    if np is not None and ext in (".npy", ".npz"):
        try:
            if ext == ".npy":
                arr = np.load(path, allow_pickle=False)
            else:
                z = np.load(path, allow_pickle=False)
                if hasattr(z, "files") and z.files:
                    arr = z[z.files[0]]
                else:
                    arr = None
            if arr is None:
                return []
            arr = np.asarray(arr).reshape(-1)
            out = (arr.astype(float) != 0.0).tolist()
            return [bool(x) for x in out]
        except Exception:
            pass

    # Try JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        series = _extract_bool_series_from_json(obj)
        if series is not None:
            return series
    except Exception:
        pass

    # Try lightweight JSON sniff (in case of trailing commas etc. won't parse; fall back)
    try:
        with open(path, "r", encoding="utf-8") as f:
            prefix = f.read(1)
        if prefix in ("[", "{"):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            try:
                obj = json.loads(text)
                series = _extract_bool_series_from_json(obj)
                if series is not None:
                    return series
            except Exception:
                pass
    except Exception:
        pass

    # Try CSV / TSV / plain text
    out: List[bool] = []
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            dialect = None
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t; ")
            except Exception:
                dialect = csv.excel
            reader = csv.reader(f, dialect)
            for row in reader:
                if not row:
                    continue
                # Skip header-like rows
                last = row[-1]
                b = _to_bool(last)
                if b is None and len(row) >= 2:
                    b = _to_bool(row[1])
                if b is None and len(row) >= 1:
                    b = _to_bool(row[0])
                if b is None:
                    continue
                out.append(bool(b))
    except Exception:
        out = []

    if not out:
        # Try line-by-line
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    b = _to_bool(line.strip())
                    if b is None:
                        continue
                    out.append(bool(b))
        except Exception:
            return []

    return out


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v2"

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

        self._trace_files = list(config.get("trace_files", []) or [])
        self._trace_mode = False
        self._trace_reliable = False
        self._trace_mismatch = 0

        self._work_done = 0.0
        self._td_len = 0

        self._avail: List[bytearray] = []
        self._runlen: List[array] = []
        self._any_spot: Optional[bytearray] = None
        self._rem_any: Optional[array] = None
        self._T = 0
        self._R = 0

        try:
            gap = float(getattr(self.env, "gap_seconds"))
            if gap <= 0:
                gap = 1.0
        except Exception:
            gap = 1.0
        self._gap = gap
        self._switch_cost_steps = int(math.ceil(float(self.restart_overhead) / gap)) if gap > 0 else 1

        try:
            self._R = int(self.env.get_num_regions())
        except Exception:
            self._R = len(self._trace_files)

        horizon_steps = int(math.ceil(float(self.deadline) / gap)) + 2
        if horizon_steps < 1:
            horizon_steps = 1

        traces: List[List[bool]] = []
        if self._trace_files:
            for p in self._trace_files[: self._R]:
                series = _load_trace_file(p)
                traces.append(series)

        if len(traces) < self._R:
            for _ in range(self._R - len(traces)):
                traces.append([])

        # Determine T from horizon, keep conservative padding to avoid false True beyond known trace.
        self._T = horizon_steps
        self._avail = [bytearray(self._T) for _ in range(self._R)]

        for r in range(self._R):
            series = traces[r]
            if not series:
                continue
            # Conservative heuristic: if very few True values, invert (likely interruption indicator).
            n = len(series)
            if n > 0:
                true_cnt = sum(1 for x in series if x)
                frac_true = true_cnt / n
                if frac_true < 0.2:
                    series = [not x for x in series]
            m = min(len(series), self._T)
            if m > 0:
                ba = self._avail[r]
                for i in range(m):
                    ba[i] = 1 if series[i] else 0

        # Precompute any_spot and remaining any_spot counts
        any_spot = bytearray(self._T)
        for t in range(self._T):
            v = 0
            for r in range(self._R):
                if self._avail[r][t]:
                    v = 1
                    break
            any_spot[t] = v
        self._any_spot = any_spot

        rem_any = array("I", [0]) * (self._T + 1)
        rem = 0
        for t in range(self._T - 1, -1, -1):
            rem += 1 if any_spot[t] else 0
            rem_any[t] = rem
        self._rem_any = rem_any

        # Precompute run lengths per region
        self._runlen = []
        for r in range(self._R):
            rl = array("I", [0]) * self._T
            cur = 0
            a = self._avail[r]
            for t in range(self._T - 1, -1, -1):
                if a[t]:
                    cur += 1
                else:
                    cur = 0
                rl[t] = cur
            self._runlen.append(rl)

        # Enable trace mode if we have traces for all regions
        self._trace_mode = bool(self._trace_files) and self._R > 0 and self._T > 0
        self._trace_reliable = self._trace_mode  # will be validated online

        return self

    def _update_work_done(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n > self._td_len:
            self._work_done += sum(td[self._td_len : n])
            self._td_len = n
        return self._work_done

    def _should_pause_one_step(self, remaining: float, time_left: float) -> bool:
        if remaining <= 0:
            return False
        if self.remaining_restart_overhead and self.remaining_restart_overhead > 0:
            return False
        gap = self._gap
        # Conservative margins to avoid risking deadline
        margin = max(2.0 * float(self.restart_overhead), 2.0 * gap)
        return (time_left - gap) >= (remaining + margin)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = self._gap
        now = float(getattr(self.env, "elapsed_seconds"))
        time_left = float(self.deadline) - now

        work_done = self._update_work_done()
        remaining = float(self.task_duration) - work_done
        if remaining <= 1e-9:
            return ClusterType.NONE

        # Force safe completion when tight.
        # remaining_restart_overhead reduces effective time for work.
        effective_time_left = time_left - float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        force_margin = max(2.0 * float(self.restart_overhead), 2.0 * gap)
        if effective_time_left <= remaining + force_margin:
            return ClusterType.ON_DEMAND

        t = int(now // gap) if gap > 0 else 0
        if t < 0:
            t = 0
        if t >= self._T:
            t = self._T - 1

        cur_region = 0
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        if cur_region < 0:
            cur_region = 0
        if cur_region >= self._R:
            cur_region = self._R - 1 if self._R > 0 else 0

        # Validate trace reliability using current region observation before any switching.
        if self._trace_reliable and self._R > 0:
            try:
                traced = bool(self._avail[cur_region][t])
                if traced != bool(has_spot):
                    self._trace_mismatch += 1
                    if self._trace_mismatch >= 3:
                        self._trace_reliable = False
                else:
                    if self._trace_mismatch > 0:
                        self._trace_mismatch -= 1
            except Exception:
                self._trace_reliable = False

        # If no reliable trace, avoid region switching and act based on current availability only.
        if not (self._trace_mode and self._trace_reliable and self._R > 0 and self._any_spot is not None and self._rem_any is not None):
            if has_spot:
                return ClusterType.SPOT
            if self._should_pause_one_step(remaining, time_left):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        any_spot_now = bool(self._any_spot[t])
        future_any_spot_steps = int(self._rem_any[t]) if self._rem_any is not None else 0
        future_spot_capacity = float(future_any_spot_steps) * gap

        # If no spot anywhere right now, prefer pausing if we can still finish.
        if not any_spot_now:
            # If even running on spot whenever possible in the future (upper bound) cannot finish, use on-demand.
            if future_spot_capacity + 1e-9 < remaining:
                return ClusterType.ON_DEMAND
            if self._should_pause_one_step(remaining, time_left):
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Spot exists somewhere now. If close to deadline, use on-demand.
        close_margin = max(3.0 * float(self.restart_overhead), 3.0 * gap)
        if effective_time_left <= remaining + close_margin:
            return ClusterType.ON_DEMAND

        # Choose best region with spot (longest expected consecutive availability).
        best_region = cur_region
        best_len = int(self._runlen[cur_region][t]) if self._avail[cur_region][t] else 0

        for r in range(self._R):
            if self._avail[r][t]:
                rl = int(self._runlen[r][t])
                if rl > best_len:
                    best_len = rl
                    best_region = r

        cur_has_spot = bool(self._avail[cur_region][t])
        cur_len = int(self._runlen[cur_region][t]) if cur_has_spot else 0

        # Avoid switching unless necessary or clearly beneficial (amortize overhead).
        if best_region != cur_region:
            if (not cur_has_spot) or (best_len > cur_len + self._switch_cost_steps):
                # Avoid switching while restart overhead pending (would reset it).
                if not (self.remaining_restart_overhead and self.remaining_restart_overhead > 0):
                    try:
                        self.env.switch_region(best_region)
                        cur_region = best_region
                        cur_has_spot = bool(self._avail[cur_region][t])
                    except Exception:
                        cur_region = cur_region
                        cur_has_spot = bool(self._avail[cur_region][t])

        if cur_has_spot:
            return ClusterType.SPOT

        # If switching failed or no spot in current region, fall back safely.
        if self._should_pause_one_step(remaining, time_left) and future_spot_capacity >= remaining:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND