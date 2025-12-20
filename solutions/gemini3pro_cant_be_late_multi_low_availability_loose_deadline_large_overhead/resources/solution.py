import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "SlackAwareRoundRobin"  # REQUIRED: unique identifier

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

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Retrieve environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        
        # Calculate work progress
        total_work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - total_work_done
        
        # If task is effectively done, stop
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # Calculate time metrics
        remaining_time = self.deadline - elapsed
        overhead = self.restart_overhead
        
        # Calculate Slack
        # Estimate worst-case time required if we switch to On-Demand immediately.
        # We add 'overhead' conservatively to ensure we can pay the restart cost.
        time_needed_od = remaining_work + overhead
        slack = remaining_time - time_needed_od
        
        # Safety Buffer
        # We need enough slack to absorb step quantization (gap) and potential search costs.
        # If slack drops below this buffer, we must switch to OD to guarantee deadline.
        SAFE_BUFFER = 1.5 * gap
        
        # 1. Panic Check: Ensure deadline safety
        if slack < SAFE_BUFFER:
            # Not enough slack to search or risk Spot. Force On-Demand.
            # OD is reliable and guaranteed to finish if we respect the buffer.
            return ClusterType.ON_DEMAND
            
        # 2. Spot Availability Check
        if has_spot:
            # Spot is available in the current region. Use it.
            return ClusterType.SPOT
            
        # 3. Search Strategy
        else:
            # Spot is unavailable in the current region, but we have plenty of slack.
            # Strategy: Switch to the next region and wait (NONE) for one time step.
            # In the next step, we will check availability in the new region.
            current_region = self.env.get_current_region()
            num_regions = self.env.get_num_regions()
            next_region = (current_region + 1) % num_regions
            
            self.env.switch_region(next_region)
            return ClusterType.NONE
