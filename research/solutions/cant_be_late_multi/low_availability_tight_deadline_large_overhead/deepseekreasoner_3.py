import json
from argparse import Namespace
from typing import List
import heapq

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "adaptive_scheduler"

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
        self.spot_price = 0.9701 / 3600  # $/sec
        self.ondemand_price = 3.06 / 3600  # $/sec
        self.time_step = self.env.gap_seconds
        self.region_count = self.env.get_num_regions()
        self.region_history = [{"spot_available": False, "last_visited": -float('inf')} 
                               for _ in range(self.region_count)]
        self.current_region = 0
        self.consecutive_failures = 0
        self.safety_margin = 2 * self.restart_overhead  # 2 restart overheads
        self.min_ondemand_time = 0

        return self

    def _compute_metrics(self) -> tuple:
        """Compute current progress and time metrics."""
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_left = self.deadline - self.env.elapsed_seconds
        progress_ratio = work_done / self.task_duration if self.task_duration > 0 else 0
        
        # Effective remaining time considering overhead
        effective_time = time_left
        if self.remaining_restart_overhead > 0:
            effective_time -= self.remaining_restart_overhead
        
        return remaining_work, time_left, effective_time, progress_ratio

    def _should_use_ondemand(self, remaining_work: float, time_left: float, 
                            effective_time: float) -> bool:
        """Determine if we should switch to on-demand based on time constraints."""
        # Calculate minimum time needed with on-demand (considering overhead)
        min_needed = remaining_work
        if self.env.cluster_type != ClusterType.ON_DEMAND:
            min_needed += self.restart_overhead
        
        # Safety conditions for on-demand
        condition1 = time_left < remaining_work + self.safety_margin
        condition2 = effective_time < remaining_work * 1.2
        condition3 = (time_left / remaining_work < 1.5) and (remaining_work > 4 * self.time_step)
        condition4 = self.consecutive_failures > 3
        
        return condition1 or condition2 or condition3 or condition4

    def _find_best_region(self, current_idx: int, has_spot: bool) -> int:
        """Find the best region to switch to based on history and current state."""
        # If current region has spot and we want spot, stay
        if has_spot and self.env.cluster_type == ClusterType.SPOT:
            return current_idx
        
        # Check all regions for potential spot availability
        best_region = current_idx
        best_score = -float('inf')
        
        for region in range(self.region_count):
            if region == current_idx:
                continue
                
            # Score based on last visit time (prefer recently visited regions)
            last_visit = self.region_history[region]["last_visited"]
            score = -abs(self.env.elapsed_seconds - last_visit)
            
            # Slight preference for cycling through regions
            score += (region - current_idx) % self.region_count * 0.1
            
            if score > best_score:
                best_score = score
                best_region = region
        
        return best_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update region history
        current_region = self.env.get_current_region()
        self.region_history[current_region]["spot_available"] = has_spot
        self.region_history[current_region]["last_visited"] = self.env.elapsed_seconds
        
        # Compute current metrics
        remaining_work, time_left, effective_time, progress_ratio = self._compute_metrics()
        
        # Check if we've failed too many times recently
        if last_cluster_type == ClusterType.SPOT and not has_spot:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
        
        # If no work left or past deadline, do nothing
        if remaining_work <= 0 or time_left <= 0:
            return ClusterType.NONE
        
        # Handle restart overhead - wait if we have overhead remaining
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Check if we should use on-demand due to time pressure
        if self._should_use_ondemand(remaining_work, time_left, effective_time):
            if last_cluster_type != ClusterType.ON_DEMAND:
                # Switch to on-demand
                return ClusterType.ON_DEMAND
            else:
                # Continue with on-demand
                return ClusterType.ON_DEMAND
        
        # Try to use spot if available
        if has_spot:
            # We have time, so prefer spot
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            else:
                # Start spot if we're not already running it
                return ClusterType.SPOT
        else:
            # Spot not available, try to switch regions
            if time_left > remaining_work + self.restart_overhead + self.time_step:
                # We have time to switch regions
                best_region = self._find_best_region(current_region, has_spot)
                if best_region != current_region:
                    self.env.switch_region(best_region)
                    # After switching, wait for next step to check new region
                    return ClusterType.NONE
            
            # If we can't switch or don't have time, use on-demand as fallback
            if time_left < remaining_work + 2 * self.time_step:
                return ClusterType.ON_DEMAND
            
            # Otherwise wait and try again next step
            return ClusterType.NONE