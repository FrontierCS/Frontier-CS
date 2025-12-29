import json
from argparse import Namespace
from typing import List
from enum import Enum

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with adaptive spot usage."""
    
    NAME = "adaptive_spot_multi_region"
    
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
        
        self.work_done = 0.0
        self.last_work_update = 0.0
        self.regions_tried = set()
        self.region_spot_history = {}
        self.consecutive_spot_failures = 0
        self.max_spot_failures = 3
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate progress
        current_work = sum(self.task_done_time)
        work_progress = current_work - self.work_done
        self.work_done = current_work
        
        # Update region spot history
        current_region = self.env.get_current_region()
        if current_region not in self.region_spot_history:
            self.region_spot_history[current_region] = []
        self.region_spot_history[current_region].append(has_spot)
        
        # If we're in restart overhead, wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Check if task is complete
        if current_work >= self.task_duration:
            return ClusterType.NONE
        
        # Calculate time pressure
        time_left = self.deadline - self.env.elapsed_seconds
        work_left = self.task_duration - current_work
        
        # Critical: must use on-demand if time is very tight
        safe_time_needed = work_left + self.restart_overhead * 2
        if time_left <= safe_time_needed:
            return ClusterType.ON_DEMAND
        
        # Check spot history in current region
        if current_region in self.region_spot_history:
            recent_history = self.region_spot_history[current_region][-5:]  # Last 5 steps
            spot_reliability = sum(recent_history) / len(recent_history) if recent_history else 0
            
            # Too many recent spot failures in this region
            if not has_spot:
                self.consecutive_spot_failures += 1
                if self.consecutive_spot_failures >= self.max_spot_failures:
                    # Try another region
                    return self._try_other_region(current_region, has_spot)
            else:
                self.consecutive_spot_failures = 0
        else:
            self.consecutive_spot_failures = 0 if has_spot else 1
        
        # Decision logic
        if has_spot:
            # Use spot if we have enough time buffer
            buffer_needed = work_left * 1.5 + self.restart_overhead * 3
            if time_left > buffer_needed:
                return ClusterType.SPOT
            else:
                # Time is getting tight, use on-demand
                return ClusterType.ON_DEMAND
        else:
            # No spot available
            if work_progress > 0:
                # We made progress last step, stay in current region with on-demand
                return ClusterType.ON_DEMAND
            else:
                # No progress, try another region
                return self._try_other_region(current_region, has_spot)
    
    def _try_other_region(self, current_region: int, has_spot: bool) -> ClusterType:
        """Try switching to another region with better spot prospects."""
        num_regions = self.env.get_num_regions()
        
        # Check all regions for potential spot availability
        for i in range(num_regions):
            if i == current_region:
                continue
            
            if i not in self.regions_tried or len(self.regions_tried) >= num_regions - 1:
                # Switch to untried region first
                self.env.switch_region(i)
                self.regions_tried.add(i)
                
                # If we have history for this region, check reliability
                if i in self.region_spot_history:
                    recent = self.region_spot_history[i][-3:] if len(self.region_spot_history[i]) >= 3 else self.region_spot_history[i]
                    if recent and sum(recent) / len(recent) > 0.5:
                        # Region has good spot history
                        return ClusterType.ON_DEMAND  # Start with on-demand, then switch to spot
                
                # Use on-demand in new region initially
                return ClusterType.ON_DEMAND
        
        # All regions tried or no good options, use on-demand in current
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.ON_DEMAND