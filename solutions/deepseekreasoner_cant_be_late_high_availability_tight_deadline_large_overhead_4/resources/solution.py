import argparse
from enum import Enum
import math
from typing import List, Optional

# These imports would be available in the evaluation environment
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"
    
    def __init__(self, args):
        super().__init__()
        self.args = args
        self._restart_timer = 0
        self._current_cluster = None
        self._work_done = 0.0
        self._time_elapsed = 0.0
        self._cost = 0.0
        self._spot_price = 0.97 / 3600  # $/sec
        self._od_price = 3.06 / 3600  # $/sec
        self._last_spot_available = False
        
    def solve(self, spec_path: str) -> "Solution":
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state
        self._time_elapsed += self.env.gap_seconds
        self._last_spot_available = has_spot
        self._current_cluster = last_cluster_type
        
        # Track restart overhead
        if self._restart_timer > 0:
            self._restart_timer = max(0, self._restart_timer - self.env.gap_seconds)
        
        # Update work done
        if last_cluster_type == ClusterType.SPOT and has_spot:
            if self._restart_timer <= 0:
                self._work_done += self.env.gap_seconds
                self._cost += self.env.gap_seconds * self._spot_price
        elif last_cluster_type == ClusterType.ON_DEMAND:
            if self._restart_timer <= 0:
                self._work_done += self.env.gap_seconds
                self._cost += self.env.gap_seconds * self._od_price
        
        # Check if we're done
        if self._work_done >= self.task_duration:
            return ClusterType.NONE
        
        # Calculate remaining work and time
        remaining_work = self.task_duration - self._work_done
        remaining_time = self.deadline - self._time_elapsed
        
        # If we can't finish even with OD due to restart overhead, go OD immediately
        if remaining_time - self.restart_overhead < remaining_work:
            # In restart overhead period
            if self._restart_timer > 0:
                # Wait out restart if we're in middle of it
                return ClusterType.NONE
            else:
                # Switch to OD if we need to
                if last_cluster_type != ClusterType.ON_DEMAND:
                    self._restart_timer = self.restart_overhead
                return ClusterType.ON_DEMAND
        
        # Calculate safe threshold
        # Be more conservative as deadline approaches
        time_safety_margin = max(2.0 * self.restart_overhead, 3600)  # At least 1 hour or 2x restart overhead
        critical_ratio = remaining_work / max(remaining_time - time_safety_margin, 0.1)
        
        # If we're getting close to deadline or work is accumulating, use OD
        if critical_ratio > 0.8:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._restart_timer = self.restart_overhead
            return ClusterType.ON_DEMAND
        
        # Use spot when available and we're not in restart
        if has_spot and self._restart_timer <= 0:
            # Only switch to spot if we were on OD or NONE and it's worth it
            if last_cluster_type != ClusterType.SPOT:
                self._restart_timer = self.restart_overhead
            return ClusterType.SPOT
        
        # If spot not available and we're not critical, wait
        if not has_spot and critical_ratio < 0.6:
            return ClusterType.NONE
        
        # Otherwise use OD
        if last_cluster_type != ClusterType.ON_DEMAND:
            self._restart_timer = self.restart_overhead
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
