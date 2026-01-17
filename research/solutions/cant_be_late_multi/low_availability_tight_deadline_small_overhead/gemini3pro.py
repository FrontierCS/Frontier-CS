import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "solution_strategy"

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
        # Gather environment state
        current_region = self.env.get_current_region()
        num_regions = self.env.get_num_regions()
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done
        
        # If task is completed
        if work_remaining <= 0:
            return ClusterType.NONE

        time_remaining = self.deadline - elapsed
        
        # Panic Threshold Calculation
        # We must switch to On-Demand if we are running out of time.
        # Time required to finish on On-Demand = work_remaining + restart_overhead (if restarting/switching).
        # If we choose to search/wait this step (returning NONE), we consume 'gap' seconds.
        # We must ensure that: time_remaining - gap >= work_remaining + restart_overhead
        # We add a safety buffer (300s) to be safe.
        
        safety_buffer = 300.0
        panic_threshold = work_remaining + self.restart_overhead + gap + safety_buffer
        
        if time_remaining < panic_threshold:
            # Not enough slack to search or rely on Spot. Force On-Demand.
            return ClusterType.ON_DEMAND
            
        # Economy Strategy: Prefer Spot
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot unavailable in current region.
            # Switch to next region and wait (NONE) to check availability in next step.
            next_region = (current_region + 1) % num_regions
            self.env.switch_region(next_region)
            return ClusterType.NONE