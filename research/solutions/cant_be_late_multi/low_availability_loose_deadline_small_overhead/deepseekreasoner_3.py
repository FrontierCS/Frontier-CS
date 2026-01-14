import json
from argparse import Namespace
import heapq
from typing import List, Tuple, Optional, Dict
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "optimized_multi_region"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)
        
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Precompute cost parameters
        self.spot_price = 0.9701  # $/hr
        self.on_demand_price = 3.06  # $/hr
        self.hour_seconds = 3600
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Get current state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate progress
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - elapsed
        
        # If no work remaining, do nothing
        if work_remaining <= 0:
            return ClusterType.NONE
        
        # Calculate critical time
        # Minimum time needed if using only on-demand (no overhead)
        min_time_needed = work_remaining
        
        # If we're already too late, use on-demand as last resort
        if time_remaining < min_time_needed:
            return ClusterType.ON_DEMAND
        
        # Calculate safe threshold: time when we must switch to on-demand
        # Account for potential overhead when switching
        overhead_buffer = self.restart_overhead
        safe_threshold = work_remaining + overhead_buffer
        
        # If we're in the critical zone, use on-demand
        if time_remaining <= safe_threshold * 1.5:
            return ClusterType.ON_DEMAND
        
        # Calculate cost efficiency metrics
        spot_cost_per_second = self.spot_price / self.hour_seconds
        ondemand_cost_per_second = self.on_demand_price / self.hour_seconds
        
        # Estimate probability of spot success based on recent history
        # (simplified: assume spots are generally available unless we just failed)
        spot_available = has_spot
        
        # If spot is available and we're not in critical zone, use spot
        if spot_available and last_cluster_type == ClusterType.SPOT:
            return ClusterType.SPOT
        elif spot_available:
            # Consider switching to spot if we're not on spot already
            # But only if we have time for potential overhead
            time_for_overhead = time_remaining - work_remaining - self.restart_overhead
            if time_for_overhead > 0:
                return ClusterType.SPOT
            else:
                # Stick with current type to avoid overhead
                if last_cluster_type == ClusterType.ON_DEMAND:
                    return ClusterType.ON_DEMAND
                else:
                    return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
        else:
            # No spot available in current region
            # Try switching regions if we have multiple regions
            if num_regions > 1:
                # Simple round-robin region switching
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
            
            # After switching (or if only one region), use on-demand
            # but check if we should pause instead
            
            # Consider pausing only if we have plenty of time
            # and spot might become available soon
            if time_remaining > work_remaining * 2.0:
                # Small chance to pause and wait for spot
                # This helps reduce cost when we have time
                if elapsed % (gap * 3) < gap:  # Pause every 3rd step occasionally
                    return ClusterType.NONE
            
            return ClusterType.ON_DEMAND