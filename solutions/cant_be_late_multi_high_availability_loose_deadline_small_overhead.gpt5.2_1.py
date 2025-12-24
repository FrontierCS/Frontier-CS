import json
import os
import math
import csv
import pickle
import gzip
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _open_maybe_gzip(path: str, mode: str = "rt"):
    if path.endswith(".gz"):
        return gzip.open(path, mode)
    return open(path, mode)


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v > 0.5
    s = str(v).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on"):
        return True
    if s in ("0", "false", "f", "no", "n", "off", "", "none", "nan"):
        return False
    try:
        return float(s) > 0.5
    except Exception:
        return False


def _extract_json_sequence(obj: Any) -> Optional[List[bool]]:
    if isinstance(obj, list):
        if not obj:
            return []
        if isinstance(obj[0], dict):
            keys = ("has_spot", "spot", "available", "availability", "avail", "is_spot")
            out = []
            for d in obj:
                if not isinstance(d, dict):
                    out.append(_to_bool(d))
                    continue
                val = None
                for k in keys:
                    if k in d:
                        val = d[k]
                        break
                if val is None:
                    if len(d) == 1:
                        val = next(iter(d.values()))
                    else:
                        val = 0
                out.append(_to_bool(val))
            return out
        return [_to_bool(x) for x in obj]
    if isinstance(obj, dict):
        for k in ("has_spot", "spot", "available", "availability", "avail", "is_spot", "trace", "data", "values"):
            if k in obj:
                seq = obj[k]
                if isinstance(seq, list):
                    return _extract_json_sequence(seq)
        for v in obj.values():
            if isinstance(v, list):
                seq = _extract_json_sequence(v)
                if seq is not None:
                    return seq
    return None


