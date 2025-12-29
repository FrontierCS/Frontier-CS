import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.97 / 3600.0  # $/second
        self.ondemand_price = 3.06 / 3600.0  # $/second
        self.required_work = None
        self.deadline_buffer = 22 * 3600  # 22 hours in seconds
        self.conservative_threshold = 4.0  # hours before deadline to go full ondemand

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.required_work is None:
            self.required_work = self.task_duration
            
        elapsed = self.env.elapsed_seconds
        remaining_work = self.required_work - sum(self.task_done_time)
        time_to_deadline = self.deadline - elapsed
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        if time_to_deadline <= 0:
            return ClusterType.NONE
            
        # Emergency mode: if we're running out of time, use ondemand
        emergency_hours = self.conservative_threshold
        if time_to_deadline <= remaining_work + self.restart_overhead + emergency_hours * 3600:
            if has_spot:
                # Even in emergency, try spot if available and we have time for restart
                time_with_spot = remaining_work + self.restart_overhead
                if time_with_spot <= time_to_deadline:
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Normal operation
        if has_spot:
            # Use spot if it makes economic sense
            spot_time_needed = remaining_work + self.restart_overhead
            if spot_time_needed <= time_to_deadline:
                # Calculate probability we need to switch later
                # Use a simple heuristic based on time remaining
                spot_value = (time_to_deadline - spot_time_needed) / self.deadline
                if spot_value > 0.1:  # Only if we have reasonable buffer
                    return ClusterType.SPOT
        
        # If spot not available or not economical, use ondemand
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)