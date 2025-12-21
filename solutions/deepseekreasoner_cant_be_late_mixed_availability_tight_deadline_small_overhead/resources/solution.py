import os
import json
from enum import Enum
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_spot_optimizer"
    
    def __init__(self, args):
        super().__init__(args)
        self.config = None
        self.safety_factor = 0.85  # Conservative factor for deadline
        self.on_demand_threshold = 0.92  # When to switch to on-demand
        self.consecutive_spot_failures = 0
        self.spot_history = []
        self.last_decision = ClusterType.NONE
        self.restart_timer = 0
        
    def solve(self, spec_path: str) -> "Solution":
        if os.path.exists(spec_path):
            with open(spec_path, 'r') as f:
                self.config = json.load(f)
        return self
    
    def _get_remaining_work(self):
        return self.task_duration - sum(self.task_done_time)
    
    def _get_time_remaining(self):
        return self.deadline - self.env.elapsed_seconds
    
    def _get_progress_rate_needed(self):
        remaining_work = self._get_remaining_work()
        time_remaining = self._get_time_remaining()
        if time_remaining <= 0:
            return float('inf')
        return remaining_work / time_remaining
    
    def _should_use_on_demand(self, progress_rate_needed):
        # Use on-demand if we're falling behind schedule
        if progress_rate_needed > self.on_demand_threshold:
            return True
        
        # Use on-demand if we have very little time left
        time_remaining = self._get_time_remaining()
        if time_remaining < 2 * self.restart_overhead:
            return True
        
        # Use on-demand after too many consecutive spot failures
        if self.consecutive_spot_failures > 5:
            return True
            
        return False
    
    def _update_spot_history(self, has_spot):
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
    
    def _get_spot_reliability(self):
        if not self.spot_history:
            return 0.5
        return sum(self.spot_history) / len(self.spot_history)
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_spot_history(has_spot)
        
        # Update restart timer
        if self.restart_timer > 0:
            self.restart_timer -= self.env.gap_seconds
            if self.restart_timer < 0:
                self.restart_timer = 0
        
        # Track consecutive spot failures
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_spot_failures += 1
        else:
            self.consecutive_spot_failures = max(0, self.consecutive_spot_failures - 1)
        
        # Calculate progress metrics
        progress_rate_needed = self._get_progress_rate_needed()
        remaining_work = self._get_remaining_work()
        time_remaining = self._get_time_remaining()
        
        # Safety check: if we can't possibly finish, use on-demand
        min_time_needed = remaining_work + (0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead)
        if min_time_needed > time_remaining:
            return ClusterType.ON_DEMAND
        
        # Check if we should use on-demand
        if self._should_use_on_demand(progress_rate_needed):
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # If spot is available and we're not in critical path, use it
        if has_spot:
            # Check if we're switching to spot and need restart
            if last_cluster_type != ClusterType.SPOT and self.restart_timer <= 0:
                self.restart_timer = self.restart_overhead
            
            self.last_decision = ClusterType.SPOT
            return ClusterType.SPOT
        
        # If spot not available and we're ahead of schedule, wait
        if progress_rate_needed < self.safety_factor * 0.7:
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
        
        # Otherwise use on-demand
        self.last_decision = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND
    
    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
