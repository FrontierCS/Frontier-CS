from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.safe_mode = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        task_done = sum(self.task_done_time)
        remaining = self.task_duration - task_done
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if time_left <= 0 or remaining <= 0:
            return ClusterType.NONE
        buffer_seconds = time_left - remaining
        safety = 3600.0
        if buffer_seconds < safety or self.safe_mode:
            self.safe_mode = True
            return ClusterType.ON_DEMAND
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)