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
        
        # Initialize state
        self.work_done = 0.0
        self.last_decision = None
        self.last_region = None
        self.spot_unavailable_count = 0
        self.consecutive_spot = 0
        self.region_stats = {}
        self.min_spot_price = 0.9701
        self.ondemand_price = 3.06
        
        return self
    
    def _get_remaining_time(self) -> float:
        """Calculate remaining time until deadline."""
        return self.deadline - self.env.elapsed_seconds
    
    def _get_progress(self) -> float:
        """Get current progress percentage."""
        return sum(self.task_done_time) / self.task_duration[0]
    
    def _get_time_pressure(self) -> float:
        """Calculate time pressure factor (0 to 1)."""
        remaining_time = self._get_remaining_time()
        remaining_work = self.task_duration[0] - sum(self.task_done_time)
        
        if remaining_time <= 0:
            return 1.0
        
        # Add buffer for overheads and safety
        time_needed = remaining_work + self.restart_overhead[0] * 2
        pressure = min(1.0, max(0.0, 1.0 - (remaining_time - time_needed) / self.deadline))
        return pressure
    
    def _should_switch_to_ondemand(self, has_spot: bool) -> bool:
        """Determine if we should switch to on-demand based on current state."""
        remaining_time = self._get_remaining_time()
        remaining_work = self.task_duration[0] - sum(self.task_done_time)
        time_pressure = self._get_time_pressure()
        
        # Critical: if we might miss deadline even with spot
        min_time_with_spot = remaining_work + self.restart_overhead[0]
        
        # High time pressure forces on-demand
        if time_pressure > 0.7:
            return True
        
        # If spot has been unavailable repeatedly
        if self.spot_unavailable_count > 3:
            return True
        
        # If we're close to deadline and still have significant work
        if remaining_time < min_time_with_spot * 1.5:
            return True
        
        # If remaining time is very tight
        safety_margin = self.restart_overhead[0] * 4
        if remaining_time < remaining_work + safety_margin:
            return True
        
        return False
    
    def _find_best_region(self, current_region: int, has_spot: bool) -> Tuple[int, bool]:
        """Find the best region to switch to."""
        num_regions = self.env.get_num_regions()
        best_region = current_region
        best_has_spot = has_spot
        
        # Simple strategy: try next region if current has no spot
        if not has_spot:
            next_region = (current_region + 1) % num_regions
            return next_region, False  # We don't know if next has spot
        
        return current_region, has_spot
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Track spot availability
        if not has_spot:
            self.spot_unavailable_count += 1
        else:
            self.spot_unavailable_count = 0
        
        # Track consecutive spot usage
        if last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot += 1
        else:
            self.consecutive_spot = 0
        
        current_region = self.env.get_current_region()
        
        # Update region stats
        if current_region not in self.region_stats:
            self.region_stats[current_region] = {"spot_count": 0, "total_steps": 0}
        self.region_stats[current_region]["total_steps"] += 1
        if has_spot:
            self.region_stats[current_region]["spot_count"] += 1
        
        # Check if we're done
        if sum(self.task_done_time) >= self.task_duration[0]:
            return ClusterType.NONE
        
        # Calculate time pressure
        time_pressure = self._get_time_pressure()
        remaining_time = self._get_remaining_time()
        remaining_work = self.task_duration[0] - sum(self.task_done_time)
        
        # Emergency: if we're about to miss deadline
        if remaining_time < remaining_work:
            # Switch to on-demand and stay there
            return ClusterType.ON_DEMAND
        
        # Decision logic
        if self._should_switch_to_ondemand(has_spot):
            # Consider region switch if current region has poor spot availability
            if current_region in self.region_stats:
                spot_ratio = (self.region_stats[current_region]["spot_count"] / 
                            max(1, self.region_stats[current_region]["total_steps"]))
                if spot_ratio < 0.5 and time_pressure < 0.8:
                    # Try another region before committing to on-demand
                    num_regions = self.env.get_num_regions()
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                    return ClusterType.ON_DEMAND
            
            return ClusterType.ON_DEMAND
        
        # Use spot when available and not under high time pressure
        if has_spot:
            # Occasionally switch regions to explore
            if (self.consecutive_spot > 10 and 
                time_pressure < 0.3 and 
                len(self.region_stats) < self.env.get_num_regions()):
                # Explore unused regions
                for i in range(self.env.get_num_regions()):
                    if i not in self.region_stats or self.region_stats[i]["total_steps"] < 5:
                        self.env.switch_region(i)
                        return ClusterType.SPOT
            
            return ClusterType.SPOT
        
        # No spot available in current region
        # Try switching regions
        num_regions = self.env.get_num_regions()
        if num_regions > 1:
            # Switch to next region
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # After switching, use on-demand for one step to be safe
            # then check spot availability in next iteration
            return ClusterType.ON_DEMAND
        
        # Fallback to on-demand if only one region
        return ClusterType.ON_DEMAND