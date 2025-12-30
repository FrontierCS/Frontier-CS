import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_strategy"

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
        """
        # Gather environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # Calculate time remaining
        time_remaining = self.deadline - elapsed
        
        # Effective work needed: remaining work + potential restart overhead
        # We include restart overhead to be conservative, assuming we might need to restart
        effective_work_needed = work_remaining + self.restart_overhead
        
        # Slack: How much extra time we have beyond what is strictly needed
        slack = time_remaining - effective_work_needed
        
        # Safety buffer: If slack falls below this threshold, we enter 'Panic Mode'.
        # We use 1.5 * gap to ensure we handle time quantization and boundaries safely.
        safe_buffer = 1.5 * gap
        
        # 1. Panic Mode: Approaching deadline
        if slack < safe_buffer:
            # We must prioritize reliability over cost.
            # Use On-Demand to guarantee availability and completion.
            # Stay in the current region to avoid switching overhead/risks.
            return ClusterType.ON_DEMAND
        
        # 2. Economy Mode: We have sufficient slack
        if has_spot:
            # Spot is available in the current region. Use it to save costs.
            return ClusterType.SPOT
        else:
            # Spot is unavailable locally.
            # Since we have slack, we can 'hunt' for Spot in other regions.
            # Strategy: Switch to next region and return NONE for this step.
            # This incurs 0 cost (just time), allowing us to check the new region next step.
            next_region = (self.env.get_current_region() + 1) % self.env.get_num_regions()
            self.env.switch_region(next_region)
            return ClusterType.NONE