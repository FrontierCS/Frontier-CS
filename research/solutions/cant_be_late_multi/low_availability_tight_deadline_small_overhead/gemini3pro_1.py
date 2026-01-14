import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cost_optimized_multi_region_strategy"

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

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Calculate work remaining
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is logically complete, stop (though environment should handle this)
        if work_remaining <= 0:
            return ClusterType.NONE

        # Calculate time constraints
        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # Minimum time required to finish using On-Demand (guaranteed capacity)
        # We add restart_overhead because switching to OD or starting OD incurs it.
        min_time_needed = work_remaining + self.restart_overhead
        
        # Slack is the buffer time we have before we MUST rely on OD to meet deadline
        slack = time_remaining - min_time_needed
        
        # Safety buffer: if slack drops below this (e.g., 2 hours), strictly use OD.
        # This prevents failure due to minor overheads or search delays when close to deadline.
        # gap_seconds is the step size (e.g. 1 hour).
        safety_buffer = 2.0 * self.env.gap_seconds
        
        # Strategy Logic:
        
        # 1. Critical Urgency: If slack is low, prioritize deadline over cost.
        if slack < safety_buffer:
            # Stay in current region and run On-Demand. 
            # Do not switch region to avoid unnecessary restart overheads/downtime.
            return ClusterType.ON_DEMAND
            
        # 2. Prefer Spot: If Spot is available in the current region, use it.
        # This is the most cost-effective option ($0.97 vs $3.06).
        if has_spot:
            return ClusterType.SPOT
            
        # 3. Hunt for Spot: Spot unavailable locally, but we have plenty of slack.
        # Instead of paying for On-Demand immediately, we switch region and wait.
        # Action: Switch to next region, return NONE.
        # Cost: $0 (monetary), 1 timestep (time).
        # Benefit: Potentially finding Spot in the next region for the next timestep.
        
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        # Round-robin switch to next region
        next_region = (current_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        # Return NONE to pause execution for this step.
        # We cannot verify Spot availability in the new region until the next _step call.
        return ClusterType.NONE