import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


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

        # Internal state
        self._od_committed = False
        try:
            self._num_regions = self.env.get_num_regions()
        except Exception:
            self._num_regions = 1
        try:
            self._current_region = self.env.get_current_region()
        except Exception:
            self._current_region = 0

        # Guard time to start on-demand before deadline. Keep small to minimize extra cost.
        gap = getattr(self.env, "gap_seconds", 300.0)
        ro = self.restart_overhead
        # Conservative but not too large
        self._od_guard_seconds = max(2 * ro, ro + 0.5 * gap)

        return self

    def _remaining_work(self) -> float:
        done = 0.0
        if self.task_done_time:
            try:
                done = sum(self.task_done_time)
            except Exception:
                done = 0.0
        return max(0.0, self.task_duration - done)

    def _time_left(self) -> float:
        return max(0.0, self.deadline - self.env.elapsed_seconds)

    def _overhead_if_switch_to_od_now(self) -> float:
        # If already on on-demand, no overhead; otherwise, we pay restart overhead once.
        return 0.0 if self.env.cluster_type == ClusterType.ON_DEMAND else self.restart_overhead

    def _should_run_on_demand_now(self) -> bool:
        if self._od_committed:
            return True
        remain = self._remaining_work()
        if remain <= 0.0:
            return False
        od_required = remain + self._overhead_if_switch_to_od_now()
        return self._time_left() <= od_required + self._od_guard_seconds

    def _rotate_region_when_idle(self):
        # Rotate region only when we plan to idle to hunt for a region with spot availability.
        if self._num_regions <= 1:
            return
        try:
            cur = self.env.get_current_region()
        except Exception:
            cur = self._current_region
        next_idx = (cur + 1) % self._num_regions
        try:
            self.env.switch_region(next_idx)
            self._current_region = next_idx
        except Exception:
            # If switching fails for any reason, ignore.
            pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If finished, do nothing.
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # Decide if we should commit to On-Demand to guarantee finish.
        if self._should_run_on_demand_now():
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Otherwise, prefer spot if available; else wait (NONE) and rotate region to search.
        if has_spot and not self._od_committed:
            return ClusterType.SPOT

        # Idle to wait for spot; rotate region to explore availability.
        self._rotate_region_when_idle()
        return ClusterType.NONE