def _read_trace_file(path: str) -> Optional[bytearray]:
    base_path = path[:-3] if path.endswith(".gz") else path
    ext = os.path.splitext(base_path)[1].lower()

    if ext in (".npy", ".npz"):
        try:
            import numpy as np  # type: ignore
        except Exception:
            return None
        try:
            if ext == ".npy":
                arr = np.load(path, allow_pickle=False)
            else:
                z = np.load(path, allow_pickle=False)
                key = None
                for k in z.files:
                    key = k
                    break
                if key is None:
                    return None
                arr = z[key]
            arr = np.asarray(arr).reshape(-1)
            out = bytearray(int(x) > 0 for x in arr.tolist())
            return out
        except Exception:
            return None

    if ext in (".pkl", ".pickle"):
        try:
            with _open_maybe_gzip(path, "rb") as f:
                obj = pickle.load(f)
            if isinstance(obj, (list, tuple)):
                return bytearray(1 if _to_bool(x) else 0 for x in obj)
            if hasattr(obj, "tolist"):
                lst = obj.tolist()
                if isinstance(lst, list):
                    return bytearray(1 if _to_bool(x) else 0 for x in lst)
        except Exception:
            return None
        return None

    if ext in (".json", ".jsn"):
        try:
            with _open_maybe_gzip(path, "rt") as f:
                obj = json.load(f)
            seq = _extract_json_sequence(obj)
            if seq is None:
                return None
            return bytearray(1 if x else 0 for x in seq)
        except Exception:
            return None

    if ext in (".csv", ".tsv"):
        try:
            delim = "," if ext == ".csv" else "\t"
            with _open_maybe_gzip(path, "rt") as f:
                reader = csv.reader(f, delimiter=delim)
                header = next(reader, None)
                if header is None:
                    return bytearray()
                header_l = [h.strip().lower() for h in header]
                col_idx = None
                for name in ("has_spot", "spot", "available", "availability", "avail", "is_spot"):
                    if name in header_l:
                        col_idx = header_l.index(name)
                        break
                if col_idx is None:
                    col_idx = len(header_l) - 1
                out = bytearray()
                for row in reader:
                    if not row:
                        continue
                    if col_idx >= len(row):
                        out.append(0)
                    else:
                        out.append(1 if _to_bool(row[col_idx]) else 0)
                return out
        except Exception:
            return None

    try:
        with _open_maybe_gzip(path, "rt") as f:
            out = bytearray()
            for line in f:
                s = line.strip()
                if not s:
                    continue
                if "," in s:
                    s = s.split(",")[-1].strip()
                out.append(1 if _to_bool(s) else 0)
            return out
    except Exception:
        return None


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        self._trace_files = list(config.get("trace_files", []))
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._force_on_demand = False
        self._done_sum = 0.0
        self._done_len = 0
        self._safety_steps = None  # computed once env.gap_seconds known

        self._offline_ready = False
        self._T = 0
        self._spot = []
        self._streak = []
        self._next_true = []
        self._suffix_any = None

        self._rr_next_region = 0

        try:
            self._init_offline_traces(self._trace_files)
        except Exception:
            self._offline_ready = False

        return self

    def _init_offline_traces(self, trace_files: Sequence[str]) -> None:
        if not trace_files:
            self._offline_ready = False
            return

        spot_by_region: List[bytearray] = []
        min_len = None
        for p in trace_files:
            arr = _read_trace_file(p)
            if arr is None:
                self._offline_ready = False
                return
            spot_by_region.append(arr)
            if min_len is None or len(arr) < min_len:
                min_len = len(arr)

        if min_len is None:
            self._offline_ready = False
            return

        min_len = int(min_len)
        if min_len <= 1:
            self._offline_ready = False
            return

        for i in range(len(spot_by_region)):
            if len(spot_by_region[i]) != min_len:
                spot_by_region[i] = spot_by_region[i][:min_len]

        R = len(spot_by_region)
        T = min_len
        self._T = T
        self._spot = spot_by_region

        self._streak = []
        self._next_true = []

        for r in range(R):
            s = spot_by_region[r]
            streak = array("I", [0]) * T
            nxt = array("I", [0]) * (T + 1)

            next_idx = T + 1
            streak_next = 0
            for t in range(T - 1, -1, -1):
                if s[t]:
                    streak_next += 1
                    streak[t] = streak_next
                    next_idx = t
                else:
                    streak_next = 0
                    streak[t] = 0
                nxt[t] = next_idx
            nxt[T] = T + 1

            self._streak.append(streak)
            self._next_true.append(nxt)

        spot_any = bytearray(T)
        for t in range(T):
            any_on = 0
            for r in range(R):
                if spot_by_region[r][t]:
                    any_on = 1
                    break
            spot_any[t] = any_on

        suffix_any = array("I", [0]) * (T + 1)
        cnt = 0
        for t in range(T - 1, -1, -1):
            cnt += 1 if spot_any[t] else 0
            suffix_any[t] = cnt
        suffix_any[T] = 0
        self._suffix_any = suffix_any

        self._offline_ready = True

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n > self._done_len:
            self._done_sum += sum(td[self._done_len : n])
            self._done_len = n

    def _step_index(self) -> int:
        gap = self.env.gap_seconds
        if gap <= 0:
            return 0
        return int(self.env.elapsed_seconds / gap + 1e-9)

    def _compute_safety_steps(self) -> int:
        gap = self.env.gap_seconds
        if gap <= 0:
            return 2
        return max(2, int(math.ceil(self.restart_overhead / gap - 1e-12)) + 1)

    def _pick_region_for_time(self, t: int, num_regions: int) -> Optional[int]:
        if not self._offline_ready or self._T <= 0 or t < 0 or t >= self._T:
            return None

        R = min(num_regions, len(self._spot))
        best = None
        best_streak = -1
        for r in range(R):
            if self._spot[r][t]:
                st = int(self._streak[r][t])
                if st > best_streak:
                    best_streak = st
                    best = r
        if best is not None:
            return best

        best = 0
        best_nt = self._T + 2
        for r in range(R):
            nt = int(self._next_true[r][t])
            if nt < best_nt:
                best_nt = nt
                best = r
        return best

    def _maybe_switch_for_next_step(self, t_now: int) -> None:
        env = self.env
        n = env.get_num_regions()
        if n <= 1:
            return
        cur = env.get_current_region()
        t_next = t_now + 1

        if self._offline_ready:
            tgt = self._pick_region_for_time(t_next, n)
            if tgt is not None and tgt != cur:
                env.switch_region(tgt)
                return

        self._rr_next_region = (cur + 1) % n
        env.switch_region(self._rr_next_region)

    def _maybe_preemptive_switch_on_spot(self, t_now: int, slack_steps: int) -> None:
        env = self.env
        n = env.get_num_regions()
        if n <= 1 or not self._offline_ready:
            return
        if t_now < 0 or t_now + 1 >= self._T:
            return

        cur = env.get_current_region()
        R = min(n, len(self._spot))
        if cur >= R:
            return

        if self._spot[cur][t_now + 1]:
            return

        if slack_steps > (self._safety_steps or 3):
            return

        best = None
        best_st = -1
        for r in range(R):
            if r == cur:
                continue
            if self._spot[r][t_now] and self._spot[r][t_now + 1]:
                st = int(self._streak[r][t_now + 1])
                if st > best_st:
                    best_st = st
                    best = r

        if best is not None:
            env.switch_region(best)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_sum()

        remaining_work = float(self.task_duration) - float(self._done_sum)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        env = self.env
        gap = float(env.gap_seconds)
        elapsed = float(env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed
        if time_left <= 1e-9:
            return ClusterType.NONE

        if self._safety_steps is None:
            self._safety_steps = self._compute_safety_steps()

        if not self._force_on_demand:
            urgent_margin = 3.0 * float(self.restart_overhead) + 2.0 * gap
            if time_left <= remaining_work + urgent_margin:
                self._force_on_demand = True

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        t_now = self._step_index()

        steps_left = int(math.ceil(time_left / gap - 1e-12)) if gap > 0 else 0
        req_steps = int(math.ceil(remaining_work / gap - 1e-12)) if gap > 0 else 0
        slack_steps = steps_left - req_steps

        if has_spot:
            self._maybe_preemptive_switch_on_spot(t_now, slack_steps)
            return ClusterType.SPOT

        try:
            self._maybe_switch_for_next_step(t_now)
        except Exception:
            pass

        if slack_steps > (self._safety_steps or 3):
            return ClusterType.NONE
        return ClusterType.ON_DEMAND
