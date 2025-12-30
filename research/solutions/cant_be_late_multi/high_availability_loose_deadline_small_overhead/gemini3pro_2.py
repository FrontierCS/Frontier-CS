import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "cant_be_late_solution"

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
        Prioritizes meeting the deadline, then minimizing cost by seeking Spot instances across regions.
        """
        # Calculate progress and remaining work
        current_progress = sum(self.task_done_time)
        remaining_work = self.task_duration - current_progress
        
        # Effective remaining work includes pending overhead.
        # If we are restarting or switching, we pay overhead.
        effective_work = remaining_work + self.remaining_restart_overhead
        
        # Calculate time remaining until deadline
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Calculate Slack: Time we can afford to waste before we MUST execute perfectly
        slack = time_left - effective_work
        
        # Define Safety Buffer
        # If slack falls below this threshold, we switch to Panic Mode (On-Demand).
        # We account for:
        # 1. The current time step gap (if we waste this step searching, we lose 'gap' seconds)
        # 2. Several restart overheads (in case of failures/preemptions)
        # Using 1.5 * gap ensures that if the gap is large (e.g., 1 hour) and we are close to the edge,
        # we don't risk waiting.
        safety_buffer = (1.5 * self.env.gap_seconds) + (6.0 * self.restart_overhead)
        
        # --- Decision Logic ---

        # 1. Critical Phase: Deadline is threatening
        if slack < safety_buffer:
            # We cannot afford to search for Spot or risk preemption.
            # Use On-Demand to guarantee progress.
            # We stay in the current region to avoid unnecessary switching overheads.
            return ClusterType.ON_DEMAND

        # 2. Economy Phase: We have time, optimize for cost
        if has_spot:
            # Spot is available in the current region. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # Since we have healthy slack, we search for Spot in other regions.
            
            # Switch to the next region (Round Robin search)
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            
            # We switched regions. We cannot use Spot immediately in this step 
            # (as `has_spot` reflects the old region).
            # We return NONE to pause and check the new region's availability in the next step.
            # This costs time (gap + overhead) but 0 money.
            return ClusterType.NONE