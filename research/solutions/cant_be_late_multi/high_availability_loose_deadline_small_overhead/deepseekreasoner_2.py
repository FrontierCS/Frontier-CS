import json
from argparse import Namespace
from typing import List, Tuple
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        
        # Initialize strategy state
        self.remaining_work = self.task_duration
        self.current_region = 0
        self.time_elapsed = 0.0
        self.strategy_initialized = False
        self.spot_price = 0.9701 / 3600  # per second
        self.on_demand_price = 3.06 / 3600  # per second
        self.gap_seconds = 3600.0  # Default, will be updated
        
        # Statistics for each region
        self.region_stats = {}
        
        return self

    def _update_state(self, last_cluster_type: ClusterType, has_spot: bool) -> None:
        """Update internal state based on environment."""
        if not self.strategy_initialized:
            self.gap_seconds = self.env.gap_seconds
            self.num_regions = self.env.get_num_regions()
            for i in range(self.num_regions):
                self.region_stats[i] = {
                    'spot_available': 0,
                    'total_steps': 0,
                    'last_spot_check': -1
                }
            self.strategy_initialized = True
        
        self.current_region = self.env.get_current_region()
        self.time_elapsed = self.env.elapsed_seconds
        self.remaining_work = self.task_duration - sum(self.task_done_time)
        
        # Update region statistics
        stats = self.region_stats[self.current_region]
        stats['total_steps'] += 1
        if has_spot:
            stats['spot_available'] += 1
        stats['last_spot_check'] = self.time_elapsed

    def _calculate_spot_probability(self, region: int) -> float:
        """Calculate probability of spot availability in a region."""
        stats = self.region_stats[region]
        if stats['total_steps'] == 0:
            return 0.5  # Default assumption
        return stats['spot_available'] / stats['total_steps']

    def _find_best_region(self, has_spot: bool) -> int:
        """Find the best region to switch to based on historical spot availability."""
        best_region = self.current_region
        best_prob = self._calculate_spot_probability(self.current_region)
        
        for region in range(self.num_regions):
            if region == self.current_region:
                continue
            prob = self._calculate_spot_probability(region)
            if prob > best_prob:
                best_prob = prob
                best_region = region
        
        # If current region has spot, stay unless another region is significantly better
        if has_spot and best_prob - best_prob * 0.2 < self._calculate_spot_probability(self.current_region):
            return self.current_region
        
        return best_region

    def _calculate_time_pressure(self) -> float:
        """Calculate time pressure factor (0 to 1)."""
        time_remaining = self.deadline - self.time_elapsed
        time_needed = self.remaining_work
        
        # If we're in restart overhead, add it to time needed
        if self.remaining_restart_overhead > 0:
            time_needed += self.remaining_restart_overhead
        
        safety_margin = self.gap_seconds * 2  # 2 steps of safety margin
        
        if time_remaining <= 0:
            return 1.0
        
        if time_needed + safety_margin >= time_remaining:
            return 1.0
        
        return max(0.0, (time_needed + safety_margin) / time_remaining)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_state(last_cluster_type, has_spot)
        
        # If work is done, return NONE
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # Calculate time pressure
        time_pressure = self._calculate_time_pressure()
        
        # If we have restart overhead pending, we can't do work
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # High time pressure: use on-demand to guarantee completion
        if time_pressure > 0.8:
            # Check if we need to switch to on-demand
            if last_cluster_type != ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # Medium time pressure: be more conservative
        elif time_pressure > 0.5:
            if has_spot:
                # Only use spot if we have good probability in this region
                spot_prob = self._calculate_spot_probability(self.current_region)
                if spot_prob > 0.7:  # High confidence in spot availability
                    return ClusterType.SPOT
                else:
                    # Try to find a better region
                    best_region = self._find_best_region(has_spot)
                    if best_region != self.current_region:
                        self.env.switch_region(best_region)
                        return ClusterType.NONE
                    else:
                        return ClusterType.ON_DEMAND
            else:
                # No spot available, try to find a region with spot
                best_region = self._find_best_region(has_spot)
                if best_region != self.current_region:
                    self.env.switch_region(best_region)
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
        
        # Low time pressure: aggressive spot usage
        else:
            if has_spot:
                return ClusterType.SPOT
            else:
                # Try to find a region with spot
                best_region = self._find_best_region(has_spot)
                if best_region != self.current_region:
                    self.env.switch_region(best_region)
                    return ClusterType.NONE
                else:
                    # If no region has good spot probability, use on-demand
                    spot_prob = self._calculate_spot_probability(self.current_region)
                    if spot_prob < 0.3:
                        return ClusterType.ON_DEMAND
                    else:
                        return ClusterType.NONE