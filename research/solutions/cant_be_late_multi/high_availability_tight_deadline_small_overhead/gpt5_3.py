import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "hedged_spot_deadline_v3"

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

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize internal state lazily
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._commit_ondemand = False
            # Cache progress sum efficiently
            self._acc_work_seconds = 0.0
            self._td_len = 0

        # Efficiently update cached sum of task_done_time
        td_len_now = len(self.task_done_time)
        while self._td_len < td_len_now:
            self._acc_work_seconds += self.task_done_time[self._td_len]
            self._td_len += 1

        # Compute remaining work and time
        work_remaining = max(0.0, self.task_duration - self._acc_work_seconds)
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)
        dt = float(self.env.gap_seconds)
        ro = float(self.restart_overhead)

        # Safety threshold: ensure even if we lose up to one full step (preemption at start),
        # we can still finish on On-Demand.
        threshold = work_remaining + ro + dt

        # If already committed to On-Demand, stick with it to avoid extra overheads.
        if self._commit_ondemand:
            return ClusterType.ON_DEMAND

        # If we're at/inside the safety window, switch to On-Demand now.
        if time_left <= threshold + 1e-9:
            self._commit_ondemand = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available outside the safety window.
        if has_spot:
            return ClusterType.SPOT

        # No Spot available and we have slack: wait to save cost.
        return ClusterType.NONE