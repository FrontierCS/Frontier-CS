import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_safe_wait_spot"

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

        # Internal state for efficiency and policy
        self._done_sum = 0.0
        self._done_len = 0
        self._commit_to_od = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress efficiently to avoid O(n) sum at each step
        if self._done_len != len(self.task_done_time):
            if self._done_len < len(self.task_done_time):
                self._done_sum += sum(self.task_done_time[self._done_len :])
            else:
                # In case environment ever shrinks the list (unlikely), recompute once
                self._done_sum = sum(self.task_done_time)
            self._done_len = len(self.task_done_time)

        remaining_work = max(0.0, self.task_duration - self._done_sum)
        time_left = self.deadline - self.env.elapsed_seconds

        # If we've committed to on-demand, continue until completion to avoid extra overheads
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # Determine if we must switch to On-Demand now to guarantee finishing
        # Conservative rule: ensure we always have time for one restart overhead + remaining work
        must_switch_to_od = time_left <= (remaining_work + self.restart_overhead)

        if must_switch_to_od:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Prefer spot if available; otherwise pause (NONE) while we still have enough slack
        if has_spot:
            return ClusterType.SPOT

        # No spot available and still safe: wait to save cost
        return ClusterType.NONE
