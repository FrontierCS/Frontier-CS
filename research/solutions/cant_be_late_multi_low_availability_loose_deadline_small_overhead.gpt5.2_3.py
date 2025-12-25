import json
import math
import inspect
from argparse import Namespace
from typing import Callable, Optional, List, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = ClusterType.SPOT
_CT_OD = ClusterType.ON_DEMAND
_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))
if _CT_NONE is None:
    _CT_NONE = ClusterType(0) if isinstance(ClusterType, type) else None


def _scalar(x: Any) -> float:
    if isinstance(x, (list, tuple)):
        return float(x[0]) if x else 0.0
    return float(x)


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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
        return self

    # --------------------- internal helpers ---------------------
    def _lazy_init(self) -> None:
        if getattr(self, "_inited", False):
            return
        self._inited = True

        self._gap = float(getattr(self.env, "gap_seconds", 3600.0))
        self._deadline = _scalar(getattr(self, "deadline", 0.0))
        self._task_duration = _scalar(getattr(self, "task_duration", 0.0))
        self._restart_overhead = _scalar(getattr(self, "restart_overhead", 0.0))

        self._num_regions = int(self.env.get_num_regions())

        self._done_len = 0
        self._done_sum = 0.0

        self._committed_od = False

        self._union_total = 0
        self._union_avail = 0

        self._reg_total = [0] * self._num_regions
        self._reg_avail = [0] * self._num_regions

        self._no_spot_streak = 0
        self._spot_seen_streak = 0

        self._od_hold = 0

        ratio = self._restart_overhead / self._gap if self._gap > 0 else 0.0
        self._min_dwell_steps = max(1, int(math.ceil(ratio)) + 1)
        self._confirm_steps = max(1, self._min_dwell_steps)

        self._spot_query_region: Optional[Callable[[int], bool]] = None
        self._spot_query_current: Optional[Callable[[], bool]] = None
        self._detect_spot_query()

    def _detect_spot_query(self) -> None:
        env = self.env
        candidates = [
            "get_has_spot",
            "has_spot",
            "is_spot_available",
            "get_spot_available",
            "spot_available",
            "get_spot",
            "peek_has_spot",
            "peek_spot",
        ]

        def _sig_npos(fn: Callable) -> Optional[int]:
            try:
                sig = inspect.signature(fn)
                npos = 0
                for p in sig.parameters.values():
                    if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
                        npos += 1
                return npos
            except Exception:
                return None

        for name in candidates:
            if not hasattr(env, name):
                continue
            attr = getattr(env, name)
            if callable(attr):
                npos = _sig_npos(attr)
                if npos == 1:
                    self._spot_query_region = attr
                    self._spot_query_current = None
                    return
                if npos == 0 and self._spot_query_current is None:
                    self._spot_query_current = attr

        # Fallback: if we found only current-region getter, keep it.
        # Otherwise, rely on has_spot passed to _step.
        return

    def _update_done_sum(self) -> None:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return
        cur_len = len(tdt)
        if cur_len <= self._done_len:
            return
        self._done_sum += float(sum(tdt[self._done_len:cur_len]))
        self._done_len = cur_len

    def _region_score(self, i: int) -> float:
        tot = self._reg_total[i]
        av = self._reg_avail[i]
        return (av + 1.0) / (tot + 2.0)

    def _select_best_region(self, avail_regions: List[int], current_region: int) -> int:
        if not avail_regions:
            return current_region
        if current_region in avail_regions:
            return current_region
        best = avail_regions[0]
        best_score = self._region_score(best)
        for r in avail_regions[1:]:
            sc = self._region_score(r)
            if sc > best_score:
                best = r
                best_score = sc
        return best

    def _estimate_union_q(self) -> float:
        return (self._union_avail + 1.0) / (self._union_total + 2.0)

    def _estimate_region_q(self, region: int) -> float:
        tot = self._reg_total[region]
        av = self._reg_avail[region]
        return (av + 1.0) / (tot + 2.0)

    def _od_steps_needed_from_now(self, last_cluster_type: ClusterType, remaining_work: float) -> int:
        if remaining_work <= 0:
            return 0
        pending = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        if last_cluster_type == _CT_OD:
            first_over = pending
        else:
            first_over = self._restart_overhead
        if self._gap <= 0:
            return 10**9
        return int(math.ceil((remaining_work + first_over) / self._gap))

    # --------------------- required API ---------------------
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_sum()

        remaining_work = self._task_duration - self._done_sum
        if remaining_work <= 1e-9:
            return _CT_NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = self._deadline - elapsed
        if time_left <= 0:
            return _CT_OD

        current_region = int(self.env.get_current_region())
        n = self._num_regions

        avail_regions: List[int] = []
        any_spot = False
        curr_has_spot = bool(has_spot)

        if self._spot_query_region is not None:
            # Best-effort: query all regions. If any call fails, fall back to provided has_spot for current region.
            region_has = [False] * n
            for i in range(n):
                v = None
                try:
                    v = self._spot_query_region(i)
                except Exception:
                    v = None
                if v is None:
                    v = bool(has_spot) if i == current_region else False
                v = bool(v)
                region_has[i] = v
                if v:
                    avail_regions.append(i)
                    any_spot = True
                self._reg_total[i] += 1
                if v:
                    self._reg_avail[i] += 1
            curr_has_spot = region_has[current_region]
        else:
            # Only know about current region.
            self._reg_total[current_region] += 1
            if curr_has_spot:
                self._reg_avail[current_region] += 1
                any_spot = True
                avail_regions = [current_region]

        self._union_total += 1
        if any_spot:
            self._union_avail += 1

        if any_spot:
            self._no_spot_streak = 0
            self._spot_seen_streak += 1
        else:
            self._no_spot_streak += 1
            self._spot_seen_streak = 0

        # If we're in the middle of paying restart overhead, avoid switching if possible.
        pending_over = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        if pending_over > 1e-9:
            if last_cluster_type == _CT_OD:
                return _CT_OD
            if last_cluster_type == _CT_SPOT and curr_has_spot:
                return _CT_SPOT

        # Decrement OD hold if we were on OD.
        if last_cluster_type == _CT_OD and self._od_hold > 0:
            self._od_hold -= 1

        # Hard commit to OD when close to deadline.
        od_steps = self._od_steps_needed_from_now(last_cluster_type, remaining_work)
        od_time = od_steps * self._gap
        safety = max(2.0 * self._gap, 4.0 * self._restart_overhead, 60.0)

        if self._committed_od or (time_left <= od_time + safety):
            self._committed_od = True
            return _CT_OD

        # Planning estimate: if we can chase any-spot across regions, use union availability; else use current region.
        if self._spot_query_region is not None:
            q_est = self._estimate_union_q()
        else:
            q_est = self._estimate_region_q(current_region)

        q_plan = max(0.01, min(0.99, q_est - 0.05))
        deficit = remaining_work - q_plan * time_left

        # If any spot is available now, prefer spot unless we are holding OD to amortize overhead or we need to burn deficit.
        if any_spot:
            if last_cluster_type == _CT_OD:
                if self._od_hold > 0 or deficit > self._gap:
                    self._od_hold = max(self._od_hold, 1)
                    return _CT_OD
                if self._spot_seen_streak < self._confirm_steps:
                    return _CT_OD

            # Choose region (avoid switching if already in a spot-available region).
            chosen = self._select_best_region(avail_regions, current_region)
            if chosen != current_region:
                try:
                    self.env.switch_region(chosen)
                    current_region = chosen
                except Exception:
                    pass

            # If we don't have multi-region spot query, only return SPOT if caller says has_spot.
            if self._spot_query_region is None and not bool(has_spot):
                return _CT_OD if deficit > 0 else _CT_NONE

            return _CT_SPOT

        # No spot available (known).
        # Use OD as needed to cover deficit and avoid running out of slack; otherwise wait for spot (free).
        if deficit > self._gap or (self._no_spot_streak * self._gap > safety and deficit > 0):
            self._od_hold = max(self._od_hold, self._min_dwell_steps)
            return _CT_OD

        return _CT_NONE
