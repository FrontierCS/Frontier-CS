import numpy as np
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

    def __init__(self, args=None):
        super().__init__(args)
        self.last_spot_available = True
        self.consecutive_spot_available = 0
        self.spot_reliability_est = 0.6
        self.safety_buffer = 0.0
        self.last_decision = ClusterType.NONE
        self.work_remaining_ratio = 1.0
        self.spot_unavailable_streak = 0
        self.time_since_start = 0.0
        self.initialized = False
        self.spot_history = []
        self.window_size = 50

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            self.initialized = True
            self.time_since_start = self.env.elapsed_seconds
            self.safety_buffer = min(3600.0, (self.deadline - self.time_since_start) * 0.1)
        
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        if len(self.task_done_time) > 0:
            work_done = sum(self.task_done_time)
        else:
            work_done = 0.0
            
        work_remaining = max(0.0, self.task_duration - work_done)
        
        if work_remaining <= 0:
            return ClusterType.NONE
            
        self.spot_history.append(has_spot)
        if len(self.spot_history) > self.window_size:
            self.spot_history.pop(0)
            
        spot_reliability = np.mean(self.spot_history) if self.spot_history else 0.6
        
        required_rate = work_remaining / time_remaining if time_remaining > 0 else float('inf')
        
        if not has_spot:
            self.spot_unavailable_streak += 1
            self.consecutive_spot_available = 0
        else:
            self.spot_unavailable_streak = 0
            self.consecutive_spot_available += 1
        
        urgency_factor = min(1.0, max(0.0, (work_remaining - time_remaining * 0.95) / (self.task_duration * 0.1)))
        
        critical_time = work_remaining + self.restart_overhead * 2
        if time_remaining < critical_time * 1.2:
            return ClusterType.ON_DEMAND
        
        if self.consecutive_spot_available >= 5 and spot_reliability > 0.7:
            if has_spot:
                return ClusterType.SPOT
        
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            if time_remaining < work_remaining + self.restart_overhead * 3:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
        
        if has_spot:
            if work_remaining / self.task_duration > 0.8:
                return ClusterType.SPOT
            elif time_remaining > work_remaining * 1.5 + self.restart_overhead * 5:
                return ClusterType.SPOT
            elif spot_reliability > 0.8 and self.consecutive_spot_available > 3:
                return ClusterType.SPOT
            else:
                if time_remaining < work_remaining * 1.2 + self.restart_overhead * 2:
                    return ClusterType.ON_DEMAND
                elif urgency_factor > 0.7:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.SPOT
        else:
            if time_remaining < work_remaining + self.restart_overhead * 2:
                return ClusterType.ON_DEMAND
            elif self.spot_unavailable_streak > 10 and time_remaining < work_remaining * 1.5:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE