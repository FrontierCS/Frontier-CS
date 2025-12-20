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
        
        # Optimization: Cache work done to avoid O(N) summation every step
        self.cached_work_done = 0.0
        self.cached_len = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Efficiently calculate work done so far
        # self.task_done_time is a list of completed work segments
        current_list = self.task_done_time
        current_len = len(current_list)
        
        if current_len > self.cached_len:
            # Update cache with new segments
            for i in range(self.cached_len, current_len):
                self.cached_work_done += current_list[i]
            self.cached_len = current_len
            
        work_rem = self.task_duration - self.cached_work_done
        
        # If finished (should be handled by env, but safe check)
        if work_rem <= 1e-7:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        overhead = self.restart_overhead
        
        # Safety Buffer: 30 minutes (1800s)
        # This provides a margin for floating point errors and guarantees safe switch
        buffer = 1800.0
        
        # Panic Condition:
        # If remaining time is close to the minimum time required to finish on On-Demand (safe resource),
        # we must switch to On-Demand immediately.
        # Required time = Remaining Work + Restart Overhead (incurred if we switch to OD)
        if time_left < (work_rem + overhead + buffer):
            return ClusterType.ON_DEMAND

        # Strategy:
        # 1. Prefer Spot (cheapest).
        # 2. If current region has Spot, use it.
        # 3. If current region lacks Spot, switch to next region and probe.
        
        if has_spot:
            return ClusterType.SPOT
        else:
            # Switch to next region in Round-Robin fashion
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Return NONE to allow the environment to update availability for the new region
            # in the next step. Returning SPOT here would be unsafe if the new region
            # also lacks Spot availability.
            return ClusterType.NONE
