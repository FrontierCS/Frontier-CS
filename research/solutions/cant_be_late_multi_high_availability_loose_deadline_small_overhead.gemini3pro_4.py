import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Calculate work done and work remaining in seconds
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # Calculate time remaining in seconds
        elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - elapsed
        
        # Calculate slack (time we can afford to lose/waste)
        slack = time_remaining - work_remaining
        
        # Panic Threshold Calculation
        # We need to guarantee completion. If slack drops below a safe margin, 
        # we must switch to On-Demand (guaranteed capacity).
        # Margin includes:
        # 1. restart_overhead: Cost to spin up the OD instance.
        # 2. 2.0 * gap_seconds: Buffer to account for the granularity of time steps.
        #    If the current step fails or is a search step, we lose 'gap_seconds'.
        #    We want to ensure we still have enough time after losing a step.
        panic_threshold = self.restart_overhead + (self.env.gap_seconds * 2.0)
        
        # Emergency Condition: Not enough slack to gamble on Spot availability.
        if slack < panic_threshold:
            return ClusterType.ON_DEMAND

        # Normal Operation: Prefer Spot instances to minimize cost.
        if has_spot:
            # If Spot is available in current region, use it.
            return ClusterType.SPOT
        
        # If Spot is not available in current region:
        # We should search for another region.
        # We switch to the next region (Round Robin strategy).
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        # After switching, we don't know the spot availability of the new region 
        # until the next time step. Returning SPOT here would be unsafe (and raise 
        # an error if unavailable). We return NONE to pause for one step and check 
        # availability in the next call.
        return ClusterType.NONE