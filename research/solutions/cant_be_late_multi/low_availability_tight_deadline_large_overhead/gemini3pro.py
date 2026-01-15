import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "CantBeLateStrategy"

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
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        work_rem = max(0.0, self.task_duration - done)
        
        # If work is done, stop
        if work_rem <= 1e-6:
            return ClusterType.NONE

        time_rem = self.deadline - elapsed
        
        # Calculate effective time required if we commit to ON_DEMAND immediately.
        # This includes remaining work + any overhead to become stable on OD.
        overhead_penalty = 0.0
        if last_cluster_type == ClusterType.ON_DEMAND:
            # If already OD, we only pay remaining overhead (if any)
            overhead_penalty = self.remaining_restart_overhead
        else:
            # If switching to OD from Spot/None, we pay full restart overhead
            overhead_penalty = self.restart_overhead
            
        time_needed_for_od = work_rem + overhead_penalty
        
        # Safety buffer: If we choose Spot or Search (NONE), we risk losing the current timestep (gap_seconds)
        # if the Spot instance is preempted or the search yields nothing.
        # If that happens, we will need to switch to OD in the future, which costs restart_overhead.
        # Therefore, we must ensure: time_rem - gap >= work_rem + restart_overhead
        # buffer = gap + restart_overhead + small safety margin
        buffer = self.env.gap_seconds + self.restart_overhead + 60.0
        
        # Panic Check: If remaining time is tight, force ON_DEMAND
        if time_rem < time_needed_for_od + buffer:
            return ClusterType.ON_DEMAND
            
        # Strategy: Use Spot if available, otherwise Search
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot not available in current region.
            # If we have multiple regions, switch to the next one to search for Spot.
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                next_region_idx = (self.env.get_current_region() + 1) % num_regions
                self.env.switch_region(next_region_idx)
            
            # Return NONE to pause/wait/travel. 
            # If we switched, overhead is incurred. 
            # If we didn't switch (single region), we wait.
            return ClusterType.NONE