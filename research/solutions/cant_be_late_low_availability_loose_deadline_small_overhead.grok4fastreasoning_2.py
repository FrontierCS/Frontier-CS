from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "safe_spot_strategy"

    def solve(self, spec_path: str) -> "Solution":
        self.safe_mode = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        remaining = self.task_duration - done
        if remaining <= 0:
            return ClusterType.NONE
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        lost_so_far = elapsed - done
        projected_finish = elapsed + remaining

        if not self.safe_mode:
            buffer = 5.0  # hours
            if projected_finish > self.deadline - buffer or lost_so_far > 10.0:
                self.safe_mode = True

        if self.safe_mode or remaining > time_left:
            return ClusterType.ON_DEMAND
        elif has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)