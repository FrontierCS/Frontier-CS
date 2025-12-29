import json
from argparse import Namespace
from typing import List, Tuple
import heapq
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline-aware planning."""
    
    NAME = "deadline_aware_multi_region"
    
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
        self.current_region = 0
        self.last_action = ClusterType.NONE
        self.work_done = 0.0
        self.safety_margin = 2.0  # hours of safety margin for deadline
        
        return self
    
    def _calculate_remaining_time(self) -> float:
        """Calculate remaining time until deadline in hours."""
        elapsed_hours = self.env.elapsed_seconds / 3600.0
        deadline_hours = self.deadline / 3600.0
        return deadline_hours - elapsed_hours
    
    def _calculate_remaining_work(self) -> float:
        """Calculate remaining work in hours."""
        total_work_hours = self.task_duration / 3600.0
        done_work_hours = sum(self.task_done_time) / 3600.0
        return total_work_hours - done_work_hours
    
    def _should_switch_to_ondemand(self, remaining_time: float, remaining_work: float) -> bool:
        """Determine if we should switch to on-demand to meet deadline."""
        # If we can't finish with spot (considering overhead), use on-demand
        if remaining_work <= 0:
            return False
            
        # Time needed with spot (assuming worst-case: each step has overhead)
        spot_time_needed = remaining_work + self.restart_overhead / 3600.0
        
        # Time needed with on-demand (no interruptions, but may have initial overhead)
        ondemand_time_needed = remaining_work
        
        # If spot can't guarantee completion within deadline, use on-demand
        if spot_time_needed > remaining_time - self.safety_margin / 3600.0:
            return True
            
        # If we're very close to deadline, use on-demand
        if remaining_time < remaining_work + 2.0:  # within 2 hours
            return True
            
        return False
    
    def _find_best_spot_region(self) -> int:
        """Find region with highest probability of having spot based on recent history."""
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Simple heuristic: try adjacent regions first
        best_region = current_region
        best_score = 0
        
        # Try all regions, prefer regions we haven't tried recently
        for region in range(num_regions):
            if region == current_region:
                continue
                
            # Simple scoring: prefer regions with lower index (arbitrary but deterministic)
            score = 1.0 / (region + 1)
            if score > best_score:
                best_score = score
                best_region = region
                
        return best_region
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal state
        self.work_done = sum(self.task_done_time) / 3600.0
        remaining_time = self._calculate_remaining_time()
        remaining_work = self._calculate_remaining_work()
        
        # If work is done, do nothing
        if remaining_work <= 0:
            return ClusterType.NONE
            
        # If no time left, try on-demand as last resort
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND
        
        # Calculate time pressure ratio
        time_pressure = remaining_work / max(remaining_time, 0.1)
        
        # Decision logic
        if self._should_switch_to_ondemand(remaining_time, remaining_work):
            # Switch to on-demand to ensure deadline
            if last_cluster_type != ClusterType.ON_DEMAND:
                # Consider staying in current region for on-demand
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.ON_DEMAND
                
        elif has_spot and time_pressure < 0.8:  # Not too much time pressure
            # Use spot if available and we have time buffer
            if last_cluster_type == ClusterType.SPOT:
                return ClusterType.SPOT
            else:
                # Switch to spot, incurring overhead
                return ClusterType.SPOT
                
        elif has_spot and time_pressure >= 0.8:
            # High time pressure but spot available - use spot but be ready to switch
            return ClusterType.SPOT
            
        else:  # No spot available
            if time_pressure > 0.7:  # High time pressure
                # Switch to on-demand immediately
                return ClusterType.ON_DEMAND
            else:
                # Try switching region to find spot
                best_region = self._find_best_spot_region()
                if best_region != self.env.get_current_region():
                    self.env.switch_region(best_region)
                    # After switching, wait one step to see if new region has spot
                    return ClusterType.NONE
                else:
                    # Stay in current region, wait for spot
                    return ClusterType.NONE