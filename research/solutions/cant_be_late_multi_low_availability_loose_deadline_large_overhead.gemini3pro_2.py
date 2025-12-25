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
        # Calculate current progress and time constraints
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done)
        time_left = self.deadline - elapsed
        
        gap = self.env.gap_seconds
        overhead = self.restart_overhead

        # Safety Check Logic:
        # Calculate the minimum time required to finish the task using reliable On-Demand instances.
        # We include:
        # 1. remaining_work: Actual work left.
        # 2. overhead: Potential restart overhead if we switch to OD now or are interrupted.
        # 3. safety_buffer: A buffer to account for the current timestep (gap) potentially being wasted
        #    during a search or transition, plus extra slack to prevent deadline violation.
        #    2.0 * gap provides a safe margin (e.g. 2 hours if gap is 1 hour).
        safety_buffer = 2.0 * gap
        required_time_for_safety = remaining_work + overhead + safety_buffer

        # If we are close to the safety threshold, strictly use On-Demand to ensure completion.
        # This avoids the -100,000 penalty for missing the deadline.
        if time_left < required_time_for_safety:
            return ClusterType.ON_DEMAND

        # Cost Optimization Logic:
        # If we have sufficient slack, we prioritize minimizing cost.
        if has_spot:
            # Spot instances are available in the current region. Use them.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in the current region.
            # Since we have slack, we avoid the expensive On-Demand option.
            # Instead, we switch to the next region and wait (return NONE) for one step.
            # In the next step, we will check if Spot is available in the new region.
            # This effectively cycles through regions to find available Spot capacity.
            current_region_idx = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region_idx = (current_region_idx + 1) % num_regions
            
            self.env.switch_region(next_region_idx)
            return ClusterType.NONE
