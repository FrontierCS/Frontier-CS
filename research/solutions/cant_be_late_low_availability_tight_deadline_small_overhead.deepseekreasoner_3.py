import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.spot_price = 0.97
        self.ondemand_price = 3.06
        self.spot_unavailable_counter = 0
        self.last_spot_available = True
        self.consecutive_unavailable = 0
        self.switch_to_ondemand_time = None
        self.restart_in_progress = False
        self.remaining_restart = 0
        self.spot_unavailable_threshold = 10
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _should_switch_to_ondemand(self, has_spot: bool, time_remaining: float, work_remaining: float) -> bool:
        # Calculate minimum time needed if we use on-demand
        min_time_needed = work_remaining
        
        # If we have less than 4 hours slack or can't finish with spot availability pattern
        if time_remaining < min_time_needed * 1.2:  # 20% safety margin
            return True
            
        # If spot has been unavailable for too many consecutive steps
        if not has_spot and self.consecutive_unavailable >= self.spot_unavailable_threshold:
            return True
            
        # If we're in restart and time is running out
        if self.restart_in_progress and time_remaining < min_time_needed + self.restart_overhead:
            return True
            
        return False
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_time = self.env.elapsed_seconds
        deadline = self.deadline
        restart_overhead = self.restart_overhead
        
        # Calculate work completed and remaining
        work_completed = sum(self.task_done_time) if self.task_done_time else 0
        work_remaining = self.task_duration - work_completed
        time_remaining = deadline - current_time
        
        # Update consecutive unavailable counter
        if has_spot:
            self.consecutive_unavailable = 0
            self.last_spot_available = True
        else:
            self.consecutive_unavailable += 1
            self.last_spot_available = False
        
        # Update restart state
        if self.restart_in_progress:
            self.remaining_restart -= self.env.gap_seconds
            if self.remaining_restart <= 0:
                self.restart_in_progress = False
                self.remaining_restart = 0
        
        # If we just finished work, return NONE
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # Calculate required work rate
        required_rate = work_remaining / time_remaining if time_remaining > 0 else float('inf')
        
        # Emergency: must use on-demand to finish in time
        if time_remaining <= work_remaining:
            return ClusterType.ON_DEMAND
        
        # Check if we should switch to on-demand
        if self._should_switch_to_ondemand(has_spot, time_remaining, work_remaining):
            return ClusterType.ON_DEMAND
        
        # If restart is in progress, wait it out
        if self.restart_in_progress and self.remaining_restart > 0:
            return ClusterType.NONE
        
        # Use spot if available and we have time buffer
        if has_spot:
            # If we were using on-demand and have time, consider switching back to spot
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Only switch back if we have sufficient time buffer
                buffer_needed = restart_overhead * 2  # Safety buffer
                if time_remaining > work_remaining + buffer_needed:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT
        else:
            # Spot unavailable, use on-demand if we can't afford to wait
            if time_remaining < work_remaining + restart_overhead * 2:
                return ClusterType.ON_DEMAND
            # Otherwise wait
            return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)