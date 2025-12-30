import argparse
from typing import List, Tuple
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.deadline_buffer = 0
        self.min_spot_percent = 0
        self.use_pause = False
        self.spot_history = []
        self.spot_availability = 0.0
        self.consecutive_spot_failures = 0
        self.last_decision = None
        self.restart_pending = 0
        self.work_remaining = 0
        self.time_remaining = 0
        self.emergency_mode = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_state(self, last_cluster_type: ClusterType, has_spot: bool):
        """Update internal state based on current situation"""
        # Update spot availability history
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
        
        # Calculate spot availability percentage
        if len(self.spot_history) > 0:
            self.spot_availability = sum(self.spot_history) / len(self.spot_history)
        
        # Track consecutive spot failures
        if not has_spot and last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = 0
        
        # Calculate remaining work and time
        if hasattr(self, 'task_duration') and hasattr(self, 'task_done_time'):
            completed = sum(end - start for start, end in self.task_done_time)
            self.work_remaining = self.task_duration - completed
            self.time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Check if we need emergency mode
        if hasattr(self, 'gap_seconds') and hasattr(self, 'restart_overhead'):
            time_per_step = self.env.gap_seconds
            needed_steps = self.work_remaining / time_per_step
            available_steps = self.time_remaining / time_per_step
            
            # Add buffer for restart overheads
            if self.restart_overhead > 0:
                needed_steps += self.restart_overhead / time_per_step * 2
            
            self.emergency_mode = needed_steps > available_steps * 0.8
            
        # Track restart overhead
        if last_cluster_type == ClusterType.NONE:
            if self.restart_pending > 0:
                self.restart_pending = max(0, self.restart_pending - self.env.gap_seconds)
        else:
            self.restart_pending = 0

    def _should_use_spot(self, has_spot: bool) -> bool:
        """Determine if we should use spot instances"""
        if not has_spot:
            return False
        
        if self.emergency_mode:
            return False
        
        # If spot availability is very low, be cautious
        if len(self.spot_history) > 20 and self.spot_availability < 0.3:
            return self.consecutive_spot_failures < 2
        
        # Normal conditions - use spot
        return True

    def _should_use_ondemand(self) -> bool:
        """Determine if we should use on-demand instances"""
        if self.emergency_mode:
            return True
        
        # Use on-demand if we've had too many consecutive spot failures
        if self.consecutive_spot_failures > 2:
            return True
        
        # Use on-demand if spot availability is very low
        if len(self.spot_history) > 20 and self.spot_availability < 0.2:
            return True
        
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state
        self._update_state(last_cluster_type, has_spot)
        
        # If we have pending restart overhead, pause
        if self.restart_pending > 0:
            return ClusterType.NONE
        
        # Determine which instance type to use
        if self._should_use_ondemand():
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.restart_pending = self.restart_overhead
            return ClusterType.ON_DEMAND
        
        if self._should_use_spot(has_spot):
            if last_cluster_type != ClusterType.SPOT:
                self.restart_pending = self.restart_overhead
            return ClusterType.SPOT
        
        # If neither spot nor on-demand is appropriate, pause
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)