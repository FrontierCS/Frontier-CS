import sys
import os
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType
from typing import List, Tuple
import math

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.safety_margin = 0
        self.spot_availability_history = []
        self.last_spot_available = False
        self.consecutive_unavailable = 0
        self.consecutive_available = 0
        self.spot_pattern_detected = False
        self.avg_availability = 0.0
        
    def solve(self, spec_path: str) -> "Solution":
        if os.path.exists(spec_path):
            try:
                with open(spec_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if "safety_margin" in line:
                            try:
                                self.safety_margin = float(line.split("=")[1].strip())
                            except:
                                pass
            except:
                pass
        if self.safety_margin <= 0:
            self.safety_margin = 7200  # 2 hours default
            
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update availability history for pattern detection
        self.spot_availability_history.append(has_spot)
        if len(self.spot_availability_history) > 100:
            self.spot_availability_history.pop(0)
        
        # Update consecutive counts
        if has_spot:
            self.consecutive_available += 1
            self.consecutive_unavailable = 0
        else:
            self.consecutive_unavailable += 1
            self.consecutive_available = 0
        
        # Calculate remaining work and time
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        # If no work left, use NONE
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If very little time left, use on-demand to finish
        if remaining_time <= max(remaining_work, self.restart_overhead * 2):
            return ClusterType.ON_DEMAND
        
        # Calculate required progress rate
        required_rate = remaining_work / remaining_time if remaining_time > 0 else float('inf')
        
        # Estimate spot availability pattern
        if len(self.spot_availability_history) >= 20:
            available_count = sum(self.spot_availability_history)
            self.avg_availability = available_count / len(self.spot_availability_history)
            
            # Detect potential patterns
            recent = self.spot_availability_history[-10:]
            if all(recent) or not any(recent):
                self.spot_pattern_detected = True
        
        # Decision logic
        if has_spot:
            # Spot is available
            if required_rate > 0.9:  # Behind schedule
                # Use on-demand if we're significantly behind
                if required_rate > 1.2:
                    return ClusterType.ON_DEMAND
                # Use spot but with caution if pattern detected
                if self.spot_pattern_detected and self.consecutive_available < 5:
                    return ClusterType.NONE
                return ClusterType.SPOT
            else:
                # On schedule or ahead
                if self.consecutive_available >= 3:  # Stable spot availability
                    return ClusterType.SPOT
                else:
                    # Wait to see if spot becomes stable
                    return ClusterType.NONE
        else:
            # Spot is not available
            if required_rate > 1.0:  # Behind schedule
                return ClusterType.ON_DEMAND
            elif remaining_time < remaining_work + self.safety_margin:
                return ClusterType.ON_DEMAND
            else:
                # Wait for spot
                if self.consecutive_unavailable > 10 and self.avg_availability < 0.2:
                    # Very low availability environment
                    if remaining_time < remaining_work + (self.safety_margin / 2):
                        return ClusterType.ON_DEMAND
                return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
