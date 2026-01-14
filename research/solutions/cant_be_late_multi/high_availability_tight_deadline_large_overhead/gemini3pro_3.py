import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "AdaptiveSlackStrategy"

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
        
        # Optimization: Cache partial sum of task_done_time to ensure O(1) step
        self._cached_work_done = 0.0
        self._last_list_len = 0
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update work done cache efficiently
        current_len = len(self.task_done_time)
        if current_len > self._last_list_len:
            new_work = sum(self.task_done_time[self._last_list_len:])
            self._cached_work_done += new_work
            self._last_list_len = current_len
            
        work_done = self._cached_work_done
        work_remaining = self.task_duration - work_done
        
        # If work is effectively done, return NONE
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        
        # Calculate time needed if we switch to/continue On-Demand to guarantee finish
        # If currently On-Demand, we only pay remaining overhead (if any)
        # If not, we assume we pay full restart overhead to switch to OD
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_cost = self.remaining_restart_overhead
        else:
            overhead_cost = self.restart_overhead
            
        # Safety buffer (2 hours) to ensure we meet deadline despite granularities
        safety_buffer = 7200.0 
        required_time_od = work_remaining + overhead_cost + safety_buffer
        
        # Panic condition: If running out of time relative to OD completion time, force On-Demand
        if time_left < required_time_od:
            return ClusterType.ON_DEMAND
            
        # If we have Slack, prefer Spot
        if has_spot:
            return ClusterType.SPOT
        
        # Spot is unavailable in current region, and we have slack.
        # Cycle to next region and wait 1 step to check availability.
        # This incurs overhead but allows searching for available Spot capacity.
        curr_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (curr_region + 1) % num_regions
        self.env.switch_region(next_region)
        
        return ClusterType.NONE