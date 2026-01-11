import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostOptimizedStrategy"

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining = max(0.0, self.task_duration - done)
        overhead = self.restart_overhead
        
        # Calculate slack time
        # Slack is the time buffer we have before we MUST run on full speed (OD) to finish.
        # Slack = Time_Left - (Work_Remaining + Restart_Overhead)
        time_left = self.deadline - elapsed
        min_time_needed = remaining + overhead
        slack = time_left - min_time_needed
        
        # Strategy Thresholds
        
        # 1. Critical Threshold
        # If slack is below this, we are in danger of missing the deadline.
        # We must use On-Demand to guarantee completion.
        # Buffer of 1.5 * gap accounts for discrete time steps and ensures we switch before it's too late.
        critical_buffer = 1.5 * gap
        
        if slack < critical_buffer:
            return ClusterType.ON_DEMAND
            
        # 2. Spot Availability Check
        # If Spot is available in current region and we are not critical, use it.
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Region Switching
        # If current region has no Spot, we switch to try another.
        # We cycle through regions in a round-robin fashion.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        if num_regions > 1:
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
        # 4. Search Strategy (Blind decision in new region)
        # We have switched regions but don't know the Spot status of the new region for this step.
        # We must decide to wait (NONE) or work (OD).
        
        # If we have plenty of slack, we use NONE to save money while searching for a stable region.
        # If slack is moderate (getting tighter), we use OD to maintain progress while searching.
        # Search Buffer allows for approximately one full rotation of region checks using NONE
        # before we start using OD to ensure progress.
        search_buffer = (num_regions * gap) + critical_buffer
        
        if slack > search_buffer:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND