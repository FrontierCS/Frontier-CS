import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args=None):
        super().__init__(args)
        self.best_spot_window = None
        self.safety_margin = None
        self.critical_threshold = None
        self.use_spot_probability = None
        
    def solve(self, spec_path: str) -> "Solution":
        # Estimate parameters from typical values
        # Task: 48h, Deadline: 52h, Overhead: 0.05h (3min)
        # Prices: On-demand ~3.06$/hr, Spot ~0.97$/hr
        
        # Best case: finish with all spot (lower bound on cost)
        # Worst case: use on-demand only (upper bound)
        
        # Strategy: Use spot when available unless:
        # 1. We're in critical zone (must guarantee progress)
        # 2. Recent spot availability has been poor
        # 3. Restart overhead would cause deadline miss
        
        self.safety_margin = 0.1  # 10% safety margin
        self.critical_threshold = 0.8  # Use on-demand when time left < threshold * work left
        self.use_spot_probability = 0.7  # Base probability to use spot when available
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If task is done, do nothing
        if len(self.task_done_time) * self.gap_seconds >= self.task_duration:
            return ClusterType.NONE
            
        # Calculate remaining work and time
        work_done = len(self.task_done_time) * self.gap_seconds
        remaining_work = self.task_duration - work_done
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Critical condition: must use on-demand to guarantee progress
        if time_left <= remaining_work + self.restart_overhead:
            return ClusterType.ON_DEMAND
        
        # Calculate efficiency ratio
        time_per_work = time_left / remaining_work if remaining_work > 0 else float('inf')
        
        # If we have plenty of time, try spot when available
        if has_spot and time_per_work > self.critical_threshold:
            # Use spot with probability based on time pressure
            spot_prob = min(self.use_spot_probability, 
                          (time_per_work - 1.0) / (self.critical_threshold - 1.0))
            
            # Adjust probability based on restart overhead impact
            overhead_impact = self.restart_overhead / remaining_work if remaining_work > 0 else 0
            spot_prob *= (1.0 - overhead_impact)
            
            # Use spot if probability threshold met
            if spot_prob > 0.5:
                return ClusterType.SPOT
        
        # If spot not available or we decided not to use it
        if not has_spot or time_per_work <= self.critical_threshold:
            # Use on-demand if we need to make progress
            if remaining_work > 0 and time_left < remaining_work * (1.0 + self.safety_margin):
                return ClusterType.ON_DEMAND
            # Otherwise, wait for spot
            return ClusterType.NONE
        
        # Default: use on-demand
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)