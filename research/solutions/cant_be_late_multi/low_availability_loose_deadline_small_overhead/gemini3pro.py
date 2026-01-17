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
        # Calculate current state
        done_work = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - done_work)
        
        # If work is completed, do nothing
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        gap = self.env.gap_seconds
        elapsed = self.env.elapsed_seconds
        time_left = max(0.0, self.deadline - elapsed)
        
        # Calculate time needed to finish if we commit to On-Demand immediately.
        # We add restart_overhead to account for the initialization/interruption cost.
        needed_time = remaining_work + self.restart_overhead
        
        # Determine safety threshold.
        # We can only afford to pause (return NONE) or search other regions if,
        # after wasting 'gap' seconds, we still have enough time to finish using On-Demand.
        # We use a small multiplier (1.01) on the gap for numerical safety.
        safety_threshold = needed_time + gap * 1.01
        
        # Panic Mode: If we are close to the "point of no return", force On-Demand.
        # This guarantees we finish before the deadline, even if it costs more.
        if time_left < safety_threshold:
            return ClusterType.ON_DEMAND

        # Optimization Mode: We have enough slack to try to save money.
        if has_spot:
            # Current region has Spot capacity, use it (cheapest option).
            return ClusterType.SPOT
        else:
            # Current region has no Spot. Since we have slack, we can afford to 
            # switch regions and wait one step to see if Spot is available there.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Return NONE to incur no monetary cost while we transition/probe.
            # In the next step, has_spot will reflect the new region's availability.
            return ClusterType.NONE