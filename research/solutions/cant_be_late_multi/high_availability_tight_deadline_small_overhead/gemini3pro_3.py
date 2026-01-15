import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "CantBeLate_Solution"

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
        # 1. Gather Telemetry
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        
        done = sum(self.task_done_time)
        remaining_work = self.task_duration - done
        
        if remaining_work <= 0:
            return ClusterType.NONE
            
        time_left = self.deadline - elapsed
        overhead = self.restart_overhead
        
        # 2. Safety Analysis
        # Calculate time required if we ran purely on On-Demand from now on
        # We include one overhead for the potential switch/start
        required_time = remaining_work + overhead
        
        # Panic Threshold:
        # If time_left is close to required_time, we must use OD to guarantee meeting deadline.
        # We add a buffer of 1.5 * gap to account for step granularity and safety.
        panic_buffer = 1.5 * gap
        
        if time_left < (required_time + panic_buffer):
            # Critical state: minimize risk, ignore cost
            return ClusterType.ON_DEMAND

        # 3. Cost Optimization Strategy
        if has_spot:
            # Best case: Spot is available in current region
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # We should try another region.
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            
            # Decision: Should we run OD in the new region immediately, or wait (NONE)?
            # Run OD: Costs money ($3.06/hr), guarantees progress.
            # Run NONE: Costs nothing ($0), wastes time (reduces slack).
            #
            # If we have abundant slack, we use NONE to "probe" the new region for free.
            # If slack is getting tighter, we use OD to maintain progress while searching.
            
            current_slack = time_left - required_time
            probe_threshold = 4.0 * gap  # Allow probing if we have >4 steps of slack
            
            if current_slack > probe_threshold:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND