import argparse
import math
from typing import Optional, List
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.reset_state()
    
    def reset_state(self):
        """Reset internal state variables."""
        self.initialized = False
        self.strategy = None
        self.critical_time_threshold = 0
        self.conservative_threshold = 0
        self.spot_wait_counter = 0
        self.max_spot_wait = 0
        self.restart_timer = 0
        self.last_action = None
        self.work_done = 0
        self.time_spent = 0
        self.critical_phase = False
    
    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        self.reset_state()
        self.initialized = True
        
        # Set conservative thresholds based on problem parameters
        # Task: 48h work, Deadline: 70h, Slack: 22h
        # Convert hours to seconds for calculations (though we'll work in hours conceptually)
        total_slack = 22  # hours
        restart_overhead_hours = 0.05  # 3 minutes
        
        # Conservative strategy: switch to on-demand when we have less than 
        # (remaining_work + safety_margin) time left
        # Safety margin accounts for potential spot preemptions
        self.critical_time_threshold = 10  # hours before deadline to be in critical mode
        self.conservative_threshold = 5   # hours before deadline to switch to OD only
        
        # Maximum consecutive time to wait for spot before switching to on-demand
        self.max_spot_wait = 2  # hours
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.
        """
        if not self.initialized:
            # Initialize on first step
            self.solve("")
        
        # Track work progress
        if last_cluster_type in [ClusterType.SPOT, ClusterType.ON_DEMAND]:
            self.work_done += self.env.gap_seconds / 3600  # Convert seconds to hours
        
        self.time_spent = self.env.elapsed_seconds / 3600  # hours
        
        # Calculate remaining work and time
        remaining_work = self.task_duration / 3600 - self.work_done  # hours
        remaining_time = self.deadline / 3600 - self.time_spent  # hours
        
        # Check if we're in critical phase (approaching deadline)
        self.critical_phase = remaining_time < self.critical_time_threshold
        
        # Update restart timer
        if self.restart_timer > 0:
            self.restart_timer -= self.env.gap_seconds / 3600
        
        # If we just restarted (preempted), set restart timer
        if (last_cluster_type == ClusterType.SPOT and not has_spot and 
            self.last_action == ClusterType.SPOT):
            self.restart_timer = self.restart_overhead / 3600  # hours
            self.spot_wait_counter = 0
        
        # Decision logic
        action = self._make_decision(remaining_work, remaining_time, has_spot)
        
        # Update state
        self.last_action = action
        
        # If we're choosing spot but none is available, we must choose something else
        if action == ClusterType.SPOT and not has_spot:
            # Wait for spot if we have time, otherwise use on-demand
            if (remaining_time > remaining_work * 1.5 and 
                self.spot_wait_counter < self.max_spot_wait):
                self.spot_wait_counter += self.env.gap_seconds / 3600
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
        
        # Reset spot wait counter if we're using spot
        if action == ClusterType.SPOT:
            self.spot_wait_counter = 0
        
        return action
    
    def _make_decision(self, remaining_work: float, remaining_time: float, 
                      has_spot: bool) -> ClusterType:
        """
        Core decision logic.
        """
        # Emergency: must use on-demand to meet deadline
        if remaining_time <= remaining_work + 0.1:  # Less than 6 minutes buffer
            return ClusterType.ON_DEMAND
        
        # Critical phase: less conservative threshold
        if remaining_time < self.conservative_threshold:
            # In critical phase, prefer on-demand but use spot if available
            # and we have some buffer
            if has_spot and remaining_time > remaining_work * 1.2:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # Normal phase: optimize for cost
        if has_spot:
            # Use spot if we have buffer for potential preemptions
            # Buffer accounts for restart overhead and spot unavailability
            required_buffer = remaining_work * 0.3 + 0.5  # 30% + 0.5h buffer
            
            if remaining_time > remaining_work + required_buffer:
                # We have enough buffer to use spot
                return ClusterType.SPOT
            elif remaining_time > remaining_work * 1.1:
                # Moderate buffer - use spot cautiously
                if self.restart_timer <= 0:  # Not in restart overhead
                    return ClusterType.SPOT
                else:
                    # In restart overhead, use on-demand to avoid wasting time
                    return ClusterType.ON_DEMAND
            else:
                # Insufficient buffer, use on-demand
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if remaining_time > remaining_work * 1.5:
                # We have time to wait for spot
                return ClusterType.NONE
            else:
                # Running out of time, use on-demand
                return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
