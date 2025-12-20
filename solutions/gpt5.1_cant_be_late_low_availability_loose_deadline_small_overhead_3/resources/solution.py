from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def solve(self, spec_path: str) -> "Solution":
        self._forced_od = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "_forced_od"):
            self._forced_od = False

        work_done = 0.0
        if hasattr(self, "task_done_time") and self.task_done_time:
            work_done = float(sum(self.task_done_time))

        task_dur = float(getattr(self, "task_duration", 0.0))
        remaining = max(task_dur - work_done, 0.0)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        deadline = float(getattr(self, "deadline", 0.0))
        time_left = deadline - elapsed

        if remaining <= 0.0 or time_left <= 0.0:
            return ClusterType.NONE

        if self._forced_od:
            return ClusterType.ON_DEMAND

        gap = float(getattr(self.env, "gap_seconds", 1.0))
        restart_overhead = float(getattr(self, "restart_overhead", 0.0))
        margin = max(gap, restart_overhead)

        overhead_future = restart_overhead
        safe_slack = time_left - (remaining + overhead_future)

        if safe_slack <= margin:
            self._forced_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
