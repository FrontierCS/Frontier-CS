import json
import math
from argparse import Namespace
from typing import List, Tuple
from enum import IntEnum

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class SpotState(IntEnum):
    UNKNOWN = 0
    AVAILABLE = 1
    UNAVAILABLE = 2


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
        
        # Initialize tracking structures
        self.spot_history = []  # Track spot availability patterns
        self.region_stats = {}  # Per-region statistics
        self.consecutive_spot_failures = 0
        self.last_decision = ClusterType.NONE
        self.spot_unavailable_count = 0
        
        return self
    
    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update spot history
        self.spot_history.append(has_spot)
        if len(self.spot_history) > 100:
            self.spot_history.pop(0)
        
        # Calculate critical metrics
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - self.env.elapsed_seconds
        
        # Calculate minimum time needed
        overhead_if_needed = self.restart_overhead if last_cluster_type != ClusterType.NONE else 0
        min_time_needed = work_remaining + overhead_if_needed
        
        # If we're in overhead period, just wait
        if self.remaining_restart_overhead > 0:
            return ClusterType.NONE
        
        # Emergency mode: if we're running out of time, use on-demand
        safety_factor = 2.0
        if time_remaining < min_time_needed * safety_factor:
            return ClusterType.ON_DEMAND
        
        # If spot was recently unreliable, be cautious
        recent_failures = sum(1 for x in self.spot_history[-10:] if not x) if len(self.spot_history) >= 10 else 0
        if recent_failures >= 5:
            # Spot has been unreliable recently, use on-demand for stability
            return ClusterType.ON_DEMAND
        
        # If we have plenty of time and spot is available, use it
        if has_spot and time_remaining > work_remaining * 3:
            return ClusterType.SPOT
        
        # If spot is not available, consider switching regions
        if not has_spot:
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            
            # Try to find a better region if we have time
            if time_remaining > work_remaining * 2:
                # Try next region
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
                # Don't start immediately after switching - let overhead apply if needed
                return ClusterType.NONE
            else:
                # Not enough time to experiment, use on-demand
                return ClusterType.ON_DEMAND
        
        # Default: use spot if available, otherwise on-demand
        return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
