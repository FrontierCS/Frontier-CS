import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"

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
        # Calculate remaining work and time
        done_time = sum(self.task_done_time)
        work_rem = self.task_duration - done_time
        time_rem = self.deadline - self.env.elapsed_seconds

        # If work is already finished, pause (though env should handle this)
        if work_rem <= 1e-6:
            return ClusterType.NONE

        # --- Panic Mode Check ---
        # Calculate if we are dangerously close to the deadline.
        # If we run On-Demand, we are guaranteed to finish if Time_Remaining >= Work_Remaining + Overhead.
        # We must decide whether we can afford to delay/gamble on Spot for this step.
        
        # Calculate overhead if we switch to ON_DEMAND now
        # If we are already running ON_DEMAND, we continue with 0 extra overhead.
        # Otherwise (Spot or None), switching to ON_DEMAND incurs restart_overhead.
        overhead_cost = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            overhead_cost = self.restart_overhead
            
        # Minimum time required to complete the task using On-Demand starting now
        min_time_needed = work_rem + overhead_cost
        
        # Safety Threshold:
        # If we do NOT run On-Demand now (i.e., we wait or try Spot), we consume 'gap_seconds'.
        # We must ensure that after consuming this gap, we still have enough time to finish via On-Demand.
        # Condition: (Time_Rem - Gap) >= min_time_needed + Buffer
        # Rearranged: Time_Rem >= min_time_needed + Gap + Buffer
        # We use 1.5 * gap_seconds as the margin to account for the current step consumption plus a safety buffer.
        safety_threshold = min_time_needed + self.env.gap_seconds * 1.5
        
        if time_rem < safety_threshold:
            # Not enough slack to risk Spot failure or waiting. Force On-Demand.
            return ClusterType.ON_DEMAND

        # --- Cost Optimization Mode ---
        # We have enough slack to try Spot or switch regions.
        if has_spot:
            # Spot is available in current region. Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable in current region.
            # We switch to the next region and wait (return NONE) to avoid paying for On-Demand 
            # or risking a crash by returning SPOT in a region we haven't checked.
            # Round-robin switching strategy.
            curr_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (curr_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE