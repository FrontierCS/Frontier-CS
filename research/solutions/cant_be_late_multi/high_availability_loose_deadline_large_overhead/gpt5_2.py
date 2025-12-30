import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_rr_guard"

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
        self._od_lock = False
        self._acc_done = 0.0
        self._last_done_len = 0
        self._rr_initialized = False
        return self

    def _update_acc_done(self):
        l = len(self.task_done_time)
        if l > self._last_done_len:
            # Incremental sum of new segments only
            add = 0.0
            for i in range(self._last_done_len, l):
                add += self.task_done_time[i]
            self._acc_done += add
            self._last_done_len = l

    def _must_use_on_demand(self, last_cluster_type: ClusterType, time_left: float, remaining_work: float) -> bool:
        # Overhead we need if we choose ON_DEMAND now and keep it
        if self._od_lock or last_cluster_type == ClusterType.ON_DEMAND:
            od_overhead = self.remaining_restart_overhead
        else:
            od_overhead = self.restart_overhead

        # Add small safety to guard discretization/edge cases
        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        safety = min(gap, self.restart_overhead)

        required = od_overhead + remaining_work
        return time_left <= required + safety

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize round-robin region starting point
        if not self._rr_initialized:
            try:
                self._rr_initialized = True
                self._rr_last_region = self.env.get_current_region()
            except Exception:
                self._rr_initialized = True
                self._rr_last_region = 0

        # Update accumulated work done efficiently
        self._update_acc_done()

        # Remaining work and time left
        remaining_work = max(0.0, self.task_duration - self._acc_done)
        time_left = self.deadline - self.env.elapsed_seconds

        if remaining_work <= 0.0:
            # Already finished; no more actions needed
            return ClusterType.NONE

        # If already locked into on-demand, keep it to avoid extra restarts
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # Decide if we must switch to (or stay on) on-demand to guarantee finish
        if self._must_use_on_demand(last_cluster_type, time_left, remaining_work):
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # Not yet forced to use on-demand; prefer spot to minimize cost
        if has_spot:
            return ClusterType.SPOT

        # Spot not available here; we can wait (NONE) as we still have slack.
        # Opportunistically round-robin to another region to increase chance of spot next step.
        try:
            n = self.env.get_num_regions()
            if n and n > 1:
                current = self.env.get_current_region()
                nxt = (current + 1) % n
                if nxt != current:
                    self.env.switch_region(nxt)
                    self._rr_last_region = nxt
        except Exception:
            pass

        return ClusterType.NONE