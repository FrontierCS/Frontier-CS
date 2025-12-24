import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late Multi-Region Scheduling Strategy."""

    NAME = "cant_be_late_strategy"

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
        current_work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - current_work_done
        
        # If work is essentially done, stop
        if work_remaining <= 1e-6:
            return ClusterType.NONE

        time_elapsed = self.env.elapsed_seconds
        time_remaining = self.deadline - time_elapsed
        
        # Calculate strict time budget needed to finish using On-Demand.
        # We assume we pay restart_overhead to account for potential switching costs.
        time_needed_od = work_remaining + self.restart_overhead
        
        # Define safety buffer: 
        # If we are close to the "Point of No Return" (time_needed_od), we must switch to OD.
        # We add 1.5 * gap_seconds to ensure we don't start a "probe" (waiting 1 step)
        # if that wait would push us past the deadline feasibility.
        safety_buffer = 1.5 * self.env.gap_seconds
        
        # Panic Condition: Force On-Demand if deadline is at risk
        if time_remaining < (time_needed_od + safety_buffer):
            return ClusterType.ON_DEMAND
        
        # Normal Operation: Prefer Spot if available
        if has_spot:
            return ClusterType.SPOT
        
        # Spot unavailable in current region, but we have time slack.
        # Switch to the next region and return NONE to probe availability in the next step.
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        next_region = (current_region + 1) % num_regions
        
        self.env.switch_region(next_region)
        return ClusterType.NONE
