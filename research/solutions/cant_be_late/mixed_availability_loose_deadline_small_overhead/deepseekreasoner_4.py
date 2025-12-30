import sys
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.current_cluster = None
        self.remaining_restart = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        SAFETY_MARGIN = 3600
        LARGE_MARGIN = 7200
        
        if self.remaining_restart > 0:
            self.remaining_restart -= self.env.gap_seconds
            if self.remaining_restart < 0:
                self.remaining_restart = 0

        self.current_cluster = self.env.cluster_type
        
        remaining_work = self.task_duration - sum(self.task_done_time)
        time_left = self.deadline - self.env.elapsed_seconds
        
        if self.remaining_restart > 0:
            if remaining_work + self.remaining_restart > time_left:
                self.remaining_restart = self.restart_overhead
                self.current_cluster = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
            return ClusterType.NONE
        
        if self.current_cluster is not None and self.current_cluster != ClusterType.NONE:
            if self.current_cluster == ClusterType.SPOT and not has_spot:
                self.remaining_restart = self.restart_overhead
                self.current_cluster = None
                return ClusterType.NONE
            else:
                if (self.current_cluster == ClusterType.ON_DEMAND and 
                    has_spot and 
                    remaining_work < time_left - LARGE_MARGIN):
                    self.current_cluster = ClusterType.SPOT
                    return ClusterType.SPOT
                elif (self.current_cluster == ClusterType.SPOT and 
                      remaining_work > time_left - SAFETY_MARGIN):
                    self.current_cluster = ClusterType.ON_DEMAND
                    return ClusterType.ON_DEMAND
                else:
                    return self.current_cluster
        else:
            if has_spot and remaining_work < time_left - SAFETY_MARGIN:
                self.current_cluster = ClusterType.SPOT
                return ClusterType.SPOT
            else:
                self.current_cluster = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)