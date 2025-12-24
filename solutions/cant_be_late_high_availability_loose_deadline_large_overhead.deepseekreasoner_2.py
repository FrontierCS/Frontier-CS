import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.time_step = None
        self.work_estimate = None
        self.safety_factor = 1.2
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.time_step is None:
            self.time_step = self.env.gap_seconds
            self.work_estimate = self.task_duration
        
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        if time_remaining <= 0:
            return ClusterType.ON_DEMAND
        
        completed_work = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - completed_work
        
        if work_remaining <= 0:
            return ClusterType.NONE
        
        required_rate = work_remaining / time_remaining
        
        effective_time = time_remaining
        if last_cluster_type != ClusterType.SPOT and has_spot:
            effective_time -= min(self.restart_overhead, effective_time)
        
        spot_rate = 0.0
        if has_spot and effective_time > 0:
            spot_rate = work_remaining / effective_time
        
        cost_on_demand = self._cost_on_demand(work_remaining)
        cost_spot = self._cost_spot(work_remaining)
        
        if spot_rate <= self.safety_factor and has_spot and cost_spot < cost_on_demand:
            if last_cluster_type != ClusterType.SPOT:
                overhead_time = min(self.restart_overhead, time_remaining)
                if work_remaining <= (time_remaining - overhead_time):
                    return ClusterType.SPOT
            else:
                return ClusterType.SPOT
        
        required_rate_threshold = 0.95
        if required_rate > required_rate_threshold:
            return ClusterType.ON_DEMAND
        
        if has_spot and cost_spot < cost_on_demand:
            if last_cluster_type != ClusterType.SPOT:
                overhead_time = min(self.restart_overhead, time_remaining)
                if work_remaining <= (time_remaining - overhead_time):
                    return ClusterType.SPOT
            else:
                return ClusterType.SPOT
        
        if required_rate < 0.1:
            return ClusterType.NONE
        
        return ClusterType.ON_DEMAND
    
    def _cost_on_demand(self, work_remaining):
        return work_remaining * 3.06 / 3600
    
    def _cost_spot(self, work_remaining):
        return work_remaining * 0.97 / 3600
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
