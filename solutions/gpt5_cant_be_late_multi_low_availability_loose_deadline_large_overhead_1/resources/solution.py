import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_guard"

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
        # Strategy state
        self._committed_to_od = False
        self._initialized = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize commit buffer on first step when env is available
        if not self._initialized:
            # Buffer to ensure we have enough time to switch and complete on OD after one more step, even if a spot preemption occurs.
            self._commit_buffer_seconds = self.env.gap_seconds + self.restart_overhead
            self._initialized = True

        # Calculate remaining work and time
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(self.task_duration - work_done, 0.0)
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0:
            # Out of time; still choose OD to avoid invalid action; environment will handle penalty.
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Overhead if we switch to on-demand now
        overhead_if_od_now = 0.0 if (last_cluster_type == ClusterType.ON_DEMAND or self._committed_to_od) else self.restart_overhead

        # Decision: commit to On-Demand if we are close to deadline
        should_commit = self._committed_to_od or (time_left <= remaining_work + overhead_if_od_now + self._commit_buffer_seconds)
        if should_commit:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Not committed yet; prefer Spot if available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable and not yet time-critical: wait to save cost
        return ClusterType.NONE
