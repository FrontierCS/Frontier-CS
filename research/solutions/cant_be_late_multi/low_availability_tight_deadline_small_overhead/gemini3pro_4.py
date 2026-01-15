import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        # 1. Update State
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        needed = self.task_duration - done
        
        # If task is completed
        if needed <= 0:
            return ClusterType.NONE

        overhead = self.restart_overhead
        # Safety buffer: 2 hours (in seconds)
        # This ensures we switch to On-Demand with enough time to finish,
        # plus a margin for any final overheads or granular inefficiencies.
        safe_buffer = 2.0 * 3600.0
        
        remaining_time = self.deadline - elapsed
        
        # Slack: The amount of time we can afford to waste (waiting or searching)
        # before we must commit to On-Demand to guarantee meeting the deadline.
        # We subtract overhead to ensure we can pay the final setup cost.
        slack = remaining_time - needed - overhead - safe_buffer

        # 2. Criticality Check (Panic Mode)
        # If slack is exhausted, we must run now using the most reliable resource.
        # We stick to On-Demand to guarantee completion.
        if slack < 0:
            return ClusterType.ON_DEMAND

        # 3. Cost Optimization (Economy Mode)
        # If Spot is available in the current region, use it.
        # This is the cheapest option and we have slack to handle potential preemptions.
        if has_spot:
            return ClusterType.SPOT

        # 4. Spot Hunting
        # Spot is unavailable in the current region, but we have slack.
        # Instead of waiting (returning NONE in the same region) or paying for OD,
        # we switch to the next region to check for Spot availability.
        
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Round-Robin switching
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        # Return NONE to pause execution for this step.
        # We cannot return SPOT because we don't know if the new region has spot yet.
        # We don't want to return ON_DEMAND because we are hunting for cheap resources.
        # The cost is 1 timestep of delay (gap_seconds), which is absorbed by our slack.
        return ClusterType.NONE