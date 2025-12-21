from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
from typing import List

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        total_done: float = sum(self.task_done_time)
        remaining_work: float = self.task_duration - total_done
        elapsed: float = self.env.elapsed_seconds
        remaining_wall: float = self.deadline - elapsed
        slack: float = remaining_wall - remaining_work
        overhead: float = self.restart_overhead

        if remaining_work <= 0 or remaining_wall <= 0:
            return ClusterType.NONE

        if not has_spot:
            return ClusterType.ON_DEMAND
        else:
            if last_cluster_type == ClusterType.SPOT:
                # Continuing a burst
                if slack >= overhead:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # Potential new burst
                if slack >= overhead:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
