import json
import math
import os
import re
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _safe_json_load(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        return None


_BOOL_TRUE = {"1", "true", "t", "yes", "y", "available", "up", "spot"}
_BOOL_FALSE = {"0", "false", "f", "no", "n", "unavailable", "down", "none"}


def _to_bool(x: Any) -> Optional[bool]:
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        if math.isnan(x):
            return None
        return bool(int(x))
    if isinstance(x, str):
        s = x.strip().lower()
        if s in _BOOL_TRUE:
            return True
        if s in _BOOL_FALSE:
            return False
        if re.fullmatch(r"-?\d+(\.\d+)?", s or ""):
            try:
                return bool(int(float(s)))
            except Exception:
                return None
    return None


def _extract_bool_series_from_json(obj: Any) -> Optional[List[bool]]:
    if isinstance(obj, list):
        if not obj:
            return []
        if all(isinstance(v, (bool, int, float, str)) or v is None for v in obj):
            out: List[bool] = []
            for v in obj:
                b = _to_bool(v)
                if b is None:
                    return None
                out.append(b)
            return out
        if all(isinstance(v, dict) for v in obj):
            keys_priority = ("has_spot", "spot", "available", "availability", "value", "state", "status")
            out2: List[bool] = []
            for d in obj:
                assert isinstance(d, dict)
                found = None
                for k in keys_priority:
                    if k in d:
                        found = _to_bool(d.get(k))
                        break
                if found is None:
                    for _, vv in d.items():
                        found = _to_bool(vv)
                        if found is not None:
                            break
                if found is None:
                    return None
                out2.append(found)
            return out2
        return None
    if isinstance(obj, dict):
        for k in ("trace", "availability", "avail", "spot", "has_spot", "data", "values"):
            if k in obj:
                s = _extract_bool_series_from_json(obj[k])
                if s is not None:
                    return s
        for _, v in obj.items():
            s = _extract_bool_series_from_json(v)
            if s is not None:
                return s
    return None


def _extract_bool_series_from_text(text: str) -> List[bool]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    sep = "," if any("," in ln for ln in lines[:10]) else None
    rows: List[List[str]] = []
    for ln in lines:
        if ln.startswith("#"):
            continue
        if sep == ",":
            parts = [p.strip() for p in ln.split(",")]
        else:
            parts = ln.split()
        if parts:
            rows.append(parts)

    if not rows:
        return []

    header = [c.strip().lower() for c in rows[0]]
    col_idx = None
    for key in ("has_spot", "spot", "available", "availability", "avail", "value", "state", "status"):
        if key in header:
            col_idx = header.index(key)
            break

    start_row = 1 if col_idx is not None else 0
    out: List[bool] = []
    for r in rows[start_row:]:
        if not r:
            continue
        candidates: Sequence[str]
        if col_idx is not None and col_idx < len(r):
            candidates = (r[col_idx],)
        else:
            candidates = reversed(r)
        found = None
        for token in candidates:
            b = _to_bool(token)
            if b is not None:
                found = b
                break
        if found is None:
            m = re.findall(r"(?:^|[^0-9])([01])(?:[^0-9]|$)", " ".join(r))
            if m:
                found = (m[-1] == "1")
        if found is None:
            continue
        out.append(found)
    return out


def _load_trace_file(path: str) -> List[bool]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    obj = _safe_json_load(text)
    if obj is not None:
        series = _extract_bool_series_from_json(obj)
        if series is not None:
            return series
    return _extract_bool_series_from_text(text)


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_region_aware_v1"

    P_ON_DEMAND = 3.06
    P_SPOT = 0.9701

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

        self._trace_files: List[str] = list(config.get("trace_files", []))
        self._raw_traces: List[List[bool]] = []
        for p in self._trace_files:
            try:
                if p and os.path.exists(p):
                    self._raw_traces.append(_load_trace_file(p))
                else:
                    self._raw_traces.append([])
            except Exception:
                self._raw_traces.append([])

        self._prepared = False
        self._T = 0
        self._avail: List[bytearray] = []
        self._streak: List[array] = []
        self._next_idx: List[array] = []

        self._done_sum = 0.0
        self._done_i = 0
        self._committed = False

        self._min_spot_prod_seconds = 0.0
        return self

    def _prepare(self) -> None:
        if self._prepared:
            return
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            gap = 1.0
        self._T = int(math.ceil(float(self.deadline) / gap))
        if self._T <= 0:
            self._T = 1

        num_regions = int(self.env.get_num_regions())
        if num_regions <= 0:
            num_regions = max(1, len(self._raw_traces))

        if len(self._raw_traces) < num_regions:
            self._raw_traces.extend([[]] * (num_regions - len(self._raw_traces)))

        self._avail = []
        self._streak = []
        self._next_idx = []

        for r in range(num_regions):
            tr = self._raw_traces[r]
            a = bytearray(self._T)
            ntr = len(tr)
            if ntr >= self._T:
                for i in range(self._T):
                    a[i] = 1 if tr[i] else 0
            else:
                for i in range(ntr):
                    a[i] = 1 if tr[i] else 0
                for i in range(ntr, self._T):
                    a[i] = 0
            self._avail.append(a)

            streak = array("I", [0]) * self._T
            nexti = array("I", [0]) * self._T

            nxt = self._T
            run = 0
            for i in range(self._T - 1, -1, -1):
                if a[i]:
                    run += 1
                    nxt = i
                else:
                    run = 0
                streak[i] = run
                nexti[i] = nxt
            self._streak.append(streak)
            self._next_idx.append(nexti)

        O = float(self.restart_overhead)
        denom = (self.P_ON_DEMAND - self.P_SPOT)
        if denom > 1e-12:
            self._min_spot_prod_seconds = (self.P_SPOT * O) / denom
        else:
            self._min_spot_prod_seconds = 0.0

        self._prepared = True

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        i = self._done_i
        n = len(td)
        if i >= n:
            return
        s = self._done_sum
        while i < n:
            s += float(td[i])
            i += 1
        self._done_sum = s
        self._done_i = i

    def _choose_region_for_next_step(self, idx_next: int) -> Optional[int]:
        if idx_next >= self._T:
            return None
        best_r = None
        best_len = -1

        for r in range(len(self._avail)):
            if self._avail[r][idx_next]:
                ln = int(self._streak[r][idx_next])
                if ln > best_len:
                    best_len = ln
                    best_r = r

        if best_r is not None:
            return best_r

        best_r2 = None
        best_next = self._T + 1
        best_streak2 = -1
        for r in range(len(self._avail)):
            ni = int(self._next_idx[r][idx_next])
            if ni < best_next:
                best_next = ni
                best_r2 = r
                best_streak2 = int(self._streak[r][ni]) if ni < self._T else -1
            elif ni == best_next and ni < self._T:
                ln = int(self._streak[r][ni])
                if ln > best_streak2:
                    best_streak2 = ln
                    best_r2 = r
        return best_r2

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._prepare()
        self._update_done_sum()

        remaining_work = float(self.task_duration) - float(self._done_sum)
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        if gap <= 0:
            gap = 1.0

        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed
        if time_left <= 1e-9:
            return ClusterType.NONE

        idx = int(elapsed // gap)
        if idx < 0:
            idx = 0
        if idx >= self._T:
            idx = self._T - 1

        current_region = int(self.env.get_current_region())

        if self._committed:
            return ClusterType.ON_DEMAND

        action = ClusterType.NONE

        if has_spot:
            if last_cluster_type == ClusterType.SPOT:
                action = ClusterType.SPOT
            else:
                streak_steps = 0
                if 0 <= current_region < len(self._streak):
                    streak_steps = int(self._streak[current_region][idx])
                streak_seconds = streak_steps * gap
                prod = streak_seconds - float(self.restart_overhead)
                if prod > max(0.0, self._min_spot_prod_seconds):
                    action = ClusterType.SPOT
                else:
                    action = ClusterType.NONE
        else:
            action = ClusterType.NONE

        if action != ClusterType.SPOT:
            idx_next = idx + 1
            desired = self._choose_region_for_next_step(idx_next)
            if desired is not None and desired != current_region:
                try:
                    self.env.switch_region(int(desired))
                except Exception:
                    pass

        if action != ClusterType.ON_DEMAND:
            if action == ClusterType.SPOT:
                if last_cluster_type == ClusterType.SPOT:
                    overhead_now = float(self.remaining_restart_overhead)
                else:
                    overhead_now = float(self.restart_overhead)
                work_this_step = max(0.0, gap - overhead_now)
            else:
                work_this_step = 0.0

            remaining_after = remaining_work - work_this_step
            max_work_if_start_od_next = max(0.0, time_left - gap - float(self.restart_overhead))
            if remaining_after > max_work_if_start_od_next + 1e-9:
                self._committed = True
                return ClusterType.ON_DEMAND

        return action