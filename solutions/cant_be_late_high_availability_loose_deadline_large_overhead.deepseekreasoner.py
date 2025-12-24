import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def solve(self, spec_path: str) -> "Solution":
        # Initialize strategy parameters
        self.spot_price = 0.97
        self.od_price = 3.06
        self.spot_od_ratio = self.spot_price / self.od_price
        
        # Conservative parameters for safety
        self.min_safety_margin = 4 * 3600  # 4 hours in seconds
        self.switch_to_od_threshold = 0.25
        self.switch_to_spot_threshold = 0.35
        
        # State tracking
        self.current_progress = 0.0
        self.last_decision = None
        self.consecutive_spot_failures = 0
        self.spot_availability_history = []
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update progress tracking
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        progress = work_done / self.task_duration
        self.current_progress = progress
        
        # Update spot availability history
        self.spot_availability_history.append(has_spot)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Calculate remaining time and work
        remaining_time = self.deadline - self.env.elapsed_seconds
        remaining_work = self.task_duration - work_done
        
        # Calculate conservative time needed
        time_needed_no_overhead = remaining_work
        if self.env.cluster_type != last_cluster_type and last_cluster_type != ClusterType.NONE:
            # Account for potential restart if we just switched
            time_needed_no_overhead += self.restart_overhead
        
        # Calculate urgency factor (0 = plenty of time, 1 = critical)
        slack_time = remaining_time - time_needed_no_overhead
        urgency = max(0.0, 1.0 - (slack_time / (self.min_safety_margin * 2)))
        
        # Calculate spot reliability from history
        if self.spot_availability_history:
            spot_reliability = sum(self.spot_availability_history) / len(self.spot_availability_history)
        else:
            spot_reliability = 0.5
        
        # Determine decision
        if urgency > self.switch_to_od_threshold:
            # High urgency: use on-demand to guarantee completion
            if has_spot and urgency < self.switch_to_spot_threshold:
                # Moderate urgency with spot available
                if spot_reliability > 0.6:
                    return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        else:
            # Low urgency: prefer spot when available
            if has_spot:
                # Use spot if we have good reliability or enough time to recover
                if spot_reliability > 0.4 or slack_time > 2 * self.restart_overhead:
                    return ClusterType.SPOT
                else:
                    return ClusterType.NONE
            else:
                # No spot available, wait for it if we have time
                if slack_time > self.restart_overhead:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
