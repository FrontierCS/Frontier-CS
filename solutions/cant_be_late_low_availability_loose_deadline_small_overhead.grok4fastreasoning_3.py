from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.total_steps = 0
        self.spot_count = 0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done = sum(self.task_done_time)
        remaining = self.task_duration - total_done
        time_left = self.deadline - self.env.elapsed_seconds

        self.total_steps += 1
        if has_spot:
            self.spot_count += 1

        if self.total_steps >= 20:
            p = self.spot_count / self.total_steps
        else:
            p = 0.2

        estimated_time = remaining / max(p, 0.01)
        buffer = 2 * self.restart_overhead

        if time_left <= remaining + buffer or estimated_time > time_left * 0.9:
            return ClusterType.ON_DEMAND
        else:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
