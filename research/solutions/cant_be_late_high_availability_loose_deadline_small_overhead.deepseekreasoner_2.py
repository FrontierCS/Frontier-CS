import os
import json
from enum import Enum
from typing import List, Optional
import math

# These imports would be provided by the environment
# from sky_spot.strategies.strategy import Strategy
# from sky_spot.utils import ClusterType

# Mock imports for local development
class ClusterType(Enum):
    SPOT = "SPOT"
    ON_DEMAND = "ON_DEMAND"
    NONE = "NONE"

class MockStrategy:
    def __init__(self):
        self.env = type('obj', (object,), {})()
        self.env.elapsed_seconds = 0
        self.env.gap_seconds = 1
        self.env.cluster_type = ClusterType.NONE
        self.task_duration = 0
        self.task_done_time = []
        self.deadline = 0
        self.restart_overhead = 0

class Strategy(MockStrategy):
    pass

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__()
        self.args = args
        self.remaining_work = 0
        self.overhead_remaining = 0
        self.conservative_mode = False
        self.last_spot_unavailable_time = 0
        self.spot_unavailable_streak = 0
        self.consecutive_spot_work = 0
        self.initial_slack = 0
        
        # Tuning parameters
        self.safety_margin_hours = 1.5
        self.spot_unavailable_threshold = 10
        self.max_consecutive_spot = 120
        self.critical_time_ratio = 0.15

    def solve(self, spec_path: str) -> "Solution":
        """Optional initialization. Called once before evaluation."""
        if os.path.exists(spec_path):
            try:
                with open(spec_path, 'r') as f:
                    spec = json.load(f)
                    # Could read tuning parameters from spec
                    pass
            except:
                pass
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """Decision logic for each time step."""
        
        # Update internal state
        self.remaining_work = self.task_duration - sum(self.task_done_time)
        self.overhead_remaining = max(0, self.overhead_remaining - self.env.gap_seconds)
        
        # If no work remaining, use NONE to minimize cost
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate time constraints
        time_remaining = self.deadline - self.env.elapsed_seconds
        work_time_needed = self.remaining_work
        if last_cluster_type == ClusterType.NONE and self.env.cluster_type != ClusterType.NONE:
            work_time_needed += self.restart_overhead
        
        # Check if we're in critical time
        slack_ratio = time_remaining / self.initial_slack if self.initial_slack > 0 else 1.0
        if slack_ratio < self.critical_time_ratio:
            self.conservative_mode = True
        
        # Update spot availability tracking
        if not has_spot:
            self.spot_unavailable_streak += 1
            self.last_spot_unavailable_time = self.env.elapsed_seconds
        else:
            self.spot_unavailable_streak = 0
        
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_work += 1
        else:
            self.consecutive_spot_work = 0
        
        # Check if we need to be conservative
        safety_margin = self.safety_margin_hours * 3600
        min_time_needed = work_time_needed + (self.restart_overhead if last_cluster_type != ClusterType.ON_DEMAND else 0)
        
        if time_remaining < min_time_needed + safety_margin:
            self.conservative_mode = True
        
        # Decision logic
        if self.conservative_mode:
            # In conservative mode, use on-demand to ensure meeting deadline
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                # Switch to on-demand, incurring restart overhead
                return ClusterType.ON_DEMAND
        
        # Normal mode: try to use spot when available
        if has_spot:
            # Use spot if we haven't used it too much consecutively
            if (self.consecutive_spot_work < self.max_consecutive_spot and 
                self.spot_unavailable_streak == 0):
                
                # Check if we have enough time to recover from potential spot failure
                time_if_fail = (self.remaining_work + self.restart_overhead * 2 + 
                              self.safety_margin_hours * 3600)
                if time_remaining > time_if_fail:
                    return ClusterType.SPOT
        
        # If spot is unavailable for too long, consider switching to on-demand
        if (self.spot_unavailable_streak > self.spot_unavailable_threshold and 
            time_remaining < work_time_needed + safety_margin * 2):
            return ClusterType.ON_DEMAND
        
        # Default: use on-demand to ensure progress
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        """For evaluator instantiation."""
        args, _ = parser.parse_known_args()
        return cls(args)