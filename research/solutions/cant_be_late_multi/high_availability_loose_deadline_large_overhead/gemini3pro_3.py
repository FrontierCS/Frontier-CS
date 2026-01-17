import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
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
        elapsed = self.env.elapsed_seconds
        done = sum(self.task_done_time)
        work_rem = self.task_duration - done
        time_rem = self.deadline - elapsed
        
        if work_rem <= 0:
            return ClusterType.NONE

        gap = self.env.gap_seconds
        overhead = self.restart_overhead
        
        # Buffer set to 2 time steps to ensure we don't accidentally cross the point of no return
        # while switching regions or handling overheads.
        buffer = 2.0 * gap
        
        # Minimum time needed: remaining work + one restart overhead
        min_time_needed = work_rem + overhead
        
        # Panic condition: if we are close to the deadline, run On-Demand to guarantee completion.
        if time_rem <= min_time_needed + buffer:
            return ClusterType.ON_DEMAND

        # Prefer Spot instances if available
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is not available in current region, and we have enough slack:
        # Switch to the next region and wait (return NONE) for one step to probe availability.
        # We need enough time to waste 'gap' seconds switching + the buffer.
        if time_rem > min_time_needed + gap + buffer:
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            self.env.switch_region(next_region)
            return ClusterType.NONE
            
        # If we cannot afford to search other regions, fallback to On-Demand
        return ClusterType.ON_DEMAND