from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbf_safe_spot_ondemand_v1"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env

        gap = env.gap_seconds
        work_done = len(self.task_done_time) * gap
        remaining_work = max(self.task_duration - work_done, 0.0)

        if remaining_work <= 0.0:
            return ClusterType.NONE

        elapsed = env.elapsed_seconds
        available_time = self.deadline - elapsed

        if available_time <= 0.0:
            return ClusterType.ON_DEMAND

        slack = available_time - remaining_work

        fallback_threshold = self.restart_overhead + gap

        if slack <= fallback_threshold:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)