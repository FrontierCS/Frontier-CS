import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CostOptimizedStrategy"  # REQUIRED: unique identifier

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
        # Gather current state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate remaining work
        completed_work = sum(self.task_done_time)
        remaining_work = self.task_duration - completed_work
        
        # Calculate time remaining
        time_left = self.deadline - elapsed
        
        # Calculate slack
        # Slack is the buffer we have before we MUST run perfectly to finish.
        # We subtract restart_overhead to account for the time lost starting up 
        # (or recovering from an interruption).
        slack = time_left - remaining_work - self.restart_overhead
        
        # Define a safety buffer/panic threshold
        # If slack drops below this, we cannot afford to waste time searching for Spot
        # or risking interruptions.
        # We use 1.5 * gap_seconds to ensure we have at least one step of buffer 
        # before hitting 0 slack (assuming gap is the decision interval).
        PANIC_THRESHOLD = 1.5 * gap
        
        # Decision Logic
        
        # 1. If we are critically low on slack, force On-Demand to guarantee completion.
        # On-Demand is reliable and never interrupted.
        if slack < PANIC_THRESHOLD:
            return ClusterType.ON_DEMAND
            
        # 2. If we have slack, try to optimize for cost (Spot).
        if has_spot:
            # Spot is available in the current region. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region.
            # Since we have sufficient slack, it is worth switching regions to find Spot
            # rather than paying for On-Demand immediately.
            
            # Switch to the next region (round-robin)
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # After switching, we are technically in a new region, but 'has_spot' 
            # reflects the state at the beginning of the step (old region).
            # Also, switching forces a restart overhead and effectively consumes this step.
            # We return NONE to transition. The next step will provide availability 
            # for the new region.
            return ClusterType.NONE
