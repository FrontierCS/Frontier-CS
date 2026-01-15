import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "robust_scheduler"

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
        # Update state variables
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        work_remaining = max(0.0, self.task_duration - work_done)
        time_left = self.deadline - elapsed
        
        # Get environment parameters
        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Calculate safety threshold to ensure deadline is met.
        # We must switch to On-Demand (guaranteed resource) if we are close to running out of time.
        # The threshold reserves time for:
        # 1. The actual remaining work.
        # 2. The restart overhead (incurred if we switch to OD or if Spot is preempted).
        # 3. A safety buffer (2 * gap) to account for the current time step potentially being lost 
        #    if we attempt Spot and it fails/is preempted, plus floating point margin.
        safety_threshold = work_remaining + overhead + (gap * 2.0)
        
        # Panic condition: If time is tight, strictly use On-Demand.
        if time_left < safety_threshold:
            return ClusterType.ON_DEMAND
            
        # If we have sufficient slack time, prefer Spot instances to minimize cost.
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is unavailable in the current region but we have slack:
        # Search for Spot in other regions.
        # We switch to the next region (Round-Robin) and return NONE.
        # Returning NONE pauses execution for one time step (gap), allowing us to 
        # check availability (has_spot) in the new region during the next _step call.
        # The cost of waiting (time loss) is acceptable due to the slack buffer.
        num_regions = self.env.get_num_regions()
        current_region = self.env.get_current_region()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        
        return ClusterType.NONE