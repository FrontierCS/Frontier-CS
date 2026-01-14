import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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

        # Internal state for efficiency
        self._cached_done_sum_seconds = 0.0
        self._cached_done_len = 0

        # Region rotation state
        try:
            n = self.env.get_num_regions()
        except Exception:
            n = 1
        self._num_regions = n
        try:
            cur = self.env.get_current_region()
        except Exception:
            cur = 0
        self._rr_next_region = (cur + 1) % max(n, 1)

        return self

    def _update_cached_done_sum(self):
        # Incrementally update the sum of task_done_time to avoid O(n) per step
        lst = self.task_done_time
        ln = len(lst)
        while self._cached_done_len < ln:
            self._cached_done_sum_seconds += lst[self._cached_done_len]
            self._cached_done_len += 1

    def _remaining_work_seconds(self) -> float:
        self._update_cached_done_sum()
        rem = self.task_duration - self._cached_done_sum_seconds
        if rem < 0:
            rem = 0.0
        return rem

    def _rotate_region(self):
        # Round-robin switch while waiting to increase chances of finding available spot
        try:
            n = self.env.get_num_regions()
            self._num_regions = n
        except Exception:
            n = self._num_regions if hasattr(self, "_num_regions") else 1
        if n <= 1:
            return
        cur = self.env.get_current_region()
        idx = getattr(self, "_rr_next_region", (cur + 1) % n)
        if idx == cur:
            idx = (idx + 1) % n
        self.env.switch_region(idx)
        self._rr_next_region = (idx + 1) % n

    def _time_left_seconds(self) -> float:
        return self.deadline - self.env.elapsed_seconds

    def _overhead_if_starting_on_demand_now(self, last_cluster_type: ClusterType) -> float:
        # If already on OD, remaining overhead is whatever is pending; else, a full restart is needed.
        pending = getattr(self, "remaining_restart_overhead", 0.0)
        if last_cluster_type == ClusterType.ON_DEMAND:
            return pending
        return self.restart_overhead

    def _should_switch_od_to_spot(self, time_left: float, remaining_work: float) -> bool:
        # Switch from OD to SPOT only if we have enough slack to handle
        # two overheads (switch now and possibly switch back later) and enough remaining work to justify switching.
        # Conservative thresholds.
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        fudge = 1.0
        # Ensure we can still finish if we must switch back: reserve two overheads.
        if time_left < remaining_work + 2 * overhead + fudge:
            return False
        # Require at least 2 gap-steps of remaining work to make switching worthwhile
        if remaining_work < 2 * gap:
            return False
        return True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update region count in case environment varies
        try:
            self._num_regions = self.env.get_num_regions()
        except Exception:
            pass

        remaining_work = self._remaining_work_seconds()
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self._time_left_seconds()
        if time_left <= 0:
            return ClusterType.NONE

        gap = self.env.gap_seconds
        fudge = 1.0  # small safety margin in seconds

        # Compute minimal time to finish with On-Demand from now
        od_overhead_future = self._overhead_if_starting_on_demand_now(last_cluster_type)
        time_needed_od = remaining_work + od_overhead_future

        # Hard guarantee: if we are at/near the deadline threshold, ensure OD is used
        if time_left <= time_needed_od + fudge:
            return ClusterType.ON_DEMAND

        # Prefer SPOT when available, unless we're already on OD and switching is risky
        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Decide whether to switch from OD to SPOT
                if self._should_switch_od_to_spot(time_left, remaining_work):
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.SPOT

        # No SPOT available
        if last_cluster_type == ClusterType.ON_DEMAND:
            # Already on OD: keep running to avoid extra overheads and ensure progress
            return ClusterType.ON_DEMAND

        # If we can safely wait one more step and still finish with OD, then wait; otherwise fallback to OD
        if time_left > time_needed_od + gap + fudge:
            # Explore other regions while waiting
            self._rotate_region()
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND