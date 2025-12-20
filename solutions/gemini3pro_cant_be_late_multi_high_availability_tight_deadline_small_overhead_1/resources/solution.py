import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy that optimizes cost while meeting deadline."""

    NAME = "cost_aware_robust_scheduler"

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        Prioritize Spot instances when slack permits.
        Switch regions to find Spot if current region is unavailable.
        Fall back to On-Demand when deadline approaches to guarantee completion.
        """
        # Calculate progress and slack
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If work is complete, do nothing
        if work_remaining <= 1e-6:
            return ClusterType.NONE
            
        time_remaining = self.deadline - self.env.elapsed_seconds
        slack = time_remaining - work_remaining
        
        # Strategy parameters
        gap = self.env.gap_seconds
        
        # Safety buffer: 2 hours.
        # If slack falls below this, we stop hunting for Spot and use reliable On-Demand.
        # This protects against trace variability and ensures we finish before deadline.
        # We need a buffer > 0 to account for potential restart overheads and small variations.
        SAFETY_BUFFER = 7200.0
        
        # 1. Critical Phase: Low Slack
        if slack < SAFETY_BUFFER:
            # We are close to the "point of no return".
            # Prioritize reliability.
            # If Spot is available right now, we could use it, but if it fails, we might miss deadline.
            # However, prompt says "finish before deadline while minimizing cost".
            # Running OD guarantees finishing if slack >= 0.
            # We stick to OD to be safe given the heavy penalty for failure.
            return ClusterType.ON_DEMAND
            
        # 2. Normal Phase: High Slack
        # We prefer Spot instances.
        
        if has_spot:
            # Spot is available in current region. Use it.
            return ClusterType.SPOT
        else:
            # Spot is not available in current region.
            # We have slack. Should we hunt for Spot in another region?
            
            # Hunting (Switch + Wait) costs 'gap' seconds of slack.
            # We only hunt if we will still have a safe buffer after wasting this step.
            if slack - gap > SAFETY_BUFFER:
                # Switch to next region in round-robin fashion
                current_region_idx = self.env.get_current_region()
                num_regions = self.env.get_num_regions()
                next_region_idx = (current_region_idx + 1) % num_regions
                
                self.env.switch_region(next_region_idx)
                
                # Return NONE to pause execution for this step (incurring gap time),
                # allowing us to check spot availability in the new region at next step.
                return ClusterType.NONE
            else:
                # Not enough slack to justify wasting time hunting.
                # Run On-Demand to ensure progress.
                return ClusterType.ON_DEMAND
