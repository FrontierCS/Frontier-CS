import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.restart_timer = 0
        self.last_decision = ClusterType.NONE
        self.spot_availability_history = []
        self.spot_down_time = 0
        self.spot_up_time = 0
        self.consecutive_spot_failures = 0
        
    def solve(self, spec_path: str) -> "Solution":
        # Initialize based on spec if needed
        self.restart_timer = 0
        self.last_decision = ClusterType.NONE
        self.spot_availability_history = []
        self.spot_down_time = 0
        self.spot_up_time = 0
        self.consecutive_spot_failures = 0
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Track spot availability pattern
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Update restart timer
        if self.restart_timer > 0:
            self.restart_timer = max(0, self.restart_timer - self.env.gap_seconds)
        
        # Calculate work done and remaining
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = max(0, self.task_duration - work_done)
        
        # Calculate time remaining until deadline
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # If no work left, pause
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # Emergency mode: if we're running out of time
        safety_margin = self.restart_overhead * 2
        time_needed = work_remaining + (self.restart_timer if self.restart_timer > 0 else 0)
        
        if time_remaining <= time_needed + safety_margin:
            # Must use on-demand to ensure meeting deadline
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Normal decision logic
        # Check if we're in restart period
        if self.restart_timer > 0:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
        
        # Calculate spot reliability from history
        if len(self.spot_availability_history) > 10:
            spot_reliability = np.mean(self.spot_availability_history[-20:])
        else:
            spot_reliability = 0.5 if has_spot else 0.3
        
        # Update consecutive failures counter
        if not has_spot:
            self.consecutive_spot_failures += 1
            self.spot_down_time += self.env.gap_seconds
            self.spot_up_time = 0
        else:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
            self.spot_up_time += self.env.gap_seconds
            self.spot_down_time = 0
        
        # Aggressively use spot when available and reliable
        if has_spot:
            # Use spot if reliability is reasonable and we have time buffer
            buffer_needed = self.restart_overhead * (1 + self.consecutive_spot_failures * 0.5)
            
            if (spot_reliability > 0.3 and 
                time_remaining > work_remaining + buffer_needed and
                self.consecutive_spot_failures < 3):
                
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
        
        # Fallback to on-demand if spot unavailable or unreliable
        self.last_decision = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)