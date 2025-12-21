import os
import pickle
import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "solution"

    def solve(self, spec_path: str) -> "Solution":
        # Read spec to get constants if needed
        if os.path.exists(spec_path):
            with open(spec_path, 'rb') as f:
                spec = pickle.load(f)
                # Store task duration, deadline, prices if needed
                self.task_duration = spec.get('task_duration_seconds', 48 * 3600)
                self.deadline = spec.get('deadline_seconds', 70 * 3600)
                self.restart_overhead = spec.get('restart_overhead_seconds', 180)
                self.od_price = spec.get('on_demand_price_per_second', 3.06 / 3600)
                self.spot_price = spec.get('spot_price_per_second', 0.97 / 3600)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        gap = self.env.gap_seconds
        remaining_work = self.task_duration - sum(self.task_done_time)
        
        # If no work left, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # Calculate minimum time needed
        min_time_needed = remaining_work
        if last_cluster_type != ClusterType.SPOT:
            min_time_needed += self.restart_overhead
            
        # Emergency mode: if we risk missing deadline, use on-demand
        safety_margin = 3600  # 1 hour safety margin
        if time_left - safety_margin < min_time_needed:
            return ClusterType.ON_DEMAND
        
        # Calculate aggressive threshold based on remaining time
        # Use more aggressive spot usage when we have plenty of time
        time_ratio = time_left / (self.deadline - self.task_duration + 1e-9)
        spot_prob_threshold = 0.15 + 0.25 * (1 - time_ratio)
        
        # If spot is available and we're not in restart overhead, use it
        if (has_spot and last_cluster_type != ClusterType.NONE and 
            elapsed % 3600 < 3540):  # Avoid switching near hour boundaries
            # Occasionally check if we should switch to on-demand
            # based on remaining time and progress
            progress_ratio = sum(self.task_done_time) / self.task_duration
            if progress_ratio < 0.8 or time_ratio > 0.3:
                return ClusterType.SPOT
        
        # If we recently had spot and it's gone, wait a bit
        if (last_cluster_type == ClusterType.SPOT and not has_spot and
            elapsed % 600 < 540):  # Wait up to 10 minutes
            return ClusterType.NONE
            
        # Default to on-demand if spot not available or we're being conservative
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
