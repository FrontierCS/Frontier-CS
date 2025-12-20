from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_safe_threshold"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self._commit_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already started on-demand, stick with it to avoid extra restarts.
        if self._commit_to_od or last_cluster_type == ClusterType.ON_DEMAND or getattr(self.env, "cluster_type", None) == ClusterType.ON_DEMAND:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Compute remaining work
        completed = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining = max(0.0, self.task_duration - completed)

        # If done, do nothing
        if remaining <= 0:
            return ClusterType.NONE

        t = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        overhead = self.restart_overhead

        # Safety margin to account for discretization and overhead alignment
        margin = 0.25 * gap

        # Latest safe time to start OD (including one restart overhead)
        latest_od_start = deadline - remaining - overhead - margin

        # If we are at/after the latest safe start time for OD, commit to OD
        if t >= latest_od_start:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Prefer spot if available while we're safely before the OD deadline
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide to wait or switch to OD
        # Waiting one step is safe only if after waiting we can still start OD and finish
        if t + gap <= latest_od_start:
            return ClusterType.NONE

        # Not safe to wait any longer; start OD now and stick with it
        self._commit_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
