import json
import os
import math
import csv
import pickle
from argparse import Namespace
from array import array
from typing import Any, List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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

        self._trace_files = list(config.get("trace_files", []))
        self._raw_traces: List[List[int]] = []
        for p in self._trace_files:
            try:
                self._raw_traces.append(self._load_trace_file(p))
            except Exception:
                self._raw_traces.append([])

        self._precomputed = False
        self._T = 0
        self._R = 0
        self._avail = []
        self._runlen = []
        self._any_spot = None
        self._suffix_any = None
        self._no_spot_runlen = None
        self._best_region = None

        self._done_work = 0.0
        self._last_td_len = 0
        self._committed_on_demand = False

        self._eps = 1e-6
        self._spot_efficiency = 0.90  # conservatism to offset overheads/switching

        return self

    def _extract_series(self, data: Any) -> List[int]:
        if data is None:
            return []
        if isinstance(data, (bytes, bytearray)):
            return [1 if b else 0 for b in data]
        if isinstance(data, dict):
            for k in ("availability", "avail", "available", "spot", "spots", "trace", "data", "values", "series"):
                if k in data:
                    return self._extract_series(data[k])
            # Dict of timestamp -> value
            try:
                items = list(data.items())
                items.sort(key=lambda kv: float(kv[0]))
                return self._extract_series([kv[1] for kv in items])
            except Exception:
                return []
        if isinstance(data, (list, tuple)):
            if not data:
                return []
            first = data[0]
            if isinstance(first, dict):
                key_candidates = (
                    "available",
                    "availability",
                    "avail",
                    "spot",
                    "has_spot",
                    "is_available",
                    "interrupt",
                    "interrupted",
                )
                key = None
                for kc in key_candidates:
                    if kc in first:
                        key = kc
                        break
                if key is not None:
                    out = []
                    inv = key in ("interrupt", "interrupted")
                    for d in data:
                        v = d.get(key, 0)
                        b = bool(v)
                        out.append(0 if b and inv else (1 if b and not inv else (1 if (not b) and inv else 0)))
                    return out
                # maybe list of {"t":..., "v":...}
                if "v" in first:
                    return [1 if bool(d.get("v", 0)) else 0 for d in data]
                # maybe list of pairs encoded as dicts
                return []
            if isinstance(first, (list, tuple)) and len(first) >= 2:
                return [1 if bool(x[1]) else 0 for x in data]
            out = []
            for x in data:
                if isinstance(x, (int, bool)):
                    out.append(1 if int(x) != 0 else 0)
                elif isinstance(x, float):
                    out.append(1 if x > 0.5 else 0)
                else:
                    try:
                        xi = int(float(x))
                        out.append(1 if xi != 0 else 0)
                    except Exception:
                        out.append(1 if bool(x) else 0)
            return out
        try:
            import numpy as np  # type: ignore

            if isinstance(data, np.ndarray):
                return self._extract_series(data.tolist())
        except Exception:
            pass
        if isinstance(data, (int, bool)):
            return [1 if int(data) != 0 else 0]
        if isinstance(data, float):
            return [1 if data > 0.5 else 0]
        return []

    def _load_trace_file(self, path: str) -> List[int]:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".npy", ".npz"):
            try:
                import numpy as np  # type: ignore

                if ext == ".npy":
                    arr = np.load(path, allow_pickle=True)
                    return self._extract_series(arr)
                else:
                    z = np.load(path, allow_pickle=True)
                    for k in z.files:
                        return self._extract_series(z[k])
                    return []
            except Exception:
                return []
        if ext in (".pkl", ".pickle"):
            with open(path, "rb") as f:
                data = pickle.load(f)
            return self._extract_series(data)
        if ext == ".json":
            with open(path, "r") as f:
                data = json.load(f)
            return self._extract_series(data)
        if ext in (".csv", ".tsv"):
            delim = "," if ext == ".csv" else "\t"
            out: List[int] = []
            with open(path, "r", newline="") as f:
                reader = csv.reader(f, delimiter=delim)
                header = None
                try:
                    header = next(reader)
                except StopIteration:
                    return []
                col_idx = None
                if header:
                    for i, h in enumerate(header):
                        hl = str(h).strip().lower()
                        if hl in ("available", "availability", "avail", "spot", "has_spot", "is_available"):
                            col_idx = i
                            break
                if col_idx is None:
                    # treat header as row if numeric
                    row = header
                    if row:
                        try:
                            v = row[-1]
                            out.append(1 if int(float(v)) != 0 else 0)
                        except Exception:
                            pass
                    col_idx = -1
                for row in reader:
                    if not row:
                        continue
                    try:
                        v = row[col_idx]
                        out.append(1 if int(float(v)) != 0 else 0)
                    except Exception:
                        try:
                            out.append(1 if bool(row[col_idx]) else 0)
                        except Exception:
                            out.append(0)
            return out
        # Fallback: read lines, each a number/bool
        out: List[int] = []
        with open(path, "r") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    out.append(1 if int(float(s)) != 0 else 0)
                except Exception:
                    sl = s.lower()
                    if sl in ("true", "t", "yes", "y", "on"):
                        out.append(1)
                    elif sl in ("false", "f", "no", "n", "off"):
                        out.append(0)
                    else:
                        out.append(0)
        return out

    def _ensure_precomputed(self) -> None:
        if self._precomputed:
            return
        self._precomputed = True

        try:
            g = float(self.env.gap_seconds)
        except Exception:
            g = 1.0
        if g <= 0:
            g = 1.0

        self._R = int(self.env.get_num_regions()) if hasattr(self, "env") else len(self._raw_traces)
        if self._R <= 0:
            self._R = max(1, len(self._raw_traces))

        T = int(math.ceil(float(self.deadline) / g)) + 3
        if T < 8:
            T = 8
        self._T = T

        # Availability per region as bytearray (0/1)
        avail_list: List[bytearray] = []
        for r in range(self._R):
            raw = self._raw_traces[r] if r < len(self._raw_traces) else []
            a = bytearray(T)
            n = min(len(raw), T)
            if n:
                # Clamp values to 0/1
                for i in range(n):
                    a[i] = 1 if raw[i] else 0
            # Default 0 for remainder
            avail_list.append(a)
        self._avail = avail_list

        # Run-length of consecutive availability from t (in steps)
        runlen_list: List[array] = []
        for r in range(self._R):
            rl = array("I", [0]) * (T + 1)
            a = avail_list[r]
            nxt = 0
            for t in range(T - 1, -1, -1):
                if a[t]:
                    nxt += 1
                    rl[t] = nxt
                else:
                    nxt = 0
                    rl[t] = 0
            runlen_list.append(rl)
        self._runlen = runlen_list

        any_spot = bytearray(T)
        best_region = array("b", [-1]) * T

        for t in range(T):
            best = -1
            best_len = 0
            anyv = 0
            for r in range(self._R):
                if avail_list[r][t]:
                    anyv = 1
                    l = runlen_list[r][t]
                    if l > best_len:
                        best_len = l
                        best = r
            any_spot[t] = anyv
            best_region[t] = best

        suffix_any = array("I", [0]) * (T + 1)
        s = 0
        for t in range(T - 1, -1, -1):
            if any_spot[t]:
                s += 1
            suffix_any[t] = s

        no_spot_runlen = array("I", [0]) * (T + 1)
        nxt = 0
        for t in range(T - 1, -1, -1):
            if any_spot[t]:
                nxt = 0
                no_spot_runlen[t] = 0
            else:
                nxt += 1
                no_spot_runlen[t] = nxt

        self._any_spot = any_spot
        self._suffix_any = suffix_any
        self._no_spot_runlen = no_spot_runlen
        self._best_region = best_region

    def _update_done_work(self) -> None:
        td = self.task_done_time
        n = len(td)
        last = self._last_td_len
        if n == last:
            return
        if n == last + 1:
            self._done_work += float(td[-1])
        elif n > last:
            # Rare: multiple appended
            s = 0.0
            for i in range(last, n):
                s += float(td[i])
            self._done_work += s
        self._last_td_len = n

    def _choose_region_for_time(self, t: int) -> Optional[int]:
        # Choose the region with the longest run starting at time t if any spot exists at t.
        if not self._precomputed:
            return None
        if t < 0:
            t = 0
        if t >= self._T:
            t = self._T - 1
        br = int(self._best_region[t])
        return br if br >= 0 else None

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_precomputed()
        self._update_done_work()

        remaining_work = float(self.task_duration) - float(self._done_work)
        if remaining_work <= self._eps:
            return ClusterType.NONE

        g = float(self.env.gap_seconds)
        if g <= 0:
            g = 1.0

        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed

        if time_left <= self._eps:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        t = int(elapsed // g)
        if t < 0:
            t = 0
        if t >= self._T - 1:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        # Hard feasibility: if we need to guarantee completion, commit to on-demand.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_needed = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        else:
            overhead_needed = float(self.restart_overhead)

        if time_left <= remaining_work + overhead_needed + self._eps:
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer spot whenever it's available in current region.
        if has_spot:
            return ClusterType.SPOT

        # Optional region switching to position for upcoming spot, but only if not committed.
        # Keep it conservative: avoid switching while we are already on-demand (to avoid extra overhead),
        # unless we are choosing NONE (not running).
        any_now = 1 if self._any_spot[t] else 0
        any_next = 1 if self._any_spot[t + 1] else 0

        # Decide whether we need on-demand work (vs waiting) based on future spot capacity.
        # Use an efficiency factor to hedge against restart overheads and missed spots.
        suffix_from_next = int(self._suffix_any[t + 1])
        future_spot_cap = float(suffix_from_next) * g * self._spot_efficiency

        need_on_demand = remaining_work > future_spot_cap + self._eps

        # If pausing one more step would make an on-demand-only completion impossible, run on-demand now.
        if (time_left - g) <= (remaining_work + float(self.restart_overhead) + self._eps):
            need_on_demand = True

        if need_on_demand:
            # If global spot is absent for only a very short burst, avoid paying restart overhead just to get no work.
            if not any_now:
                no_spot_block_seconds = float(self._no_spot_runlen[t]) * g
                if no_spot_block_seconds <= float(self.restart_overhead) + self._eps:
                    # Only skip on-demand if we still have comfortable slack.
                    if time_left > remaining_work + 2.0 * float(self.restart_overhead) + g:
                        # If we are going to pause, reposition to catch spot ASAP.
                        if any_next:
                            target = self._choose_region_for_time(t + 1)
                            if target is not None and target != int(self.env.get_current_region()):
                                self.env.switch_region(int(target))
                        return ClusterType.NONE

            # If we are going to run on-demand, still reposition only if it helps next step and we're not already OD.
            if last_cluster_type != ClusterType.ON_DEMAND:
                target_t = self._choose_region_for_time(t) if any_now else None
                if target_t is None and any_next:
                    target_t = self._choose_region_for_time(t + 1)
                if target_t is not None and target_t != int(self.env.get_current_region()):
                    self.env.switch_region(int(target_t))
            return ClusterType.ON_DEMAND

        # Not needing on-demand: pause and try to position for next spot.
        if any_now:
            target = self._choose_region_for_time(t)
        elif any_next:
            target = self._choose_region_for_time(t + 1)
        else:
            target = None

        if target is not None and target != int(self.env.get_current_region()):
            self.env.switch_region(int(target))

        return ClusterType.NONE
