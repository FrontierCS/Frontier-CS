import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cost_optimized_strategy"

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
        # Current state
        current_time = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        time_remaining = self.deadline - current_time
        
        # Restart overhead in seconds
        overhead = self.restart_overhead
        
        # Slack calculation:
        # Time remaining minus work remaining minus one overhead (to be safe for a restart)
        # Slack represents the buffer of time we can waste before we fail
        slack = time_remaining - work_remaining - overhead
        
        # Define safety thresholds (in seconds)
        # 1.5x overhead provides a buffer against floating point issues or mid-step changes.
        # If slack drops below this, we are in danger of missing the deadline.
        safety_buffer = 1.5 * overhead
        
        # Panic Mode: If slack is insufficient, force On-Demand to avoid failure penalty.
        # The penalty for failure (-100,000) outweighs any cost savings.
        if slack < safety_buffer:
            return ClusterType.ON_DEMAND
        
        # Prefer Spot if available (it is significantly cheaper)
        if has_spot:
            return ClusterType.SPOT
            
        # If Spot is unavailable in current region:
        # Strategy: Switch to the next region to search for Spot availability.
        # We cycle through regions round-robin.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        # Switch region (incurs overhead on next execution)
        self.env.switch_region(next_region)
        
        # After switching, we cannot use Spot in this step because 'has_spot' was False 
        # for the previous region, and we haven't checked the new region yet.
        # We must decide whether to run On-Demand or Wait (NONE).
        
        # If we return NONE:
        # - Cost: $0
        # - Progress: 0
        # - Slack Impact: Decreases by 'gap_seconds' (time wasted waiting)
        
        # If we return ON_DEMAND:
        # - Cost: High ($3.06/hr)
        # - Progress: gap_seconds - overhead
        # - Slack Impact: Decreases by 'overhead' (time wasted on restart)
        
        # Decision: 
        # If we have plenty of slack, return NONE to save money and check the new region for Spot in the next step.
        # If slack is tight, return ON_DEMAND to ensure we make progress.
        
        if slack > (self.env.gap_seconds + safety_buffer):
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND