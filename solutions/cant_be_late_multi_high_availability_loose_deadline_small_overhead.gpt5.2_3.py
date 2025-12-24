import json
import math
import os
from argparse import Namespace
from array import array
from typing import List, Optional, Sequence

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT", None)
_CT_ON_DEMAND = getattr(ClusterType, "ON_DEMAND", None)
_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))


def _safe_float(x: str) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _parse_bool_token(tok: str) -> Optional[int]:
    t = tok.strip().strip('"').strip("'")
    if not t:
        return None
    tl = t.lower()
    if tl in ("1", "true", "t", "yes", "y", "available", "avail", "up"):
        return 1
    if tl in ("0", "false", "f", "no", "n", "unavailable", "unavail", "down"):
        return 0
    v = _safe_float(t)
    if v is None:
        return None
    return 1 if v > 0.0 else 0


def _read_trace_file(path: str) -> List[int]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in ("trace", "availability", "avail", "data", "values"):
                if k in data and isinstance(data[k], list):
                    data = data[k]
                    break
        if isinstance(data, list):
            out = []
            for x in data:
                if isinstance(x, bool):
                    out.append(1 if x else 0)
                elif isinstance(x, (int, float)):
                    out.append(1 if float(x) > 0.0 else 0)
                elif isinstance(x, str):
                    b = _parse_bool_token(x)
                    if b is not None:
                        out.append(b)
            return out

    out: List[int] = []
    with open(path, "r") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            # split by comma if present, else whitespace
            if "," in s:
                parts = [p.strip() for p in s.split(",") if p.strip()]
            else:
                parts = s.split()
            if not parts:
                continue
            # Try last token first (often availability column), else any token that parses.
            b = _parse_bool_token(parts[-1])
            if b is None and len(parts) >= 2:
                b = _parse_bool_token(parts[0])
                if b is None:
                    # try second token
                    b = _parse_bool_token(parts[1])
            if b is None:
                continue
            out.append(b)
    return out


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._avail: List[bytearray] = []
        self._streak: List[array] = []
        self._N: int = 0
        self._R_parsed: int = 0

        self._gap: Optional[float] = None
        self._deadline_steps: Optional[int] = None
        self._end_step: Optional[int] = None

        self._any_spot: Optional[bytearray] = None
        self._suffix_any: Optional[array] = None

        self._done_work: float = 0.0
        self._done_len: int = 0

        self._precomp_ready: bool = False

        # parameters / heuristics
        self._price_on_demand: float = 3.06
        self._price_spot: float = 0.9701
        self._min_switch_len_ond_to_spot: int = 1
        self._min_switch_len_ond_to_spot_if_needless: int = 1
        self._overhead_steps: int = 0
        self._reserve_seconds: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        trace_files = config.get("trace_files", []) or []
        avail_lists: List[List[int]] = []
        max_len = 0
        for p in trace_files:
            try:
                a = _read_trace_file(p)
            except Exception:
                a = []
            if not a:
                a = []
            avail_lists.append(a)
            if len(a) > max_len:
                max_len = len(a)

        self._R_parsed = len(avail_lists)
        self._N = max_len

        self._avail = []
        if max_len > 0:
            for a in avail_lists:
                ba = bytearray(max_len)
                la = len(a)
                if la:
                    ba[:la] = bytes(1 if x else 0 for x in a)
                self._avail.append(ba)

            # precompute streak length per region (in steps)
            self._streak = []
            for r in range(self._R_parsed):
                st = array("I", [0]) * (max_len + 1)
                ar = self._avail[r]
                for i in range(max_len - 1, -1, -1):
                    if ar[i]:
                        st[i] = st[i + 1] + 1
                    else:
                        st[i] = 0
                self._streak.append(st)
        else:
            self._avail = [bytearray()]
            self._streak = [array("I", [0])]

        self._precomp_ready = False
        self._gap = None
        self._deadline_steps = None
        self._end_step = None
        self._any_spot = None
        self._suffix_any = None
        self._done_work = 0.0
        self._done_len = 0

        return self

    def _init_precomp(self):
        if self._precomp_ready:
            return
        if self.env is None:
            return
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            gap = 1.0
        self._gap = gap

        self._deadline_steps = int(math.ceil(self.deadline / gap - 1e-12))
        end_step = self._deadline_steps
        if self._N > 0:
            end_step = min(end_step, self._N)
        else:
            end_step = 0
        self._end_step = end_step

        # Overhead in steps (used as heuristics)
        self._overhead_steps = max(0, int(math.ceil(self.restart_overhead / gap - 1e-12)))

        diff = self._price_on_demand - self._price_spot
        if diff <= 1e-9:
            base = 1e9
        else:
            base = self._price_on_demand / diff  # ~1.46

        # Need run length L (steps) long enough so switching overhead doesn't dominate.
        # Use strict inequality L > base * overhead/gap, so floor+1.
        v1 = base * (self.restart_overhead / gap) if gap > 0 else 1e9
        self._min_switch_len_ond_to_spot_if_needless = max(1, int(math.floor(v1 + 1e-12)) + 1)
        v2 = 2.0 * v1
        self._min_switch_len_ond_to_spot = max(1, int(math.floor(v2 + 1e-12)) + 1)

        # Also require enough time to overcome the overhead itself.
        self._min_switch_len_ond_to_spot = max(self._min_switch_len_ond_to_spot, self._overhead_steps + 1)
        self._min_switch_len_ond_to_spot_if_needless = max(
            self._min_switch_len_ond_to_spot_if_needless, self._overhead_steps + 1
        )

        # Reserve a bit of slack to account for unavoidable restarts and float issues.
        self._reserve_seconds = max(2.0 * self.restart_overhead, 2.0 * gap)

        # Precompute any-spot (OR over regions) and suffix counts for horizon.
        R_env = int(self.env.get_num_regions())
        R_use = min(R_env, self._R_parsed)
        N = self._N
        end = self._end_step or 0

        if N <= 0 or R_use <= 0 or end <= 0:
            self._any_spot = bytearray(N if N > 0 else 0)
            self._suffix_any = array("I", [0]) * ((N if N > 0 else 0) + 1)
            self._precomp_ready = True
            return

        any_spot = bytearray(N)
        for i in range(end):
            v = 0
            for r in range(R_use):
                v |= self._avail[r][i]
                if v:
                    break
            any_spot[i] = 1 if v else 0
        # beyond end, irrelevant
        self._any_spot = any_spot

        suffix = array("I", [0]) * (N + 1)
        for i in range(N - 1, -1, -1):
            suffix[i] = suffix[i + 1] + (1 if any_spot[i] else 0)
        self._suffix_any = suffix

        self._precomp_ready = True

    def _update_done_work_cache(self):
        td = self.task_done_time
        ln = len(td)
        if ln <= self._done_len:
            return
        s = 0.0
        for x in td[self._done_len :]:
            s += float(x)
        self._done_work += s
        self._done_len = ln

    def _get_step_index(self) -> int:
        if self._gap is None or self._gap <= 0:
            gap = float(self.env.gap_seconds) if self.env is not None else 1.0
        else:
            gap = self._gap
        t = int(self.env.elapsed_seconds / gap + 1e-9)
        if t < 0:
            t = 0
        return t

    def _best_spot_region_and_streak(self, t: int, R_env: int) -> (int, int):
        if self._N <= 0:
            return 0, 0
        end = self._end_step or 0
        if t < 0 or t >= end:
            return 0, 0
        R_use = min(R_env, self._R_parsed)
        best_r = 0
        best_len = 0
        for r in range(R_use):
            if self._avail[r][t]:
                l = int(self._streak[r][t])
                if l > best_len:
                    best_len = l
                    best_r = r
        return best_r, best_len

    def _any_spot_now(self, t: int) -> bool:
        if self._any_spot is None:
            return False
        if t < 0:
            return False
        end = self._end_step or 0
        if t >= end:
            return False
        return bool(self._any_spot[t])

    def _remaining_spot_steps(self, t: int) -> int:
        if self._suffix_any is None:
            return 0
        end = self._end_step or 0
        if t < 0:
            t = 0
        if t >= end:
            return 0
        s = int(self._suffix_any[t])
        e = int(self._suffix_any[end]) if end <= self._N else 0
        return max(0, s - e)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_precomp()
        self._update_done_work_cache()

        gap = self._gap if self._gap is not None else float(self.env.gap_seconds)
        if gap <= 0:
            gap = 1.0

        t = self._get_step_index()
        end = self._end_step or 0

        remaining_work = float(self.task_duration) - float(self._done_work)
        if remaining_work <= 1e-9:
            return _CT_NONE

        remaining_time = float(self.deadline) - float(self.env.elapsed_seconds)
        if remaining_time <= 1e-9:
            return _CT_NONE

        # Slack based on wall-clock; reserve a bit for restarts.
        slack = remaining_time - remaining_work - float(getattr(self, "remaining_restart_overhead", 0.0)) - self._reserve_seconds

        R_env = int(self.env.get_num_regions())
        cur_region = int(self.env.get_current_region())

        any_spot_now = self._any_spot_now(t)
        best_r, best_streak = self._best_spot_region_and_streak(t, R_env)

        # Conservative capacity estimate for spot-only future (upper bound), used only to decide idling.
        rem_spot_steps = self._remaining_spot_steps(t + (1 if not any_spot_now else 0))
        spot_capacity = rem_spot_steps * gap

        overhead_pending = float(getattr(self, "remaining_restart_overhead", 0.0))
        urgent = slack <= 0.0

        # If in the tail, avoid idling.
        if remaining_time <= remaining_work + overhead_pending + self._reserve_seconds:
            urgent = True

        # Helper to switch region only when we will actually run spot.
        def _switch_to(region_idx: int):
            if region_idx != cur_region:
                self.env.switch_region(region_idx)

        # If spot is available somewhere now:
        if any_spot_now and best_streak > 0:
            # If we're already on spot, prefer staying put to avoid extra restarts,
            # unless current region has no spot (forced restart).
            if last_cluster_type == _CT_SPOT:
                cur_has = False
                if 0 <= cur_region < self._R_parsed and self._N > 0 and t < end:
                    cur_has = bool(self._avail[cur_region][t])
                else:
                    cur_has = bool(has_spot)

                if cur_has:
                    return _CT_SPOT

                # Forced: current region spot isn't available; move to best available region.
                _switch_to(best_r)
                return _CT_SPOT

            # If we're on on-demand, only switch to spot for sufficiently long streak.
            if last_cluster_type == _CT_ON_DEMAND:
                min_len = self._min_switch_len_ond_to_spot
                # If we likely can finish without on-demand anyway, allow shorter spot windows.
                if spot_capacity >= remaining_work + self._reserve_seconds:
                    min_len = self._min_switch_len_ond_to_spot_if_needless

                # If urgent, still prefer spot (cheaper) when available, but avoid totally useless windows.
                if urgent:
                    min_len = min(min_len, max(1, self._overhead_steps + 1))

                if best_streak >= min_len:
                    _switch_to(best_r)
                    return _CT_SPOT
                return _CT_ON_DEMAND

            # If we're idle/none (or other), start on spot in best region if it will actually yield work.
            # Avoid starting spot if the window is so short it likely won't get past overhead.
            min_start_len = max(1, self._overhead_steps + 1)
            if urgent or best_streak >= min_start_len:
                _switch_to(best_r)
                return _CT_SPOT
            # Not urgent, short window: skip it to avoid overhead churn.
            return _CT_NONE

        # No spot available anywhere now.
        # If overhead pending, don't idle; keep running on-demand to burn overhead and make progress.
        if overhead_pending > 1e-9:
            return _CT_ON_DEMAND

        # If not urgent and there appears to be enough future spot capacity, idle to save cost.
        if (not urgent) and (spot_capacity >= remaining_work + self._reserve_seconds):
            return _CT_NONE

        # Otherwise, on-demand to ensure deadline.
        return _CT_ON_DEMAND
