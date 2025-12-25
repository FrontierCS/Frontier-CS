import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
import argparse

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.config = {}
        self.remaining_work = 0.0
        self.spot_down_time = 0.0
        self.last_action = ClusterType.NONE
        self.consecutive_spot_use = 0
        self.consecutive_od_use = 0
        self.work_history = []
        self.time_history = []
        self.spot_history = []
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Track history
        self.work_history.append(sum(self.task_done_time))
        self.time_history.append(elapsed)
        self.spot_history.append(has_spot)
        
        # Calculate remaining work
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # If work is done, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Calculate time left
        time_left = self.deadline - elapsed
        if time_left <= 0:
            return ClusterType.NONE
            
        # Calculate urgency factor
        if time_left > 0:
            work_rate_needed = remaining_work / time_left
        else:
            work_rate_needed = float('inf')
            
        # Update spot down timer
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.spot_down_time = self.restart_overhead
        elif self.spot_down_time > 0:
            self.spot_down_time -= gap
            
        # Track consecutive usage
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_use += 1
            self.consecutive_od_use = 0
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.consecutive_od_use += 1
            self.consecutive_spot_use = 0
        else:
            self.consecutive_spot_use = 0
            self.consecutive_od_use = 0
            
        # Urgency threshold calculation
        # Start conservative, become more aggressive as deadline approaches
        if time_left < 2 * 3600:  # Less than 2 hours left
            urgency_threshold = 0.8
        elif time_left < 6 * 3600:  # Less than 6 hours left
            urgency_threshold = 0.6
        elif time_left < 12 * 3600:  # Less than 12 hours left
            urgency_threshold = 0.4
        else:
            urgency_threshold = 0.2
            
        # Safety margin calculation
        safety_margin = max(self.restart_overhead * 2, 3600)  # At least 1 hour safety
        
        # Decision logic
        if work_rate_needed > 1.2 or time_left < remaining_work + safety_margin:
            # Critical: need to work fast
            return ClusterType.ON_DEMAND
            
        elif has_spot and self.spot_down_time <= 0:
            # Spot is available and not in restart overhead
            
            # Calculate risk factor based on consecutive spot usage
            spot_risk = min(self.consecutive_spot_use * gap / 3600.0, 2.0) / 2.0
            
            # Calculate time buffer
            time_buffer = time_left - remaining_work
            
            # Conservative strategy: use spot only if we have enough buffer
            if time_buffer > self.restart_overhead * 3 and spot_risk < 0.7:
                # Check if we should pause to avoid potential restart
                if self.consecutive_spot_use * gap > 1800 and time_buffer > 7200:  # Used spot for >30min, buffer >2hr
                    # Pause briefly to reset consecutive counter
                    if remaining_work / max(time_left - 3600, 1) < 0.9:
                        return ClusterType.NONE
                    else:
                        return ClusterType.SPOT
                else:
                    return ClusterType.SPOT
            elif time_buffer > self.restart_overhead * 1.5 and spot_risk < 0.5:
                return ClusterType.SPOT
            else:
                # Not enough buffer or too risky
                if work_rate_needed > urgency_threshold:
                    return ClusterType.ON_DEMAND
                else:
                    # Wait for better conditions
                    return ClusterType.NONE
                    
        elif not has_spot and work_rate_needed > urgency_threshold:
            # Spot not available and we're falling behind
            return ClusterType.ON_DEMAND
            
        elif self.spot_down_time > 0 and work_rate_needed > urgency_threshold * 1.5:
            # In restart overhead but urgent
            return ClusterType.ON_DEMAND
            
        else:
            # Wait for spot or better conditions
            return ClusterType.NONE