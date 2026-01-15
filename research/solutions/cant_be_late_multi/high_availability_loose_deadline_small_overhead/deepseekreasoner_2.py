import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""
    
    NAME = "adaptive_spot_scheduler"

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
        
        self.region_count = None
        self.gap_seconds = None
        self.remaining_work = None
        self.consecutive_spot_failures = 0
        self.max_spot_attempts = 3
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self.gap_seconds is None:
            self.gap_seconds = self.env.gap_seconds
        
        if self.region_count is None:
            self.region_count = self.env.get_num_regions()
        
        current_region = self.env.get_current_region()
        elapsed = self.env.elapsed_seconds
        
        remaining_time = self.deadline - elapsed
        if self.remaining_work is None:
            total_done = sum(self.task_done_time)
            self.remaining_work = self.task_duration - total_done
        
        if self.remaining_work <= 0:
            return ClusterType.NONE
        
        # If we're running out of time, switch to on-demand
        if remaining_time < self.remaining_work + self.restart_overhead:
            return ClusterType.ON_DEMAND
        
        # Calculate slack time ratio
        slack_ratio = (remaining_time - self.remaining_work) / self.remaining_work
        
        # If we have spot availability and good slack, try spot
        if has_spot and slack_ratio > 0.3:
            if last_cluster_type == ClusterType.SPOT:
                self.consecutive_spot_failures = 0
                return ClusterType.SPOT
            else:
                # Only switch to spot if we haven't had too many failures recently
                if self.consecutive_spot_failures < self.max_spot_attempts:
                    return ClusterType.SPOT
        
        # No spot available or not enough slack - check other regions
        if not has_spot and last_cluster_type == ClusterType.SPOT:
            self.consecutive_spot_failures += 1
            
            # Try switching to another region that might have spot
            best_region = current_region
            best_score = -1
            
            # Check all regions for potential spot usage
            for region in range(self.region_count):
                if region == current_region:
                    continue
                
                # Simple heuristic: regions with different parity might have different patterns
                if (region % 2) != (current_region % 2):
                    best_region = region
                    break
            
            if best_region != current_region:
                self.env.switch_region(best_region)
                # After switching, we'll need to check spot availability in next step
                return ClusterType.NONE
        
        # Default to on-demand if no good spot option
        return ClusterType.ON_DEMAND