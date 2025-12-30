import argparse
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.safety_margin = 0.0
        self.consecutive_spot_failures = 0
        self.last_decision = ClusterType.NONE
        self.work_done = 0.0
        self.work_rates = {ClusterType.SPOT: 1.0, ClusterType.ON_DEMAND: 1.0, ClusterType.NONE: 0.0}
        self.min_spot_availability = 0.43
        self.max_spot_availability = 0.78

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds / 3600.0
        deadline = self.deadline / 3600.0
        task_duration = self.task_duration / 3600.0
        overhead = self.restart_overhead / 3600.0
        
        if elapsed >= deadline:
            return ClusterType.NONE

        completed_work = sum(end - start for start, end in self.task_done_time) / 3600.0
        remaining_work = task_duration - completed_work
        remaining_time = deadline - elapsed
        
        if remaining_work <= 0:
            return ClusterType.NONE
        
        required_rate = remaining_work / remaining_time if remaining_time > 0 else float('inf')
        
        spot_available = has_spot
        current_type = self.env.cluster_type
        
        if spot_available:
            effective_spot_rate = self.work_rates[ClusterType.SPOT]
            spot_time_needed = remaining_work / effective_spot_rate
            spot_buffer = overhead * 2
            
            if current_type == ClusterType.SPOT:
                self.consecutive_spot_failures = 0
            else:
                if self.last_decision != ClusterType.SPOT and current_type != ClusterType.SPOT:
                    spot_time_needed += overhead
            
            can_use_spot = (spot_time_needed + spot_buffer <= remaining_time)
            
            if can_use_spot:
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
        
        ondemand_time_needed = remaining_work / self.work_rates[ClusterType.ON_DEMAND]
        if current_type != ClusterType.ON_DEMAND:
            ondemand_time_needed += overhead
        
        critical_time = ondemand_time_needed * 1.2
        
        if remaining_time <= critical_time or required_rate > 0.8:
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        if not spot_available:
            if self.consecutive_spot_failures < 2 and remaining_time > ondemand_time_needed * 1.5:
                self.consecutive_spot_failures += 1
                self.last_decision = ClusterType.NONE
                return ClusterType.NONE
            else:
                self.consecutive_spot_failures = 0
                self.last_decision = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        
        self.last_decision = ClusterType.NONE
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)