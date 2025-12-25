import sys
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.config = {}
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.task_duration <= 0:
            return ClusterType.NONE
            
        if self.env.elapsed_seconds >= self.deadline:
            return ClusterType.NONE
            
        work_done = sum(self.task_done_time) if self.task_done_time else 0
        work_remaining = self.task_duration - work_done
        
        if work_remaining <= 0:
            return ClusterType.NONE
            
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        progress_rate = 0.0
        if self.env.elapsed_seconds > 0:
            progress_rate = work_done / self.env.elapsed_seconds
        
        required_rate = work_remaining / time_remaining if time_remaining > 0 else float('inf')
        
        conservative_factor = 1.3
        safe_required_rate = required_rate * conservative_factor
        
        has_enough_time = time_remaining > work_remaining * (1 + 0.5)
        
        emergency_mode = time_remaining < work_remaining * 1.2 or progress_rate < 0.6
        
        if emergency_mode:
            if has_spot and time_remaining > work_remaining * 1.5:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        if not has_enough_time:
            return ClusterType.ON_DEMAND
        
        if has_spot and time_remaining > work_remaining * 1.3:
            if safe_required_rate < 0.7:
                return ClusterType.SPOT
            elif safe_required_rate < 0.9 and has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        if has_spot and time_remaining > work_remaining * 1.1:
            return ClusterType.SPOT
        
        if time_remaining > work_remaining * 1.05:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        
        return ClusterType.ON_DEMAND