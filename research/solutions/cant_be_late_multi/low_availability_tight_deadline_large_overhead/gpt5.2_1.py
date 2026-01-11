import json
import math
from argparse import Namespace
from typing import Callable, List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

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

        self._committed_on_demand = False

        self._td_len = 0
        self._td_sum = 0.0

        self._query_initialized = False
        self._spot_query_all: Optional[Callable[[], Optional[List[bool]]]] = None

        self._nregions = None
        self._prev_avail: Optional[List[bool]] = None
        self._total_steps: Optional[List[int]] = None
        self._up_steps: Optional[List[int]] = None
        self._up_up: Optional[List[int]] = None
        self._up_down: Optional[List[int]] = None
        self._up_streak: Optional[List[int]] = None

        self._last_switch_step = -10**18
        self._step_counter = 0

        return self

    @staticmethod
    def _ceil_div_pos(a: float, b: float) -> int:
        if a <= 0.0:
            return 0
        eps = 1e-9
        return int((a + b - eps) // b)

    def _update_work_done(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n != self._td_len:
            # Assume append-only.
            for i in range(self._td_len, n):
                self._td_sum += float(td[i])
            self._td_len = n
        return self._td_sum

    def _ensure_region_stats(self, n: int) -> None:
        if self._nregions == n and self._total_steps is not None:
            return
        self._nregions = n
        self._prev_avail = [False] * n
        self._total_steps = [0] * n
        self._up_steps = [0] * n
        self._up_up = [0] * n
        self._up_down = [0] * n
        self._up_streak = [0] * n

    def _init_spot_query(self) -> None:
        if self._query_initialized:
            return
        self._query_initialized = True

        env = self.env
        try:
            n = int(env.get_num_regions())
        except Exception:
            self._spot_query_all = None
            return

        def is_bool_list(x) -> bool:
            if not isinstance(x, (list, tuple)):
                return False
            if len(x) != n:
                return False
            for v in x:
                if not isinstance(v, (bool, int)):
                    return False
            return True

        attr_list_names = [
            "spot_availabilities",
            "spot_availability",
            "has_spot_by_region",
            "spot_by_region",
            "spot",
            "has_spot_all",
        ]
        for name in attr_list_names:
            if hasattr(env, name):
                try:
                    val = getattr(env, name)
                    if is_bool_list(val):
                        def _q(val=val):
                            v = getattr(env, name)
                            if is_bool_list(v):
                                return [bool(x) for x in v]
                            return None
                        self._spot_query_all = _q
                        return
                except Exception:
                    pass

        list_method_names = [
            "get_spot_availabilities",
            "get_all_spot_availabilities",
            "get_spot_by_region",
            "get_has_spot_by_region",
            "get_spot_availability_by_region",
        ]
        for name in list_method_names:
            fn = getattr(env, name, None)
            if callable(fn):
                try:
                    out = fn()
                    if is_bool_list(out):
                        def _q(fn=fn):
                            try:
                                v = fn()
                                if is_bool_list(v):
                                    return [bool(x) for x in v]
                            except Exception:
                                return None
                            return None
                        self._spot_query_all = _q
                        return
                except Exception:
                    pass

        idx_method_names = [
            "get_has_spot",
            "has_spot",
            "get_spot",
            "spot_available",
            "is_spot_available",
            "get_spot_availability",
        ]
        for name in idx_method_names:
            fn = getattr(env, name, None)
            if callable(fn):
                try:
                    out0 = fn(0)
                    if isinstance(out0, (bool, int)):
                        def _q(fn=fn, n=n):
                            res = [False] * n
                            for i in range(n):
                                try:
                                    res[i] = bool(fn(i))
                                except Exception:
                                    return None
                            return res
                        self._spot_query_all = _q
                        return
                except Exception:
                    pass

        self._spot_query_all = None

    def _update_spot_stats(self, avails: List[bool]) -> None:
        n = self._nregions
        prev = self._prev_avail
        total = self._total_steps
        up = self._up_steps
        up_up = self._up_up
        up_down = self._up_down
        streak = self._up_streak

        for i in range(n):
            a = bool(avails[i])
            total[i] += 1
            if a:
                up[i] += 1
                streak[i] += 1
            else:
                streak[i] = 0

            if prev[i]:
                if a:
                    up_up[i] += 1
                else:
                    up_down[i] += 1
            prev[i] = a

    def _region_score(self, i: int) -> float:
        total = self._total_steps[i]
        up = self._up_steps[i]
        up_up = self._up_up[i]
        up_down = self._up_down[i]
        streak = self._up_streak[i]

        up_rate = (up + 1.0) / (total + 2.0)
        den = up_up + up_down
        p_continue = (up_up + 1.0) / (den + 2.0) if den > 0 else 0.5
        streak_score = min(streak, 50) / 50.0
        return 0.60 * p_continue + 0.30 * up_rate + 0.10 * streak_score

    def _choose_spot_region(self, avails: List[bool], curr: int) -> int:
        if avails[curr]:
            return curr
        best = -1
        best_score = -1e18
        for i, a in enumerate(avails):
            if not a:
                continue
            s = self._region_score(i)
            if s > best_score:
                best_score = s
                best = i
        if best >= 0:
            return best
        return curr

    def _restart_overhead_for_action(
        self,
        last_cluster_type: ClusterType,
        next_cluster_type: ClusterType,
        region_switched: bool,
    ) -> float:
        if next_cluster_type == ClusterType.NONE:
            return 0.0
        if region_switched:
            return float(self.restart_overhead)
        if last_cluster_type == next_cluster_type:
            return float(self.remaining_restart_overhead)
        return float(self.restart_overhead)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._step_counter += 1
        env = self.env

        gap = float(env.gap_seconds)
        if gap <= 0.0:
            return ClusterType.NONE

        elapsed = float(env.elapsed_seconds)
        remaining_time = float(self.deadline) - elapsed
        if remaining_time <= 0.0:
            return ClusterType.NONE

        work_done = self._update_work_done()
        rem_work = float(self.task_duration) - work_done
        if rem_work <= 0.0:
            return ClusterType.NONE

        steps_left = int((remaining_time + 1e-9) // gap)
        if steps_left <= 0:
            return ClusterType.NONE

        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        try:
            nregions = int(env.get_num_regions())
        except Exception:
            nregions = 1
        self._ensure_region_stats(nregions)

        self._init_spot_query()
        avails = None
        if self._spot_query_all is not None and nregions > 1:
            avails = self._spot_query_all()
            if avails is not None and len(avails) == nregions:
                self._update_spot_stats(avails)
            else:
                avails = None

        curr_region = 0
        try:
            curr_region = int(env.get_current_region())
        except Exception:
            curr_region = 0

        # Determine if spot is available anywhere we can reliably see.
        if avails is None:
            has_any_spot = bool(has_spot)
        else:
            has_any_spot = any(avails)

        # Helper: check if idling this step is safe assuming ON_DEMAND thereafter.
        needed_if_start_next = self._ceil_div_pos(rem_work + float(self.restart_overhead), gap)
        can_idle = (steps_left - 1) >= needed_if_start_next

        # If we can see a spot region, try to run spot there (possibly switching).
        if has_any_spot:
            target_region = curr_region
            if avails is not None:
                target_region = self._choose_spot_region(avails, curr_region)
            else:
                if not bool(has_spot):
                    target_region = curr_region  # no visibility, no switching to spot

            region_switched = (target_region != curr_region)
            if region_switched:
                try:
                    env.switch_region(int(target_region))
                except Exception:
                    region_switched = False

            # If we don't have visibility, must respect passed has_spot.
            if avails is None:
                if not bool(has_spot):
                    # Can't safely run spot; decide between NONE and ON_DEMAND.
                    if can_idle:
                        return ClusterType.NONE
                    self._committed_on_demand = True
                    return ClusterType.ON_DEMAND
            else:
                if not avails[target_region]:
                    # Defensive: visibility says no spot; fall back.
                    if can_idle:
                        return ClusterType.NONE
                    self._committed_on_demand = True
                    return ClusterType.ON_DEMAND

            overhead_spot = self._restart_overhead_for_action(last_cluster_type, ClusterType.SPOT, region_switched)
            work_gain = max(0.0, gap - overhead_spot)
            rem_after = rem_work - min(rem_work, work_gain)

            steps_left_after = steps_left - 1
            needed_after_switch_to_od = self._ceil_div_pos(rem_after + float(self.restart_overhead), gap)

            if needed_after_switch_to_od <= steps_left_after:
                return ClusterType.SPOT

            # Spot this step would make worst-case completion impossible; use ON_DEMAND.
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # No spot we can use now.
        if can_idle:
            return ClusterType.NONE

        self._committed_on_demand = True
        return ClusterType.ON_DEMAND