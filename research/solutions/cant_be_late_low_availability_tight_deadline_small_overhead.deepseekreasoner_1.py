import argparse
import math
from enum import Enum
from typing import List, Optional, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "adaptive_threshold"
    
    def __init__(self, args):
        super().__init__(args)
        self._emergency_mode = False
        self._spot_unavailable_streak = 0
        self._consecutive_spot_uses = 0
        self._last_action = ClusterType.NONE
        self._initialized = False
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._initialized = True
            self._last_action = last_cluster_type
        
        # Calculate progress metrics
        completed_work = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - completed_work
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        # Check if we're in emergency mode (must use on-demand to finish)
        if remaining_time <= remaining_work + self.restart_overhead * 2:
            self._emergency_mode = True
        
        # If in emergency mode, use on-demand exclusively
        if self._emergency_mode:
            self._last_action = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Update streaks
        if last_cluster_type == ClusterType.SPOT:
            self._consecutive_spot_uses += 1
            self._spot_unavailable_streak = 0
        else:
            self._consecutive_spot_uses = 0
        
        if not has_spot:
            self._spot_unavailable_streak += 1
        else:
            self._spot_unavailable_streak = 0
        
        # Calculate safe threshold based on remaining slack
        slack = self.deadline - self.task_duration - elapsed
        safe_threshold = max(1, min(10, int(slack / (self.restart_overhead * 2))))
        
        # If we've had too many consecutive spot uses, be cautious
        if self._consecutive_spot_uses > 20 and has_spot:
            # Take a break to avoid potential preemptions
            self._last_action = ClusterType.NONE
            return ClusterType.NONE
        
        # If spot has been unavailable for too long, consider switching
        if self._spot_unavailable_streak > safe_threshold and remaining_work > 0:
            # Calculate if we can still finish with spot interruptions
            estimated_spot_time = remaining_work + (
                self.restart_overhead * max(1, remaining_work / (self.env.gap_seconds * 10))
            )
            
            if estimated_spot_time > remaining_time * 0.8:
                self._last_action = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        
        # Main decision logic
        if has_spot:
            # Use spot if we have good progress margin
            progress_ratio = completed_work / self.task_duration
            time_ratio = elapsed / self.deadline
            
            if progress_ratio > time_ratio * 1.1:  # Ahead of schedule
                self._last_action = ClusterType.SPOT
                return ClusterType.SPOT
            elif remaining_time > remaining_work * 1.5:  # Plenty of time
                self._last_action = ClusterType.SPOT
                return ClusterType.SPOT
            else:
                # Conservative: use on-demand when time is tight
                self._last_action = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
        else:
            # Spot not available
            if self._last_action == ClusterType.SPOT:
                # Just lost spot, wait a bit to see if it comes back
                if self._spot_unavailable_streak <= 2:
                    self._last_action = ClusterType.NONE
                    return ClusterType.NONE
                else:
                    self._last_action = ClusterType.ON_DEMAND
                    return ClusterType.ON_DEMAND
            else:
                self._last_action = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND