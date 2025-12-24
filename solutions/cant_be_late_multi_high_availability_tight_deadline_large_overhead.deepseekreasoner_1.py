import json
from argparse import Namespace
from typing import List, Tuple
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

    def __init__(self, args):
        super().__init__(args)
        self.spot_price = 0.9701
        self.ondemand_price = 3.06
        self.region_history = []
        self.spot_availability = []
        self.last_decision = None
        self.consecutive_failures = 0
        self.best_regions = []
        self.initialized = False
        self.remaining_work_history = []
        self.time_history = []
        self.region_switch_counter = 0
        self.last_spot_availability = {}

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)
        
        # Initialize data structures
        self.region_history = []
        self.spot_availability = []
        self.last_decision = None
        self.consecutive_failures = 0
        self.best_regions = []
        self.initialized = False
        self.remaining_work_history = []
        self.time_history = []
        self.region_switch_counter = 0
        self.last_spot_availability = {}
        
        return self

    def _get_remaining_work(self) -> float:
        """Calculate remaining work in seconds."""
        return max(0, self.task_duration - sum(self.task_done_time))

    def _get_remaining_time(self) -> float:
        """Calculate remaining time until deadline in seconds."""
        return max(0, self.deadline - self.env.elapsed_seconds)

    def _get_time_pressure(self) -> float:
        """Calculate time pressure ratio."""
        remaining_work = self._get_remaining_work()
        remaining_time = self._get_remaining_time()
        
        if remaining_time <= 0:
            return float('inf')
        if remaining_work <= 0:
            return 0
        
        # Account for potential restart overhead
        effective_time = remaining_time - self.restart_overhead
        if effective_time <= 0:
            return float('inf')
        
        return remaining_work / effective_time

    def _should_use_ondemand(self) -> bool:
        """Determine if we should switch to on-demand based on time pressure."""
        time_pressure = self._get_time_pressure()
        
        # If time pressure is very high, use on-demand
        if time_pressure > 1.5:
            return True
        
        # If we're very close to deadline
        remaining_time = self._get_remaining_time()
        remaining_work = self._get_remaining_work()
        
        # If we can't finish with spot even without interruptions
        if remaining_time < remaining_work + self.restart_overhead:
            return True
        
        # If we've had too many consecutive failures
        if self.consecutive_failures > 3:
            return True
            
        return False

    def _find_best_region(self, current_region: int, has_spot: bool) -> int:
        """Find the best region to switch to."""
        num_regions = self.env.get_num_regions()
        
        # Initialize spot availability tracking
        if not hasattr(self, 'region_spot_stats'):
            self.region_spot_stats = [{'hits': 1, 'total': 1} for _ in range(num_regions)]
        
        # Update current region stats
        if has_spot:
            self.region_spot_stats[current_region]['hits'] += 1
        self.region_spot_stats[current_region]['total'] += 1
        
        # Calculate availability scores
        scores = []
        for i in range(num_regions):
            if i == current_region:
                continue
                
            stats = self.region_spot_stats[i]
            if stats['total'] > 0:
                availability = stats['hits'] / stats['total']
            else:
                availability = 0.5  # Default assumption
            
            # Penalize frequent switching
            switch_penalty = 0.1 if self.region_switch_counter > 10 else 0
            
            score = availability - switch_penalty
            scores.append((score, i))
        
        if not scores:
            return current_region
        
        # Return region with highest score
        scores.sort(reverse=True)
        return scores[0][1]

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Calculate key metrics
        remaining_work = self._get_remaining_work()
        remaining_time = self._get_remaining_time()
        time_pressure = self._get_time_pressure()
        
        # If work is done, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
        
        # If no time left, try anything
        if remaining_time <= 0:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        current_region = self.env.get_current_region()
        
        # Update failure counter
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
        
        # Check if we should use on-demand due to time pressure
        if self._should_use_ondemand():
            # If switching from spot to on-demand in same region
            if last_cluster_type != ClusterType.ON_DEMAND:
                self.consecutive_failures = 0
            return ClusterType.ON_DEMAND
        
        # Try to use spot if available
        if has_spot:
            self.consecutive_failures = 0
            
            # If we were using on-demand, consider switching back to spot
            if last_cluster_type == ClusterType.ON_DEMAND:
                # Only switch if we have enough time buffer
                if time_pressure < 0.8:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            
            return ClusterType.SPOT
        
        # Spot not available in current region
        # Consider switching regions if we have time
        if remaining_time > remaining_work + 2 * self.restart_overhead:
            # Only switch if we haven't switched too much recently
            if self.region_switch_counter < 5 or time_pressure < 0.7:
                best_region = self._find_best_region(current_region, has_spot)
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self.region_switch_counter += 1
                    # After switching, wait one step to assess new region
                    return ClusterType.NONE
        
        # If we can't switch or don't want to, wait for spot
        return ClusterType.NONE
