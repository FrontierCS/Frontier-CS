import math
from enum import Enum
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args=None):
        super().__init__(args)
        self.spot_history = []
        self.spot_availability = 0.0
        self.work_done = 0.0
        self.time_used = 0.0
        self.current_mode = "spot"  # "spot", "ondemand", "none"
        self.restart_remaining = 0.0
        self.critical_threshold = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_state(self, last_cluster_type, has_spot):
        gap = self.env.gap_seconds
        self.time_used += gap
        
        # Update work done
        if last_cluster_type == ClusterType.SPOT and has_spot:
            self.work_done += gap
        elif last_cluster_type == ClusterType.ON_DEMAND:
            self.work_done += gap
        # If restart overhead active, no work done
        
        # Update spot availability history
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
        self.spot_availability = sum(self.spot_history) / len(self.spot_history)
        
        # Update restart timer
        if self.restart_remaining > 0:
            self.restart_remaining = max(0, self.restart_remaining - gap)
        
        # Update critical threshold
        remaining_work = self.task_duration - self.work_done
        time_left = self.deadline - self.env.elapsed_seconds
        safe_time = remaining_work + self.restart_overhead
        
        # Dynamic threshold based on risk
        risk_factor = 1.2 + 0.5 * (1 - self.spot_availability)
        self.critical_threshold = safe_time * risk_factor

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_state(last_cluster_type, has_spot)
        
        gap = self.env.gap_seconds
        remaining_work = self.task_duration - self.work_done
        time_left = self.deadline - self.env.elapsed_seconds
        
        # If work is done, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # Check if we're in critical zone
        if time_left <= self.critical_threshold:
            # Critical zone: use on-demand if needed
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                # Check if we can finish with spot
                spot_time_needed = remaining_work / self.spot_availability if self.spot_availability > 0 else float('inf')
                if spot_time_needed <= time_left and has_spot:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
        
        # Non-critical zone
        # Handle restart overhead
        if self.restart_remaining > 0:
            # Continue with current cluster if possible
            if last_cluster_type == ClusterType.SPOT and has_spot:
                return ClusterType.SPOT
            elif last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            else:
                # Wait out restart
                return ClusterType.NONE
        
        # Normal operation
        if has_spot:
            # Use spot if available and not too risky
            risk_level = (self.critical_threshold - time_left) / self.critical_threshold
            spot_prob_needed = remaining_work / max(time_left, 0.1)
            
            if self.spot_availability >= spot_prob_needed * 0.8:
                return ClusterType.SPOT
            else:
                # Spot reliability too low, consider on-demand
                if time_left < remaining_work * 1.5:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.SPOT  # Try anyway, we have time
        else:
            # Spot unavailable
            if last_cluster_type == ClusterType.SPOT:
                # Just got preempted, start restart timer
                self.restart_remaining = self.restart_overhead
                return ClusterType.NONE
            else:
                # Wait for spot to return
                if time_left > self.critical_threshold * 1.5:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
