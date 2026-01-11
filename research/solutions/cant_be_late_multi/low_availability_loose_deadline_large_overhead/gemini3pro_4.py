import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "AdaptiveSpotHunter"

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
        
        Strategy:
        1. Calculate remaining work and time left.
        2. Define a "Panic Threshold": If time left is close to the minimum time required 
           to finish using On-Demand (including overheads), force On-Demand usage to ensure deadline.
        3. If not in panic mode:
           - If Spot is available in current region, use it (cheapest option).
           - If Spot is NOT available:
             - If multiple regions exist, switch to the next region to "hunt" for Spot.
             - Return NONE for the current step to avoid paying On-Demand costs while transitioning
               or waiting, and to avoid selecting Spot blindly after a switch.
        """
        # 1. State Calculation
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        
        # Sanity check if task is already complete
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_left = deadline - elapsed
        
        pending_overhead = self.remaining_restart_overhead
        gap = self.env.gap_seconds
        overhead_const = self.restart_overhead
        
        # 2. Safety / Panic Check
        # Calculate strict minimum time needed to finish on OD:
        # Work + Current Pending Overhead + Buffer.
        # Buffer accounts for step granularity (gap), potential new overhead if we are currently
        # in a bad state, and a safety margin to prevent failing at the very last second.
        # 3.0 * gap gives us a 3-step (usually 3-hour) runway before the absolute mathematical limit.
        safety_buffer = (3.0 * gap) + (2.0 * overhead_const)
        
        min_time_needed_for_od = remaining_work + pending_overhead + safety_buffer
        
        # If we are within the danger zone, prioritize Deadline over Cost.
        if time_left < min_time_needed_for_od:
            return ClusterType.ON_DEMAND

        # 3. Cost Minimization Logic (Slack is available)
        if has_spot:
            # Spot is available in current region. Best option.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # We have slack, so we avoid OD. We try to find Spot elsewhere.
            
            num_regions = self.env.get_num_regions()
            current_region = self.env.get_current_region()
            
            if num_regions > 1:
                # Switch to next region in round-robin fashion
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
            
            # We return NONE because:
            # a) If we switched, we don't know the Spot status of the new region yet (has_spot is stale).
            # b) If we didn't switch (1 region), Spot is false, so we wait.
            # c) NONE incurs no monetary cost, only time cost (which we can afford given slack).
            return ClusterType.NONE