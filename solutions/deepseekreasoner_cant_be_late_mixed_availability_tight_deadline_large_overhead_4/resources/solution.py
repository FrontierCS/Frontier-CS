import argparse
import math
from enum import Enum
from typing import List, Tuple

class ClusterType(Enum):
    SPOT = "SPOT"
    ON_DEMAND = "ON_DEMAND"
    NONE = "NONE"

class Strategy:
    pass

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args=None):
        super().__init__()
        self.args = args
        self.task_duration = None
        self.deadline = None
        self.restart_overhead = None
        self.env = None
        self.task_done_time = None
        
        # Internal state
        self.work_remaining = 0.0
        self.time_remaining = 0.0
        self.last_spot_work_time = 0.0
        self.spot_available_history = []
        self.consecutive_spot_available = 0
        self.consecutive_spot_unavailable = 0
        self.last_action = None
        self.restart_pending = 0.0
        
    def solve(self, spec_path: str) -> "Solution":
        # Read configuration if needed
        # For now, just return self
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state from environment
        current_time = self.env.elapsed_seconds
        time_step = self.env.gap_seconds
        
        # Track spot availability history
        self.spot_available_history.append(1 if has_spot else 0)
        if len(self.spot_available_history) > 100:
            self.spot_available_history.pop(0)
            
        # Update consecutive counters
        if has_spot:
            self.consecutive_spot_available += 1
            self.consecutive_spot_unavailable = 0
        else:
            self.consecutive_spot_unavailable += 1
            self.consecutive_spot_available = 0
        
        # Calculate work remaining
        total_done = 0.0
        for start, end in self.task_done_time:
            total_done += end - start
        self.work_remaining = self.task_duration - total_done
        
        # Calculate time remaining
        self.time_remaining = self.deadline - current_time
        
        # Update restart pending counter
        if last_cluster_type == ClusterType.SPOT:
            if self.restart_pending > 0:
                self.restart_pending -= time_step
                if self.restart_pending < 0:
                    self.restart_pending = 0
        else:
            # Reset restart counter when not using spot
            self.restart_pending = 0
        
        # Emergency mode: switch to on-demand if we're running out of time
        safety_margin = self.restart_overhead * 2.0  # 24 minutes buffer
        time_needed_for_remaining_work = self.work_remaining
        
        # If we're in restart overhead, add that time
        if self.restart_pending > 0:
            time_needed_for_remaining_work += self.restart_pending
            
        if self.time_remaining - time_needed_for_remaining_work < safety_margin:
            # We're getting too close to deadline, use on-demand
            if self.work_remaining > 0:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE
        
        # Early completion check
        if self.work_remaining <= 0:
            return ClusterType.NONE
            
        # Check if we should wait due to restart overhead
        if self.restart_pending > 0:
            # If restart overhead is small compared to time remaining, wait
            if self.restart_pending < time_step * 2:
                return ClusterType.NONE
            # Otherwise switch to on-demand to avoid waiting too long
            return ClusterType.ON_DEMAND
        
        # Calculate spot reliability score
        spot_reliability = 0.0
        if len(self.spot_available_history) > 0:
            spot_reliability = sum(self.spot_available_history) / len(self.spot_available_history)
        
        # Determine if we should use spot
        if has_spot:
            # Use spot if reliability is decent and we have time buffer
            time_buffer_needed = self.restart_overhead * 2.0
            
            # Calculate risk factor based on current progress
            progress_ratio = 1.0 - (self.work_remaining / self.task_duration)
            completion_ratio = 1.0 - (self.time_remaining / (self.deadline - 0))
            
            # More conservative as we approach deadline
            risk_tolerance = min(1.0, self.time_remaining / (self.deadline * 0.3))
            
            # Use spot if:
            # 1. We have good spot availability recently
            # 2. We have time buffer for potential restart
            # 3. We're not too close to deadline
            use_spot_threshold = 0.3 + 0.4 * risk_tolerance
            
            recent_reliability = spot_reliability
            if self.consecutive_spot_available > 5:
                recent_reliability = 1.0
            
            if (recent_reliability > use_spot_threshold and 
                self.time_remaining - time_needed_for_remaining_work > time_buffer_needed and
                self.consecutive_spot_unavailable < 3):
                
                # Mark that we're using spot, which may trigger restart overhead later
                self.last_spot_work_time = current_time
                return ClusterType.SPOT
        
        # Default to on-demand
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
