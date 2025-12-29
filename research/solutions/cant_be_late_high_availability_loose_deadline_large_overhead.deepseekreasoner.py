import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.price_spot = 0.97
        self.price_ondemand = 3.06
        self.safety_buffer = 1.5  # hours of safety buffer
        self.min_spot_run = 0.5   # minimum hours to run spot before considering switch
        self.last_spot_start = -1000
        self.consecutive_spot_failures = 0
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate work done and remaining
        total_done = sum(end - start for start, end in self.task_done_time)
        remaining_work = max(0, self.task_duration - total_done)
        current_time = self.env.elapsed_seconds / 3600.0
        remaining_time = (self.deadline - self.env.elapsed_seconds) / 3600.0
        restart_hours = self.restart_overhead / 3600.0
        
        # If work is done, stop
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If we're at risk of missing deadline, use on-demand
        time_needed = remaining_work + restart_hours  # worst case with one restart
        if remaining_time < time_needed * self.safety_buffer:
            return ClusterType.ON_DEMAND
        
        # If spot is available and we haven't had too many failures recently
        if has_spot:
            # Check if we should continue with current cluster type
            if last_cluster_type == ClusterType.SPOT:
                self.consecutive_spot_failures = 0
                # Calculate expected completion time if we continue with spot
                spot_progress_per_hour = self.env.gap_seconds / 3600.0
                expected_hours = remaining_work / spot_progress_per_hour
                
                # If we can finish with spot and have buffer, stay with spot
                if remaining_time > expected_hours * 1.2:
                    return ClusterType.SPOT
                # Otherwise switch to on-demand to be safe
                else:
                    return ClusterType.ON_DEMAND
                    
            # If we're currently on on-demand, check if we should switch back to spot
            elif last_cluster_type == ClusterType.ON_DEMAND:
                # Only switch if we have significant time savings and buffer
                if remaining_time > (remaining_work + restart_hours) * 2.0:
                    hours_since_spot_start = current_time - self.last_spot_start
                    if hours_since_spot_start > self.min_spot_run or self.consecutive_spot_failures < 2:
                        return ClusterType.SPOT
                        
            # If we're currently on NONE, start with spot if available
            else:
                return ClusterType.SPOT
        else:
            # Spot not available
            if last_cluster_type == ClusterType.SPOT:
                self.consecutive_spot_failures += 1
                self.last_spot_start = current_time
                
            # Use on-demand if we need to make progress, otherwise wait
            if remaining_time < remaining_work * 1.5:
                return ClusterType.ON_DEMAND
                
        # Default to on-demand for safety
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)