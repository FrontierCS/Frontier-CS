import json
import math
import os
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _coerce_bool01(x: Any) -> int:
    if isinstance(x, bool):
        return 1 if x else 0
    if x is None:
        return 0
    if isinstance(x, (int, float)):
        return 1 if x > 0 else 0
    if isinstance(x, str):
        s = x.strip().lower()
        if not s:
            return 0
        if s in ("1", "true", "t", "yes", "y", "on", "spot", "available", "avail"):
            return 1
        if s in ("0", "false", "f", "no", "n", "off", "unavailable", "na", "none"):
            return 0
        try:
            v = float(s)
            return 1 if v > 0 else 0
        except Exception:
            return 0
    return 1 if x else 0


def _extract_list_from_json(obj: Any) -> Optional[List[Any]]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("availability", "avail", "spot", "data", "trace", "values", "series"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
        for v in obj.values():
            if isinstance(v, list):
                return v
    return None


def _load_trace_file(path: str) -> bytearray:
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except Exception:
        return bytearray()

    try:
        if head.startswith(b"\x93NUMPY"):
            try:
                import numpy as np  # type: ignore
            except Exception:
                return bytearray()
            arr = np.load(path, allow_pickle=False)
            arr = np.asarray(arr).reshape(-1)
            out = bytearray(int(v) & 1 if isinstance(v, (int, bool)) else _coerce_bool01(v) for v in arr.tolist())
            return out
    except Exception:
        pass

    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
    except Exception:
        try:
            with open(path, "r", encoding="latin-1") as f:
                txt = f.read()
        except Exception:
            return bytearray()

    s = txt.lstrip()
    if not s:
        return bytearray()

    if s[0] in "[{":
        try:
            obj = json.loads(s)
            lst = _extract_list_from_json(obj)
            if lst is None:
                return bytearray()
            out = bytearray()
            for item in lst:
                if isinstance(item, dict):
                    v = None
                    for k in ("availability", "avail", "spot", "value", "state", "available"):
                        if k in item:
                            v = item[k]
                            break
                    if v is None:
                        out.append(0)
                    else:
                        out.append(_coerce_bool01(v))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    out.append(_coerce_bool01(item[1]))
                else:
                    out.append(_coerce_bool01(item))
            return out
        except Exception:
            pass

    parts = []
    cur = []
    for ch in txt:
        if ch.isdigit() or ch in ".-+eE" or ch.isalpha():
            cur.append(ch)
        else:
            if cur:
                parts.append("".join(cur))
                cur.clear()
    if cur:
        parts.append("".join(cur))

    out = bytearray()
    for p in parts:
        out.append(_coerce_bool01(p))
    return out


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

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

        self._trace_files: List[str] = list(config.get("trace_files", [])) if isinstance(config, dict) else []
        self._avail: List[bytearray] = []
        self._streak: List[array] = []
        self._next_on: List[array] = []
        self._best_region_overall: int = 0
        self._traces_loaded: bool = False

        self._work_done: float = 0.0
        self._last_done_len: int = 0
        self._forced_on_demand: bool = False
        self._pending_switch_to_best: bool = False

        if self._trace_files:
            self._load_and_precompute_traces(self._trace_files)

        return self

    def _load_and_precompute_traces(self, trace_files: Sequence[str]) -> None:
        avail_list: List[bytearray] = []
        for p in trace_files:
            try:
                avail_list.append(_load_trace_file(p))
            except Exception:
                avail_list.append(bytearray())

        if not avail_list:
            return

        m = len(avail_list)
        streak_list: List[array] = [array("I") for _ in range(m)]
        next_on_list: List[array] = [array("I") for _ in range(m)]

        best_idx = 0
        best_sum = -1

        for r, av in enumerate(avail_list):
            n = len(av)
            st = array("I", [0]) * (n + 1)
            no = array("I", [0]) * (n + 1)
            nxt = n
            st[n] = 0
            no[n] = n
            for i in range(n - 1, -1, -1):
                if av[i]:
                    st[i] = st[i + 1] + 1
                    nxt = i
                else:
                    st[i] = 0
                no[i] = nxt
            streak_list[r] = st
            next_on_list[r] = no

            s = int(sum(av))
            if s > best_sum:
                best_sum = s
                best_idx = r

        self._avail = avail_list
        self._streak = streak_list
        self._next_on = next_on_list
        self._best_region_overall = best_idx
        self._traces_loaded = True

    def _update_work_done(self) -> None:
        tdt = self.task_done_time
        n = len(tdt)
        if n > self._last_done_len:
            self._work_done += float(sum(tdt[self._last_done_len : n]))
            self._last_done_len = n

    def _time_index(self) -> int:
        g = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        e = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        if g <= 0:
            return 0
        return int(math.floor(e / g + 1e-12))

    def _pick_region_when_off_spot(self, idx: int, lookahead_steps: int = 1) -> int:
        if not self._traces_loaded:
            return int(self.env.get_current_region())

        num_regions = int(self.env.get_num_regions())
        num_regions = min(num_regions, len(self._avail))
        if num_regions <= 0:
            return int(self.env.get_current_region())

        cur = int(self.env.get_current_region())
        best = cur
        best_wait = 1 << 30
        best_len = -1

        target_idx = idx + max(0, int(lookahead_steps))

        for r in range(num_regions):
            av = self._avail[r]
            n = len(av)
            if n == 0:
                continue
            i = target_idx
            if i < 0:
                i = 0
            if i > n:
                i = n
            j = int(self._next_on[r][i]) if i <= n else n
            if j >= n:
                wait = 1 << 29
                run_len = 0
            else:
                wait = j - target_idx
                run_len = int(self._streak[r][j])

            if wait < best_wait:
                best_wait = wait
                best_len = run_len
                best = r
            elif wait == best_wait:
                if run_len > best_len:
                    best_len = run_len
                    best = r
                elif run_len == best_len and r == self._best_region_overall:
                    best = r

        return int(best)

    def _should_force_on_demand(self, remaining_time: float, remaining_work: float) -> bool:
        margin = 3.0 * float(self.restart_overhead)
        needed = remaining_work + float(self.restart_overhead) + margin
        return remaining_time <= needed

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_work_done()

        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        now = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        remaining_time = float(self.deadline) - now
        if remaining_time <= 0.0:
            return ClusterType.ON_DEMAND

        if (not self._forced_on_demand) and self._should_force_on_demand(remaining_time, remaining_work):
            self._forced_on_demand = True

        if self._forced_on_demand:
            return ClusterType.ON_DEMAND

        idx = self._time_index()
        cur_region = int(self.env.get_current_region())

        # If we have a preferred region, switch to it only when we're not using spot.
        if self._traces_loaded and not self._pending_switch_to_best:
            if cur_region != self._best_region_overall:
                self._pending_switch_to_best = True

        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable in current region: reposition to improve chances next steps.
        if self._traces_loaded:
            target = self._pick_region_when_off_spot(idx, lookahead_steps=1)
            if target != cur_region:
                try:
                    # Avoid switching while already running on-demand to prevent extra restarts.
                    if not (last_cluster_type == ClusterType.ON_DEMAND):
                        self.env.switch_region(int(target))
                        cur_region = int(target)
                except Exception:
                    pass

        # If we had a pending "move to best overall region", try now (only off-spot).
        if self._pending_switch_to_best and self._traces_loaded:
            if cur_region != self._best_region_overall:
                try:
                    if not (last_cluster_type == ClusterType.ON_DEMAND):
                        self.env.switch_region(int(self._best_region_overall))
                        cur_region = int(self._best_region_overall)
                except Exception:
                    pass
            self._pending_switch_to_best = False

        g = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        margin = 3.0 * float(self.restart_overhead)
        # If a restart overhead is already pending, don't pause; keep progressing.
        if float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0) > 0.0:
            return ClusterType.ON_DEMAND

        if (remaining_time - g) >= (remaining_work + float(self.restart_overhead) + margin):
            return ClusterType.NONE

        return ClusterType.ON_DEMAND