import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__(args)
        self.remaining_work = None
        self.time_to_deadline = None
        self.overhead_remaining = 0
        self.last_decision = ClusterType.NONE
        
    def solve(self, spec_path: str) -> "Solution":
        # Initialize with task parameters
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update state
        current_time = self.env.elapsed_seconds
        self.time_to_deadline = self.deadline - current_time
        
        # Calculate remaining work
        completed = sum(self.task_done_time)
        self.remaining_work = self.task_duration - completed
        
        # Update overhead
        if self.overhead_remaining > 0:
            self.overhead_remaining = max(0, self.overhead_remaining - self.env.gap_seconds)
        
        # If overhead active, cannot do work
        if self.overhead_remaining > 0:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
        
        # Check if we've completed the task
        if self.remaining_work <= 0:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
        
        # Calculate conservative time needed
        time_needed = self.remaining_work
        
        # If we're critically short on time, use on-demand
        if self.time_to_deadline < time_needed * 1.1:  # 10% safety margin
            if has_spot:
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
            else:
                self.last_decision = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        
        # Normal operation - use spot when available
        if has_spot:
            # Check if we should switch from on-demand to spot
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Only switch if we have enough time buffer
                buffer_needed = self.restart_overhead * 2
                if self.time_to_deadline - time_needed > buffer_needed:
                    # Switching from on-demand to spot - incur restart overhead
                    self.overhead_remaining = self.restart_overhead
                    self.last_decision = ClusterType.NONE
                    return ClusterType.NONE
                else:
                    self.last_decision = ClusterType.ON_DEMAND
                    return ClusterType.ON_DEMAND
            
            self.last_decision = ClusterType.SPOT
            return ClusterType.SPOT
        else:
            # Spot not available - use on-demand if we were using spot
            if last_cluster_type == ClusterType.SPOT:
                # Spot was preempted - incur restart overhead
                self.overhead_remaining = self.restart_overhead
                self.last_decision = ClusterType.NONE
                return ClusterType.NONE
            
            # Otherwise continue with on-demand
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
