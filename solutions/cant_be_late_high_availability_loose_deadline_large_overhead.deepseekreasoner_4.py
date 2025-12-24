import sys
import math
from typing import List, Tuple, Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_threshold"
    
    def __init__(self, args):
        super().__init__(args)
        self.config = {}
        self.restart_progress = 0.0
        self.spot_streak = 0
        self.consecutive_spot_failures = 0
        self.last_decision = ClusterType.NONE
        self.work_done_history = []
        self.time_history = []
        
    def solve(self, spec_path: str) -> "Solution":
        # Read any configuration from spec_path if needed
        try:
            import json
            with open(spec_path, 'r') as f:
                self.config = json.load(f)
        except:
            self.config = {}
        return self
    
    def _estimate_work_left(self) -> float:
        """Calculate remaining work needed."""
        work_done = 0.0
        for start, end, _ in self.task_done_time:
            work_done += (end - start)
        return max(0.0, self.task_duration - work_done)
    
    def _calculate_safe_threshold(self, work_left: float, time_left: float) -> float:
        """Calculate safety threshold based on remaining work and time."""
        # Base threshold: work_left / time_left ratio
        if time_left <= 0:
            return 1.0
        
        base_ratio = work_left / time_left
        
        # Add safety margin based on spot reliability
        # If we've had recent failures, be more conservative
        if self.consecutive_spot_failures > 0:
            safety_margin = 0.15 + 0.05 * min(self.consecutive_spot_failures, 5)
        else:
            safety_margin = 0.1
            
        # Adjust based on remaining time buffer
        time_buffer = time_left - work_left
        if time_buffer < self.restart_overhead * 2:
            safety_margin += 0.2
        elif time_buffer < self.restart_overhead * 4:
            safety_margin += 0.1
            
        return min(0.9, base_ratio + safety_margin)
    
    def _should_use_spot(self, work_left: float, time_left: float, has_spot: bool) -> bool:
        """Determine if we should use spot instances."""
        if not has_spot:
            return False
            
        if work_left <= 0:
            return False
            
        # If we're in restart overhead period, continue waiting
        if self.restart_progress > 0:
            return False
            
        # Critical time: switch to on-demand if we're running out of time
        critical_time = work_left + self.restart_overhead * 2
        if time_left <= critical_time:
            return False
            
        # Calculate safety threshold
        threshold = self._calculate_safe_threshold(work_left, time_left)
        
        # Current progress ratio
        current_ratio = work_left / time_left if time_left > 0 else 1.0
        
        # Use spot if we're ahead of schedule or have good margin
        if current_ratio <= threshold:
            # Check if we've had too many consecutive failures
            if self.consecutive_spot_failures >= 3:
                # After 3 consecutive failures, be more conservative
                return current_ratio <= threshold * 0.7
            return True
            
        return False
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update restart progress
        if last_cluster_type != ClusterType.SPOT and self.last_decision == ClusterType.SPOT:
            # We attempted spot but got interrupted or switched
            self.restart_progress = self.restart_overhead
            self.consecutive_spot_failures += 1
            self.spot_streak = 0
        elif last_cluster_type == ClusterType.SPOT and self.last_decision == ClusterType.SPOT:
            # Successfully used spot
            self.restart_progress = max(0.0, self.restart_progress - self.env.gap_seconds)
            self.consecutive_spot_failures = 0
            self.spot_streak += 1
        else:
            # Using on-demand or none
            self.restart_progress = max(0.0, self.restart_progress - self.env.gap_seconds)
            
        # Calculate current state
        work_left = self._estimate_work_left()
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Store history for debugging
        self.work_done_history.append(work_left)
        self.time_history.append(time_left)
        
        # Check if we've completed the work
        if work_left <= 0:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
            
        # Check if we're in restart overhead
        if self.restart_progress > 0:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
            
        # Determine which cluster type to use
        if self._should_use_spot(work_left, time_left, has_spot):
            self.last_decision = ClusterType.SPOT
            return ClusterType.SPOT
        else:
            # Use on-demand only if we have work to do and it's safe
            if work_left > 0 and time_left > 0:
                self.last_decision = ClusterType.ON_DEMAND
                return ClusterType.ON_DEMAND
            else:
                self.last_decision = ClusterType.NONE
                return ClusterType.NONE
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
