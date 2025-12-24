import argparse
import math
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.spot_available_history = []
        self.spot_unavailable_history = []
        self.last_decision = None
        self.consecutive_spot = 0
        self.consecutive_unavailable = 0
        self.overhead_remaining = 0
        self.work_remaining = 0
        
    def solve(self, spec_path: str) -> "Solution":
        # Read configuration if needed
        try:
            with open(spec_path, 'r') as f:
                # Placeholder for reading spec if needed
                pass
        except:
            pass
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update state
        time_step = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        
        # Track spot availability history
        if has_spot:
            self.spot_available_history.append(elapsed)
            self.consecutive_spot += 1
            self.consecutive_unavailable = 0
        else:
            self.spot_unavailable_history.append(elapsed)
            self.consecutive_unavailable += 1
            self.consecutive_spot = 0
        
        # Calculate remaining work
        completed = sum(end - start for start, end in self.task_done_time)
        self.work_remaining = self.task_duration - completed
        
        # Calculate time remaining
        time_remaining = deadline - elapsed
        
        # Update overhead remaining
        if self.overhead_remaining > 0:
            self.overhead_remaining = max(0, self.overhead_remaining - time_step)
        
        # Critical section: if we're running out of time, go to on-demand
        # Conservative estimate: assume any future spot usage will have overhead
        min_time_needed = self.work_remaining
        if self.work_remaining > 0 and last_cluster_type == ClusterType.NONE:
            min_time_needed += self.restart_overhead
        
        # Safety margin: 2 hours
        safety_margin = 7200  # 2 hours in seconds
        
        if time_remaining - min_time_needed < safety_margin:
            # We're running out of time, use on-demand
            return ClusterType.ON_DEMAND
        
        # If in overhead period, do nothing
        if self.overhead_remaining > 0:
            return ClusterType.NONE
        
        # If spot was just lost, we need to handle overhead
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.overhead_remaining = self.restart_overhead
            return ClusterType.NONE
        
        # Use spot when available and we have enough time buffer
        if has_spot:
            # Check if we can afford potential interruption
            # Estimate probability of interruption based on recent history
            if len(self.spot_available_history) > 10:
                # Simple heuristic: if spot was recently interrupted frequently, be cautious
                recent_interval = 3600  # 1 hour
                recent_unavailable = sum(1 for t in self.spot_unavailable_history 
                                       if elapsed - t < recent_interval)
                
                if recent_unavailable > 2:  # More than 2 interruptions in last hour
                    # Use on-demand for stability
                    return ClusterType.ON_DEMAND
            
            # Use spot if we have good buffer
            buffer_needed = self.restart_overhead * 2  # Allow for one interruption
            if time_remaining - self.work_remaining > buffer_needed:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        # Spot not available
        # If we just started or have no work done, wait for spot
        if completed == 0 and time_remaining > self.task_duration * 1.5:
            return ClusterType.NONE
        
        # If we've been waiting too long for spot, use on-demand
        if self.consecutive_unavailable * time_step > 1800:  # 30 minutes
            return ClusterType.ON_DEMAND
        
        # Otherwise wait for spot
        return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
