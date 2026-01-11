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
        """
        # Calculate state
        accumulated_work = sum(self.task_done_time)
        remaining_work = self.task_duration - accumulated_work
        time_left = self.deadline - self.env.elapsed_seconds
        
        # Conservative overhead estimate (in seconds)
        overhead = self.restart_overhead
        
        # Panic Threshold:
        # If time remaining is dangerously close to the minimum time needed to finish
        # (work + overhead), we must switch to On-Demand and stay there to guarantee completion.
        # We add a safety buffer of 2 timesteps (gap_seconds) to account for simulator granularity.
        panic_buffer = 2.0 * self.env.gap_seconds
        panic_threshold = remaining_work + overhead + panic_buffer
        
        if time_left < panic_threshold:
            # Panic mode: Force On-Demand, do not switch regions to ensure stability.
            return ClusterType.ON_DEMAND

        # If Spot is available in the current region, use it (cheapest option).
        if has_spot:
            return ClusterType.SPOT

        # Hunt Mode:
        # Spot is unavailable in current region. We should look elsewhere.
        # Switch to the next region in a round-robin fashion.
        num_regions = self.env.get_num_regions()
        curr_region = self.env.get_current_region()
        self.env.switch_region((curr_region + 1) % num_regions)
        
        # Decide whether to Probe (pause) or Run (OD) in the new region.
        # If we have substantial slack, we return NONE to "peek" at the next step's availability
        # without incurring OD costs. 
        # Probe Threshold is set to allow hunting as long as we have ~6 steps of slack buffer.
        probe_threshold = remaining_work + overhead + (6.0 * self.env.gap_seconds)
        
        if time_left > probe_threshold:
            # Plenty of time: Pause to save money and check spot availability in new region next tick.
            return ClusterType.NONE
        else:
            # Slack is tightening: Run OD in new region to ensure progress while still potentially 
            # switching to Spot next tick if it becomes available (since we switched region).
            return ClusterType.ON_DEMAND