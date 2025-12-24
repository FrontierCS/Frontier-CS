import random
import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.safety_margin = None
        self.min_spot_window = None
        self.aggressiveness = None
        self.initialized = False
        
    def solve(self, spec_path: str) -> "Solution":
        # Read configuration parameters from spec_path if needed
        self.safety_margin = 0.2  # 20% safety margin
        self.min_spot_window = 1800  # Minimum 30 minutes of continuous spot to be worthwhile
        self.aggressiveness = 0.85  # Higher = more aggressive with spot
        self.initialized = True
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self.initialized:
            # Default parameters if not initialized
            self.safety_margin = 0.2
            self.min_spot_window = 1800
            self.aggressiveness = 0.85
        
        # Calculate progress metrics
        total_done = sum(end - start for start, end in self.task_done_time)
        remaining_work = max(0, self.task_duration - total_done)
        current_time = self.env.elapsed_seconds
        time_remaining = self.deadline - current_time
        
        # If we're done, use NONE to minimize cost
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # If we cannot finish even with 100% on-demand, use on-demand as last resort
        # Account for restart overhead when switching
        effective_remaining = remaining_work
        if last_cluster_type != ClusterType.ON_DEMAND:
            effective_remaining += self.restart_overhead
        
        if effective_remaining > time_remaining:
            return ClusterType.ON_DEMAND
        
        # Calculate required progress rate
        required_rate = effective_remaining / time_remaining if time_remaining > 0 else float('inf')
        
        # Calculate slack ratio (how much time we have vs how much we need)
        slack_ratio = time_remaining / max(effective_remaining, 0.001)
        
        # If we're very tight on time, use on-demand
        if slack_ratio < 1.0 + self.safety_margin:
            return ClusterType.ON_DEMAND
        
        # If spot is available and we have enough slack
        if has_spot and slack_ratio > 1.5:
            # Calculate how long we might use spot
            potential_spot_time = min(
                time_remaining - effective_remaining * (1 + self.safety_margin),
                self.min_spot_window * 2
            )
            
            # Only use spot if we can use it for a meaningful duration
            if potential_spot_time >= self.min_spot_window:
                # Use spot with probability based on aggressiveness and slack
                spot_prob = min(1.0, self.aggressiveness * (slack_ratio - 1.0))
                if random.random() < spot_prob:
                    return ClusterType.SPOT
        
        # If we have moderate slack and spot isn't available or worthwhile, wait
        if slack_ratio > 1.2 and required_rate < 0.7:
            return ClusterType.NONE
        
        # Default to on-demand for reliable progress
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
