import json
from argparse import Namespace
from typing import List, Tuple
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "adaptive_multi_region_scheduler"
    
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
        
        # Initialize strategy parameters
        self.spot_cost = 0.9701  # $/hr
        self.ondemand_cost = 3.06  # $/hr
        self.time_step = 3600.0  # seconds (1 hour)
        
        # State tracking
        self.region_history = {}
        self.last_action = None
        self.consecutive_failures = 0
        self.best_region = 0
        self.region_attempts = {}
        self.region_successes = {}
        
        return self
    
    def _calculate_time_pressure(self) -> float:
        """Calculate how much time pressure we're under (0-1 scale)."""
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        
        # Calculate minimum time needed with overhead
        if self.remaining_restart_overhead > 0:
            min_needed = remaining_work + self.remaining_restart_overhead
        else:
            min_needed = remaining_work + self.restart_overhead
        
        if min_needed <= 0:
            return 0.0
        
        time_ratio = remaining_time / min_needed
        # Normalize to 0-1, where >1 means we have slack, <1 means we're behind
        return max(0.0, min(1.0, time_ratio))
    
    def _find_best_spot_region(self) -> int:
        """Find the region with highest historical spot availability."""
        if not self.region_successes:
            return self.env.get_current_region()
        
        best_region = self.env.get_current_region()
        best_score = -1.0
        
        for region in range(self.env.get_num_regions()):
            attempts = self.region_attempts.get(region, 0)
            if attempts == 0:
                continue
            success_rate = self.region_successes.get(region, 0) / attempts
            # Penalize regions we've switched from recently to avoid thrashing
            penalty = 1.0
            if region != self.env.get_current_region():
                penalty = 0.8  # Slight penalty for switching
            
            score = success_rate * penalty
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        current_region = self.env.get_current_region()
        
        # Update region statistics
        if last_cluster_type == ClusterType.SPOT:
            self.region_attempts[current_region] = self.region_attempts.get(current_region, 0) + 1
            if has_spot:  # Spot was successful last time
                self.region_successes[current_region] = self.region_successes.get(current_region, 0) + 1
        
        # Calculate progress and time pressure
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        elapsed = self.env.elapsed_seconds
        remaining_time = self.deadline - elapsed
        
        time_pressure = self._calculate_time_pressure()
        
        # Emergency mode: if we're critically behind schedule
        if remaining_time < remaining_work + self.restart_overhead:
            # Use on-demand to guarantee progress
            if last_cluster_type != ClusterType.ON_DEMAND and self.remaining_restart_overhead == 0:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
        
        # If we have pending restart overhead, wait it out
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Strategic region switching
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_failures += 1
            # After 2 consecutive spot failures in this region, consider switching
            if self.consecutive_failures >= 2:
                best_region = self._find_best_spot_region()
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    self.consecutive_failures = 0
                    # After switching, start with on-demand for one step to avoid immediate failure
                    if time_pressure < 0.7:  # If we have some time
                        return ClusterType.ON_DEMAND
                    else:
                        return ClusterType.NONE
        else:
            self.consecutive_failures = 0
        
        # Decision logic based on time pressure
        if time_pressure > 0.8:  # Plenty of time
            if has_spot:
                return ClusterType.SPOT
            else:
                # Wait for spot to become available
                return ClusterType.NONE
        
        elif time_pressure > 0.5:  # Moderate time pressure
            if has_spot:
                # Use spot but be ready to switch if needed
                return ClusterType.SPOT
            else:
                # Try a different region
                best_region = self._find_best_spot_region()
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    return ClusterType.NONE
                else:
                    # Stay in current region but use on-demand
                    return ClusterType.ON_DEMAND
        
        else:  # High time pressure (time_pressure <= 0.5)
            if has_spot and time_pressure > 0.3:
                # Still try spot if available, but only if not too pressured
                return ClusterType.SPOT
            else:
                # Use on-demand to guarantee progress
                return ClusterType.ON_DEMAND
