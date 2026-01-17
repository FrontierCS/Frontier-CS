import json
from argparse import Namespace
import heapq
from typing import List, Tuple, Dict
from collections import defaultdict

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
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
        
        # Initialize additional state
        self.remaining_work = self.task_duration[0]
        self.regions_count = 0  # Will be set in first _step call
        self.spot_history = defaultdict(list)
        self.last_decision = ClusterType.NONE
        self.consecutive_none = 0
        self.region_spot_availability = defaultdict(list)
        self.current_spot_pattern = {}
        self.time_since_switch = 0
        self.original_region = -1
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Initialize regions count on first call
        if self.regions_count == 0:
            self.regions_count = self.env.get_num_regions()
            self.original_region = self.env.get_current_region()
            
        # Update spot availability history
        current_region = self.env.get_current_region()
        self.spot_history[current_region].append(has_spot)
        
        # Calculate remaining work and time
        completed_work = sum(self.task_done_time)
        remaining_work = self.remaining_work - completed_work
        remaining_time = self.deadline - self.env.elapsed_seconds
        
        # If work is done, return NONE
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If we're out of time, use on-demand as last resort
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND
            
        # Calculate safe thresholds
        time_per_unit = self.env.gap_seconds
        overhead = self.restart_overhead[0]
        
        # Calculate how much work we can do in remaining time
        max_possible_work = remaining_time - (overhead if last_cluster_type == ClusterType.NONE else 0)
        
        # If we're in danger zone (little time left), use on-demand
        if remaining_time < max(overhead * 3, remaining_work * 1.5):
            if has_spot and remaining_time > overhead * 2:
                # Still try spot if available and we have some buffer
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND
        
        # If we have overhead pending, wait or use on-demand
        if self.remaining_restart_overhead > 0:
            # If overhead is small relative to remaining time, wait
            if self.remaining_restart_overhead < remaining_time * 0.1:
                return ClusterType.NONE
            # Otherwise, use on-demand to avoid wasting more time
            return ClusterType.ON_DEMAND
        
        # Analyze spot patterns in current region
        recent_history = self.spot_history[current_region][-5:]  # Last 5 steps
        if recent_history:
            spot_availability = sum(recent_history) / len(recent_history)
            
            # If spot is consistently available, use it
            if spot_availability >= 0.8 and has_spot:
                self.consecutive_none = 0
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
        
        # Check other regions for better spot availability
        if not has_spot or (recent_history and spot_availability < 0.5):
            best_region = current_region
            best_availability = 0
            
            # Quick survey of other regions
            for region in range(self.regions_count):
                if region == current_region:
                    continue
                    
                region_history = self.spot_history[region]
                if len(region_history) >= 3:
                    avail = sum(region_history[-3:]) / min(3, len(region_history))
                    if avail > best_availability:
                        best_availability = avail
                        best_region = region
            
            # Switch if significantly better and we can afford overhead
            if (best_region != current_region and best_availability > 0.7 and 
                remaining_time > overhead * 2 + remaining_work):
                self.env.switch_region(best_region)
                self.time_since_switch = 0
                # After switch, use spot if available in new region
                # (Note: has_spot still refers to old region, but we'll check next step)
                return ClusterType.NONE
        
        # Decision logic
        if has_spot:
            # Use spot when available and we have time buffer
            risk_factor = remaining_work / max(remaining_time - overhead, 1)
            if risk_factor < 0.7:  # Only use spot if we have good buffer
                self.consecutive_none = 0
                self.last_decision = ClusterType.SPOT
                return ClusterType.SPOT
        
        # Use on-demand if we're falling behind schedule
        progress_ratio = completed_work / self.remaining_work
        time_ratio = self.env.elapsed_seconds / self.deadline
        
        if progress_ratio < time_ratio * 0.8:  # Behind schedule
            self.consecutive_none = 0
            self.last_decision = ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND
        
        # If we're ahead of schedule and no spot, wait briefly
        if self.consecutive_none < 2 and remaining_time > remaining_work * 1.5:
            self.consecutive_none += 1
            self.last_decision = ClusterType.NONE
            return ClusterType.NONE
        
        # Default to on-demand
        self.consecutive_none = 0
        self.last_decision = ClusterType.ON_DEMAND
        return ClusterType.ON_DEMAND