import heapq
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def solve(self, spec_path: str) -> "Solution":
        # Initialize internal state
        self.remaining_work = 0
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.price_ratio = self.spot_price / self.ondemand_price
        self.required_duration = 48 * 3600  # 48 hours in seconds
        self.deadline_buffer = 4 * 3600  # 4 hours in seconds
        self.restart_penalty = 3 * 60  # 3 minutes in seconds
        self.safety_factor = 0.85  # Conservative factor for restart penalties
        self.phase = "initial"
        self.spot_unavailable_streak = 0
        self.consecutive_spot_work = 0
        self.last_decision = ClusterType.NONE
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate current progress
        elapsed = self.env.elapsed_seconds
        total_work_done = sum(self.task_done_time) if self.task_done_time else 0
        self.remaining_work = self.task_duration - total_work_done
        time_left = self.deadline - elapsed
        
        # Emergency check: if we're running out of time, use on-demand
        if time_left <= self.remaining_work + self.restart_overhead * 2:
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Check if we can finish with spot given current time
        # Account for potential future interruptions
        estimated_spot_time = self.remaining_work
        if last_cluster_type != ClusterType.SPOT or not has_spot:
            estimated_spot_time += self.restart_overhead
        
        safe_spot_time = estimated_spot_time * (1.0 / self.safety_factor)
        
        # If safe spot time is less than time left, try spot
        if has_spot and safe_spot_time <= time_left:
            # Track spot availability streak
            if has_spot:
                self.spot_unavailable_streak = 0
                self.consecutive_spot_work += self.env.gap_seconds
            else:
                self.spot_unavailable_streak += 1
                self.consecutive_spot_work = 0
            
            # If we've been using spot successfully for a while, continue
            if self.consecutive_spot_work > self.restart_overhead * 5:
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
            
            # Avoid switching too frequently
            if (last_cluster_type == ClusterType.SPOT and has_spot and 
                self.consecutive_spot_work > 0):
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
            
            # Only use spot if we have good margin
            margin_needed = self.restart_overhead * 3
            if time_left - estimated_spot_time > margin_needed:
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
        
        # Default to on-demand if spot is unavailable or margin is tight
        if not has_spot or time_left - estimated_spot_time <= self.restart_overhead * 2:
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Otherwise wait
        self.last_decision = ClusterType.NONE
        return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
