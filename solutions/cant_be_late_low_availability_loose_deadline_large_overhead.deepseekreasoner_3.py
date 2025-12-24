import argparse
from typing import List
import math

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.safety_margin = None
        self.use_spot_until = None
        self.current_mode = None
        self.spot_unavailable_streak = 0

    def solve(self, spec_path: str) -> "Solution":
        # Read config parameters if needed
        # We'll compute safety margin based on task parameters
        # Safety margin = restart_overhead * safety_factor
        # We use a conservative safety factor of 3.0
        self.safety_factor = 3.0
        return self

    def _compute_safety_margin(self) -> float:
        """Compute safety margin based on restart overhead."""
        return self.restart_overhead * self.safety_factor

    def _get_remaining_work(self) -> float:
        """Calculate remaining work time needed."""
        if not self.task_done_time:
            return self.task_duration
        return self.task_duration - sum(self.task_done_time)

    def _get_remaining_time(self) -> float:
        """Calculate remaining time until deadline."""
        return self.deadline - self.env.elapsed_seconds

    def _get_min_time_needed(self) -> float:
        """Minimum time needed if using only on-demand."""
        return self._get_remaining_work()

    def _get_conservative_time_needed(self) -> float:
        """Conservative time estimate including restart overhead."""
        remaining_work = self._get_remaining_work()
        # Add one restart overhead as safety
        return remaining_work + self.restart_overhead

    def _get_aggressive_time_needed(self) -> float:
        """Aggressive time estimate assuming spot works perfectly."""
        return self._get_remaining_work()

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current state
        remaining_work = self._get_remaining_work()
        remaining_time = self._get_remaining_time()
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If we're out of time, use on-demand
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND
            
        # Calculate how much work we need to do per remaining time
        min_work_rate = remaining_work / remaining_time
        
        # Track spot availability streak
        if has_spot:
            self.spot_unavailable_streak = 0
        else:
            self.spot_unavailable_streak += 1
        
        # Safety margin calculation
        safety_margin = self._compute_safety_margin()
        
        # Determine if we're in critical mode (need to guarantee progress)
        critical_mode = False
        conservative_time = self._get_conservative_time_needed()
        
        # If conservative estimate shows we might miss deadline, go critical
        if conservative_time > remaining_time * 0.9:
            critical_mode = True
        # If work rate required is high, go critical
        elif min_work_rate > 0.8:  # Need to work >80% of time
            critical_mode = True
        # If spot has been unavailable for too long, go critical
        elif self.spot_unavailable_streak > 5:
            critical_mode = True
        
        # Strategy decision logic
        if critical_mode:
            # Critical: Use on-demand to guarantee progress
            return ClusterType.ON_DEMAND
        else:
            # Non-critical: Try to use spot when available
            if has_spot:
                # Use spot if available and we have enough safety margin
                # Check if we have enough time to absorb potential restart
                time_after_restart = remaining_time - self.restart_overhead
                if time_after_restart > remaining_work * 1.2:
                    return ClusterType.SPOT
                else:
                    # Not enough safety margin, use on-demand
                    return ClusterType.ON_DEMAND
            else:
                # Spot not available
                # Check if we can afford to wait
                # Calculate maximum wait time based on remaining slack
                slack = remaining_time - remaining_work
                max_wait = slack * 0.3  # Use up to 30% of slack for waiting
                
                if max_wait > self.env.gap_seconds:
                    # Can wait for spot to become available
                    return ClusterType.NONE
                else:
                    # Can't wait, use on-demand
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
